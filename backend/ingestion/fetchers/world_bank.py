import logging
from datetime import date
from decimal import Decimal

import httpx
from django.utils import timezone

from core.models import Country, DataSource
from intelligence.models import CountryRiskSnapshot, EconomicIndicator

from .base import FetchedItem

logger = logging.getLogger(__name__)

WORLD_BANK_BASE = "https://api.worldbank.org/v2"

# ISO2 -> World Bank uses 2-letter codes in v2 country API
EAC_ISO2 = ["UG", "KE", "TZ", "RW", "BI", "SS"]

ISO3_TO_ISO2 = {
    "UGA": "UG", "KEN": "KE", "TZA": "TZ", "RWA": "RW", "BDI": "BI", "SSD": "SS",
}

INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": (EconomicIndicator.IndicatorType.GDP_GROWTH, "GDP growth (annual %)"),
    "FP.CPI.TOTL.ZG": (EconomicIndicator.IndicatorType.INFLATION, "Inflation, consumer prices (annual %)"),
    "PA.NUS.FCRF": (EconomicIndicator.IndicatorType.FX_RATE, "Official exchange rate (LCU per US$)"),
}


def fetch_world_bank_indicators(country_codes: list[str] | None = None) -> dict:
    """Fetch latest World Bank indicators and persist EconomicIndicator rows."""
    codes = country_codes or EAC_ISO2

    source, _ = DataSource.objects.get_or_create(
        name="World Bank Open Data API",
        defaults={
            "source_type": DataSource.SourceType.WORLD_BANK,
            "url": "https://data.worldbank.org/",
            "is_active": True,
        },
    )

    created = 0
    updated = 0
    errors: list[str] = []
    latest_by_country: dict[str, list[Decimal]] = {}

    with httpx.Client(timeout=60.0) as client:
        for iso2 in codes:
            for indicator_code, (indicator_type, label) in INDICATORS.items():
                url = (
                    f"{WORLD_BANK_BASE}/country/{iso2}/indicator/{indicator_code}"
                    f"?format=json&mrv=1&per_page=1"
                )
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    payload = response.json()
                except httpx.HTTPError as exc:
                    errors.append(f"{iso2}/{indicator_code}: {exc}")
                    continue

                if not isinstance(payload, list) or len(payload) < 2:
                    errors.append(f"{iso2}/{indicator_code}: unexpected response")
                    continue

                records = payload[1]
                if not records:
                    continue

                record = records[0]
                if record.get("value") is None:
                    continue

                try:
                    country = Country.objects.get(code=iso2)
                except Country.DoesNotExist:
                    continue

                period_year = int(record.get("date", "2020"))
                period = date(period_year, 12, 31)
                value = Decimal(str(record["value"]))
                source_url = (
                    f"https://data.worldbank.org/indicator/{indicator_code}?locations={iso2}"
                )

                _, was_created = EconomicIndicator.objects.update_or_create(
                    country=country,
                    indicator_type=indicator_type,
                    period=period,
                    defaults={
                        "label": label,
                        "value": value,
                        "unit": "%" if "ZG" in indicator_code else "LCU/USD",
                        "source": source,
                        "source_url": source_url,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

                latest_by_country.setdefault(iso2, []).append(value)

    _update_risk_snapshots(latest_by_country)
    source.last_checked_at = timezone.now()
    source.save(update_fields=["last_checked_at"])

    _index_world_bank_evidence()

    return {
        "created": created,
        "updated": updated,
        "countries": len(latest_by_country),
        "errors": errors,
    }


def _update_risk_snapshots(latest_by_country: dict[str, list[Decimal]]) -> None:
    """Derive simple country risk snapshots from available indicators."""
    today = date.today()
    for iso2, values in latest_by_country.items():
        try:
            country = Country.objects.get(code=iso2)
        except Country.DoesNotExist:
            continue

        avg = sum(values) / len(values) if values else Decimal("50")
        # Higher inflation / volatility => higher risk (simplified heuristic)
        overall = min(Decimal("100"), max(Decimal("0"), Decimal("50") + abs(avg - Decimal("5")) * 2))

        CountryRiskSnapshot.objects.update_or_create(
            country=country,
            as_of=today,
            defaults={
                "overall_score": overall,
                "political_risk": overall * Decimal("0.9"),
                "regulatory_risk": overall * Decimal("1.1"),
                "trade_risk": overall,
                "summary": f"Auto-computed from World Bank indicators as of {today.isoformat()}.",
            },
        )


def _index_world_bank_evidence() -> None:
    """Index World Bank country profiles as assistant evidence."""
    from assistant.models import EvidenceDocument

    for item in fetch_world_bank_as_items():
        EvidenceDocument.objects.update_or_create(
            source_url=item.url,
            defaults={
                "title": item.title,
                "country_code": item.external_id.replace("wb-country-", ""),
                "category": "economic",
                "content": item.content,
                "published_at": item.published_at,
            },
        )


def fetch_world_bank_as_items() -> list[FetchedItem]:
    """Return World Bank country profile pages as evidence items."""
    items: list[FetchedItem] = []
    for code in EAC_ISO2:
        try:
            country = Country.objects.get(code=code)
        except Country.DoesNotExist:
            continue
        url = f"https://data.worldbank.org/country/{code.lower()}"
        items.append(
            FetchedItem(
                external_id=f"wb-country-{code}",
                title=f"World Bank country profile: {country.name}",
                url=url,
                content=(
                    f"World Bank open data profile for {country.name} ({code}). "
                    f"Includes GDP, inflation, trade, and business environment indicators."
                ),
                published_at=date.today(),
            )
        )
    return items
