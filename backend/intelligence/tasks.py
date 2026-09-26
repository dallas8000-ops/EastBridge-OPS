from celery import shared_task
from ingestion.fetchers.world_bank import fetch_world_bank_indicators
from ingestion.models import IngestionRun
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def sync_economic_indicators():
    """Sync economic indicators from World Bank API."""
    run = IngestionRun.objects.create(run_type=IngestionRun.RunType.ECONOMIC)
    
    try:
        result = fetch_world_bank_indicators()
        run.items_new = result.get("created", 0)
        run.items_fetched = result.get("created", 0) + result.get("updated", 0)
        run.summary = result
        logger.info("Economic indicators sync completed: %s", result)
    except Exception as exc:
        logger.exception("Economic indicators sync failed")
        run.items_failed = 1
        run.summary = {"error": str(exc)}
    
    run.finished_at = timezone.now()
    run.save()
    
    return {
        "run_id": run.id,
        "items_new": run.items_new,
        "items_failed": run.items_failed,
    }
