import logging

import httpx
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from core.models import DataSource
from ingestion.fetchers.world_bank import fetch_world_bank_indicators
from ingestion.services import indexer

logger = logging.getLogger(__name__)


@shared_task
def run_regulatory_ingestion():
    run = indexer.run_regulatory_ingestion()
    return {
        "run_id": run.id,
        "items_new": run.items_new,
        "items_failed": run.items_failed,
    }


@shared_task
def run_economic_ingestion():
    from ingestion.models import IngestionRun

    run = IngestionRun.objects.create(run_type=IngestionRun.RunType.ECONOMIC)
    try:
        result = fetch_world_bank_indicators()
    except Exception as exc:
        logger.exception("World Bank sync failed")
        run.items_failed = 1
        run.summary = {"error": str(exc)}
        run.finished_at = timezone.now()
        run.save()
        return {"error": str(exc)}

    run.items_new = result.get("created", 0)
    run.items_fetched = result.get("created", 0) + result.get("updated", 0)
    run.summary = result
    run.finished_at = timezone.now()
    run.save()
    return result


def dispatch_change_alerts(change) -> dict:
    """Send email and webhook alerts for a new regulatory change."""
    try:
        from regulatory.models import ChangeAlertSubscription

        subs = ChangeAlertSubscription.objects.filter(is_active=True).filter(
            Q(country__isnull=True) | Q(country=change.country)
        )
        if change.category:
            subs = subs.filter(Q(category="") | Q(category=change.category))

        emails = list(subs.values_list("email", flat=True).distinct())
        sent = 0
        errors = []

        subject = f"[EastBridge] {change.risk_level.upper()} regulatory change — {change.country.code}"
        body = (
            f"Title: {change.title}\n\n"
            f"Country: {change.country.name}\n"
            f"Category: {change.category}\n"
            f"Risk: {change.risk_level}\n\n"
            f"Summary: {change.summary}\n\n"
            f"Business impact: {change.business_impact}\n\n"
            f"Required action: {change.required_action}\n\n"
            f"Source: {change.source_url}\n"
        )

        if emails:
            try:
                send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    emails,
                    fail_silently=True,  # Changed to fail_silently to avoid blocking
                )
                sent = len(emails)
            except Exception as exc:
                logger.exception("Email alert failed")
                errors.append(str(exc))

        webhook = getattr(settings, "ALERT_WEBHOOK_URL", "")
        if webhook:
            payload = {
                "event": "regulatory_change.created",
                "title": change.title,
                "country": change.country.code,
                "category": change.category,
                "risk_level": change.risk_level,
                "source_url": change.source_url,
                "summary": change.summary,
                "required_action": change.required_action,
            }
            try:
                with httpx.Client(timeout=15.0) as client:
                    client.post(webhook, json=payload)
            except Exception as exc:
                logger.exception("Webhook alert failed")
                errors.append(str(exc))

        return {"emails_sent": sent, "errors": errors}
    except Exception as exc:
        logger.exception("Failed to dispatch alerts for change")
        return {"emails_sent": 0, "errors": [str(exc)]}


@shared_task
def monitor_uganda_legal_sources():
    """Monitor Uganda-specific legal sources with high frequency."""
    return _monitor_country_legal_sources("UG")


@shared_task
def monitor_uganda_gazette():
    """Monitor Uganda Gazette specifically for official legal notices."""
    return _monitor_country_gazette("UG")


def _monitor_country_gazette(country_code: str) -> dict:
    """Monitor Gazette for a specific country."""
    from ingestion.models import IngestionRun

    run = IngestionRun.objects.create(run_type=IngestionRun.RunType.REGULATORY)
    
    gazette_source = DataSource.objects.filter(
        is_active=True,
        country__code=country_code,
        source_type=DataSource.SourceType.GAZETTE
    ).first()
    
    if not gazette_source:
        logger.warning("%s Gazette source not found", country_code)
        run.items_failed = 1
        run.summary = {"error": "Gazette source not configured"}
        run.finished_at = timezone.now()
        run.save()
        return {"error": "Gazette source not configured"}
    
    try:
        result = indexer.run_source_ingestion(gazette_source)
        run.items_fetched = result.get("fetched", 0)
        run.items_new = result.get("indexed", 0)
        run.items_failed = result.get("failed", 0)
        run.summary = result
        # Risk levels are set by the indexer and alerts sent by the post_save signal.
    except Exception as exc:
        logger.exception("%s Gazette monitoring failed", country_code)
        run.items_failed = 1
        run.summary = {"error": str(exc)}
    
    run.finished_at = timezone.now()
    run.save()
    
    logger.info(
        "%s Gazette monitoring completed: %d new items",
        country_code, run.items_new
    )
    
    return {
        "run_id": run.id,
        "items_new": run.items_new,
        "items_failed": run.items_failed,
    }


