"""Offline sample regulatory, economic, and evidence data for zip/fixture exports (no network)."""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from assistant.models import EvidenceDocument
from core.models import Country, DataSource
from intelligence.models import CountryRiskSnapshot, EconomicIndicator
from regulatory.models import RegulatoryChange


SAMPLES = [
    {
        "country_code": "UG",
        "source_name": "Uganda Revenue Authority",
        "title": "URA VAT filing deadline reminder for Q1 2026",
        "summary": (
            "Uganda Revenue Authority reminds registered taxpayers to file VAT returns "
            "and remit payments by the statutory deadline for the January–March 2026 period."
        ),
        "business_impact": (
            "EU exporters with Ugandan VAT registration must confirm filing calendars "
            "and avoid late-payment penalties on cross-border equipment imports."
        ),
        "required_action": (
            "Confirm your local tax agent has filed Q1 VAT and reconcile import VAT "
            "credits against customs entries."
        ),
        "category": RegulatoryChange.Category.TAX,
        "risk_level": RegulatoryChange.RiskLevel.MEDIUM,
        "source_url": "https://www.ura.go.eg/offline-sample/ura-vat-q1-2026",
        "published_at": date(2026, 3, 15),
        "evidence_content": (
            "Uganda Revenue Authority VAT filing: registered taxpayers must submit returns "
            "and payment for the quarterly period. Penalties apply for late filing. "
            "Importers should reconcile customs import VAT with filed returns."
        ),
    },
    {
        "country_code": "KE",
        "source_name": "Kenya Revenue Authority",
        "title": "KRA customs declaration update for solar equipment HS codes",
        "summary": (
            "Kenya Revenue Authority published guidance on classification and documentation "
            "for photovoltaic modules and inverters under updated HS headings."
        ),
        "business_impact": (
            "Solar EPC projects importing modules and inverters must verify HS codes, "
            "duty exemptions, and supporting certificates before clearance."
        ),
        "required_action": (
            "Review bill of lading and commercial invoice HS codes with your customs broker "
            "before shipment arrival at Mombasa."
        ),
        "category": RegulatoryChange.Category.CUSTOMS,
        "risk_level": RegulatoryChange.RiskLevel.HIGH,
        "source_url": "https://www.kra.go.ke/offline-sample/kra-solar-hs-2026",
        "published_at": date(2026, 2, 10),
        "evidence_content": (
            "Kenya customs: photovoltaic equipment imports require correct HS classification, "
            "valid certificates of origin where applicable, and IDF filing before arrival. "
            "Brokers should validate duty relief eligibility for renewable energy projects."
        ),
    },
]

INDICATORS = [
    ("UG", EconomicIndicator.IndicatorType.GDP_GROWTH, "Real GDP growth", "5.400000", "%", date(2025, 12, 31)),
    ("KE", EconomicIndicator.IndicatorType.INFLATION, "Consumer price inflation", "6.800000", "%", date(2025, 12, 31)),
    ("TZ", EconomicIndicator.IndicatorType.FX_RATE, "TZS per EUR (approx.)", "2750.000000", "TZS/EUR", date(2026, 1, 31)),
]

RISK_SNAPSHOTS = [
    ("UG", "62.50", "58.00", "65.00", "60.00", "Moderate regulatory churn; verify URA filings before equipment import."),
    ("KE", "55.00", "52.00", "58.00", "54.00", "Strong trade gateway; monitor KRA customs classification updates."),
]


class Command(BaseCommand):
    help = "Load offline regulatory, economic, and evidence samples (no live ingest)."

    def handle(self, *args, **options):
        wb_source = DataSource.objects.filter(name__icontains="World Bank").first()

        for sample in SAMPLES:
            country = Country.objects.get(code=sample["country_code"])
            source = DataSource.objects.filter(name=sample["source_name"]).first()
            RegulatoryChange.objects.update_or_create(
                source_url=sample["source_url"],
                defaults={
                    "title": sample["title"],
                    "summary": sample["summary"],
                    "business_impact": sample["business_impact"],
                    "required_action": sample["required_action"],
                    "category": sample["category"],
                    "risk_level": sample["risk_level"],
                    "source": source,
                    "country": country,
                    "published_at": sample["published_at"],
                },
            )
            EvidenceDocument.objects.update_or_create(
                source_url=sample["source_url"],
                defaults={
                    "title": sample["title"],
                    "country_code": sample["country_code"],
                    "category": sample["category"],
                    "content": sample["evidence_content"],
                    "published_at": sample["published_at"],
                },
            )

        for code, indicator_type, label, value, unit, period in INDICATORS:
            country = Country.objects.get(code=code)
            EconomicIndicator.objects.update_or_create(
                country=country,
                indicator_type=indicator_type,
                period=period,
                defaults={
                    "label": label,
                    "value": Decimal(value),
                    "unit": unit,
                    "source": wb_source,
                    "source_url": "https://data.worldbank.org/offline-sample",
                },
            )

        for code, overall, political, regulatory, trade, summary in RISK_SNAPSHOTS:
            country = Country.objects.get(code=code)
            CountryRiskSnapshot.objects.update_or_create(
                country=country,
                as_of=date(2026, 1, 31),
                defaults={
                    "overall_score": Decimal(overall),
                    "political_risk": Decimal(political),
                    "regulatory_risk": Decimal(regulatory),
                    "trade_risk": Decimal(trade),
                    "summary": summary,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Offline snapshot: {len(SAMPLES)} regulatory changes, "
                f"{len(INDICATORS)} indicators, {len(RISK_SNAPSHOTS)} risk snapshots."
            )
        )
