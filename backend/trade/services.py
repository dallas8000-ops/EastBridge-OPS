import logging

from django.utils import timezone

from assistant.models import EvidenceDocument
from core.models import Country
from trade.fetchers.tip import TIP_PORTALS, fetch_country_procedures
from trade.models import TradeProcedure, TradeProcedureStep

logger = logging.getLogger(__name__)


def sync_trade_procedures(country_codes: list[str] | None = None, offline: bool = False) -> dict:
    codes = country_codes or list(TIP_PORTALS.keys())
    created = 0
    updated = 0
    errors: list[str] = []

    for code in codes:
        try:
            country = Country.objects.get(code=code)
        except Country.DoesNotExist:
            errors.append(f"Unknown country: {code}")
            continue

        try:
            parsed_list, source = fetch_country_procedures(code, offline=offline)
        except Exception as exc:
            logger.exception("TIP fetch failed for %s", code)
            errors.append(f"{code}: {exc}")
            continue

        if source == "fallback" and not offline:
            errors.append(f"{code}: live portal unreachable — loaded curated fallback procedures")

        portal_name = TIP_PORTALS.get(code, {}).get("name", "EAC TIP")

        for parsed in parsed_list:
            procedure, was_created = TradeProcedure.objects.update_or_create(
                external_id=parsed.external_id,
                defaults={
                    "title": parsed.title,
                    "slug": parsed.external_id.split("-", 1)[-1][:255],
                    "country": country,
                    "activity_type": parsed.activity_type,
                    "summary": parsed.summary,
                    "source_url": parsed.url,
                    "source_portal": portal_name,
                    "estimated_days": parsed.estimated_days,
                    "estimated_cost": parsed.estimated_cost,
                    "last_synced_at": timezone.now(),
                },
            )

            procedure.steps.all().delete()
            for step_data in parsed.steps:
                TradeProcedureStep.objects.create(procedure=procedure, **step_data)

            step_text = "\n".join(
                f"{s['sort_order'] + 1}. {s['title']}: {s['description'][:300]}"
                for s in parsed.steps
            )
            evidence_content = (
                f"{parsed.summary}\n\nProcedure steps:\n{step_text}\n\n"
                f"Source: {portal_name} ({parsed.url})"
            )
            EvidenceDocument.objects.update_or_create(
                source_url=parsed.url,
                defaults={
                    "title": f"{portal_name}: {parsed.title}",
                    "country_code": code,
                    "category": "trade_procedure",
                    "content": evidence_content,
                },
            )

            from assistant.tasks import embed_document
            from assistant.models import EvidenceDocument as ED

            doc = ED.objects.get(source_url=parsed.url)
            embed_document(doc)

            if was_created:
                created += 1
            else:
                updated += 1

    return {"created": created, "updated": updated, "errors": errors}
