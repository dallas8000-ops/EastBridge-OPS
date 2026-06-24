import logging

import httpx
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

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
                fail_silently=False,
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