@shared_task
def daily_health_check():
    """Daily health check and cleanup tasks."""
    from ingestion.models import IngestedItem, IngestionRun
    from django.utils import timezone
    from datetime import timedelta
    
    logger.info("Starting daily health check")
    
    # Clean up old ingestion runs (keep last 30 days)
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_runs = IngestionRun.objects.filter(
        started_at__lt=cutoff_date
    ).delete()
    
    # Clean up failed ingestion items older than 7 days
    failed_cutoff = timezone.now() - timedelta(days=7)
    deleted_items = IngestedItem.objects.filter(
        status=IngestedItem.Status.FAILED,
        fetched_at__lt=failed_cutoff
    ).delete()
    
    # Check for stale sources (not checked in 24 hours)
    stale_cutoff = timezone.now() - timedelta(hours=24)
    stale_sources = DataSource.objects.filter(
        is_active=True,
        last_checked_at__lt=stale_cutoff
    ).count()
    
    health_report = {
        "deleted_runs": deleted_runs[0] if deleted_runs else 0,
        "deleted_failed_items": deleted_items[0] if deleted_items else 0,
        "stale_sources": stale_sources,
        "timestamp": timezone.now().isoformat(),
    }
    
    logger.info("Daily health check completed: %s", health_report)
    
    return health_report


@shared_task
def monitor_kenya_legal_sources():
    """Monitor Kenya-specific legal sources with high frequency."""
    return _monitor_country_legal_sources("KE")


@shared_task
def monitor_rwanda_legal_sources():
    """Monitor Rwanda-specific legal sources with high frequency."""
    return _monitor_country_legal_sources("RW")


def _monitor_country_legal_sources(country_code: str) -> dict:
    """Monitor legal sources for a specific country with high frequency."""
    from ingestion.models import IngestionRun

    run = IngestionRun.objects.create(run_type=IngestionRun.RunType.REGULATORY)
    
    # Target country-specific legal sources for high-frequency monitoring
    country_sources = DataSource.objects.filter(
        is_active=True,
        country__code=country_code,
        source_type__in=[
            DataSource.SourceType.LEGAL_REFORM,
            DataSource.SourceType.PARLIAMENT,
            DataSource.SourceType.JUDICIARY,
            DataSource.SourceType.GAZETTE,
            DataSource.SourceType.JUSTICE_MINISTRY,
        ]
    )
    
    summary = []
    total_new = 0
    total_failed = 0
    
    for source in country_sources:
        try:
            result = indexer.run_source_ingestion(source)
            summary.append(result)
            total_new += result.get("indexed", 0)
            total_failed += result.get("failed", 0)
            # Risk levels are set by the indexer and alerts sent by the post_save signal.
        except Exception as exc:
            logger.exception("Failed to monitor source %s", source.name)
            summary.append({
                "source": source.name,
                "error": str(exc),
                "indexed": 0,
                "failed": 1
            })
            total_failed += 1
    
    run.items_fetched = sum(r.get("fetched", 0) for r in summary)
    run.items_new = total_new
    run.items_failed = total_failed
    run.summary = {
        "country": country_code,
        "sources_monitored": len(country_sources),
        "results": summary
    }
    run.finished_at = timezone.now()
    run.save()
    
    logger.info(
        "%s legal sources monitoring completed: %d new items, %d failed",
        country_code, total_new, total_failed
    )
    
    return {
        "run_id": run.id,
        "country": country_code,
        "sources_monitored": len(country_sources),
        "items_new": total_new,
        "items_failed": total_failed,
    }


@shared_task
def monitor_kenya_gazette():
    """Monitor Kenya Gazette specifically for official legal notices."""
    return _monitor_country_gazette("KE")


@shared_task
def monitor_rwanda_gazette():
    """Monitor Rwanda Gazette specifically for official legal notices."""
    return _monitor_country_gazette("RW")
