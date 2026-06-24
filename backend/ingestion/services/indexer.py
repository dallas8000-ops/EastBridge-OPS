import logging

from django.utils import timezone

from assistant.models import EvidenceDocument
from core.models import DataSource
from ingestion.fetchers.base import FetchedItem, content_hash
from ingestion.fetchers.rss import fetch_html_list, fetch_rss
from ingestion.fetchers.world_bank import fetch_world_bank_as_items
from ingestion.models import IngestedItem, IngestionRun
from regulatory.models import RegulatoryChange

logger = logging.getLogger(__name__)

SOURCE_TYPE_TO_CATEGORY = {
    DataSource.SourceType.TAX_AUTHORITY: RegulatoryChange.Category.TAX,
    DataSource.SourceType.INVESTMENT_AUTHORITY: RegulatoryChange.Category.INVESTMENT,
    DataSource.SourceType.CUSTOMS: RegulatoryChange.Category.CUSTOMS,
    DataSource.SourceType.EAC_TRADE: RegulatoryChange.Category.EAC_TRADE,
    DataSource.SourceType.DATA_PROTECTION: RegulatoryChange.Category.DATA_PROTECTION,
    DataSource.SourceType.LABOR: RegulatoryChange.Category.LABOR,
    DataSource.SourceType.TRADE_PORTAL: RegulatoryChange.Category.CUSTOMS,
    DataSource.SourceType.RSS: RegulatoryChange.Category.OTHER,
}


def _infer_risk_level(title: str, content: str) -> str:
    text = f"{title} {content}".lower()
    if any(w in text for w in ("urgent", "immediate", "deadline", "penalty", "prosecution")):
        return RegulatoryChange.RiskLevel.HIGH
    if any(w in text for w in ("amendment", "change", "update", "new rate", "effective")):
        return RegulatoryChange.RiskLevel.MEDIUM
    return RegulatoryChange.RiskLevel.LOW


def _summarize_impact(title: str, content: str) -> tuple[str, str, str]:
    summary = content[:500] if content else title
    impact = (
        "Review this update for effects on registration, tax filing, import/export, "
        "or sector-specific compliance obligations."
    )
    action = "Assign to compliance lead for review and update internal checklists."
    if "tax" in title.lower() or "ura" in title.lower():
        impact = "May affect tax registration, filing deadlines, or duty rates for EU exporters."
        action = "Verify with local tax advisor and update VAT/import duty calculations."
    elif "customs" in title.lower() or "import" in title.lower():
        impact = "May affect import documentation, clearance procedures, or tariff classifications."
        action = "Review EAC customs procedure and update shipping documentation requirements."
    return summary, impact, action


def fetch_from_source(source: DataSource) -> list[FetchedItem]:
    config = source.ingestion_config or {}
    ingest_type = config.get("type", "rss")

    if ingest_type == "rss":
        feed_url = source.feed_url or source.url
        return fetch_rss(feed_url, max_items=config.get("max_items", 20))

    if ingest_type == "html_list":
        return fetch_html_list(
            list_url=config.get("list_url", source.url),
            link_selector=config.get("link_selector", "article a, .news-item a, h3 a, h2 a"),
            max_items=config.get("max_items", 15),
            base_url=config.get("base_url", source.url),
        )

    if ingest_type == "world_bank_profile":
        return fetch_world_bank_as_items()

    if ingest_type == "world_bank_api":
        return []

    raise ValueError(f"Unknown ingestion type: {ingest_type}")


