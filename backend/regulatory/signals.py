import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import RegulatoryChange

logger = logging.getLogger(__name__)


@receiver(post_save, sender=RegulatoryChange)
def notify_on_new_regulatory_change(sender, instance, created, **kwargs):
    if not created:
        return

    from ingestion.tasks import dispatch_change_alerts

    try:
        result = dispatch_change_alerts(instance)
        logger.info("Alerts dispatched for change %s: %s", instance.id, result)
    except Exception:
        logger.exception("Alert dispatch failed for change %s", instance.id)