def process_fetched_item(source: DataSource, item: FetchedItem) -> IngestedItem:
    """Dedupe, index evidence, and create regulatory change if applicable."""
    digest = content_hash(f"{item.title}|{item.url}|{item.content[:2000]}")

    ingested, created = IngestedItem.objects.get_or_create(
        data_source=source,
        external_id=item.external_id,
        defaults={
            "content_hash": digest,
            "title": item.title,
            "url": item.url,
            "raw_content": item.content,
            "published_at": item.published_at,
            "status": IngestedItem.Status.NEW,
        },
    )

    if not created and ingested.content_hash == digest:
        ingested.status = IngestedItem.Status.SKIPPED
        ingested.save(update_fields=["status"])
        return ingested

    if not created:
        ingested.content_hash = digest
        ingested.raw_content = item.content
        ingested.title = item.title
        ingested.url = item.url
        ingested.published_at = item.published_at

    country_code = ""
    if source.country:
        country_code = source.country.code

    category = SOURCE_TYPE_TO_CATEGORY.get(
        source.source_type, RegulatoryChange.Category.OTHER
    )

    evidence, _ = EvidenceDocument.objects.update_or_create(
        source_url=item.url,
        defaults={
            "title": item.title,
            "country_code": country_code,
            "category": category,
            "content": item.content,
            "published_at": item.published_at,
        },
    )
    ingested.evidence_id = evidence.id

    from assistant.tasks import embed_document

    embed_document(evidence)

    is_regulatory = source.source_type in (
        DataSource.SourceType.TAX_AUTHORITY,
        DataSource.SourceType.INVESTMENT_AUTHORITY,
        DataSource.SourceType.CUSTOMS,
        DataSource.SourceType.EAC_TRADE,
        DataSource.SourceType.DATA_PROTECTION,
        DataSource.SourceType.LABOR,
        DataSource.SourceType.TRADE_PORTAL,
        DataSource.SourceType.RSS,
    )

    if is_regulatory and source.country:
        summary, impact, action = _summarize_impact(item.title, item.content)
        change, _ = RegulatoryChange.objects.update_or_create(
            source_url=item.url,
            defaults={
                "title": item.title,
                "summary": summary,
                "business_impact": impact,
                "required_action": action,
                "category": category,
                "risk_level": _infer_risk_level(item.title, item.content),
                "source": source,
                "country": source.country,
                "published_at": item.published_at,
            },
        )
        ingested.regulatory_change_id = change.id

    ingested.status = IngestedItem.Status.INDEXED
    ingested.save()
    return ingested


def run_source_ingestion(source: DataSource) -> dict:
    try:
        items = fetch_from_source(source)
    except Exception as exc:
        logger.exception("Ingestion failed for %s", source.name)
        return {"source": source.name, "error": str(exc), "new": 0}

    new_count = 0
    failed = 0
    for item in items:
        try:
            result = process_fetched_item(source, item)
            if result.status == IngestedItem.Status.INDEXED:
                new_count += 1
        except Exception as exc:
            logger.exception("Failed processing item %s", item.url)
            failed += 1
            IngestedItem.objects.update_or_create(
                data_source=source,
                external_id=item.external_id,
                defaults={
                    "content_hash": content_hash(item.content),
                    "title": item.title,
                    "url": item.url,
                    "raw_content": item.content,
                    "status": IngestedItem.Status.FAILED,
                    "error_message": str(exc),
                },
            )

    source.last_checked_at = timezone.now()
    source.save(update_fields=["last_checked_at"])
    return {
        "source": source.name,
        "fetched": len(items),
        "indexed": new_count,
        "failed": failed,
    }


def run_regulatory_ingestion() -> IngestionRun:
    run = IngestionRun.objects.create(run_type=IngestionRun.RunType.REGULATORY)
    sources = DataSource.objects.filter(is_active=True).exclude(
        source_type=DataSource.SourceType.WORLD_BANK
    )
    summary = []
    total_new = 0
    total_failed = 0

    for source in sources:
        config = source.ingestion_config or {}
        if config.get("type") in ("world_bank_profile", "world_bank_api"):
            continue
        result = run_source_ingestion(source)
        summary.append(result)
        total_new += result.get("indexed", 0)
        total_failed += result.get("failed", 0)

    run.items_fetched = sum(r.get("fetched", 0) for r in summary)
    run.items_new = total_new
    run.items_failed = total_failed
    run.summary = summary
    run.finished_at = timezone.now()
    run.save()
    return run
