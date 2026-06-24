from celery import shared_task

from ingestion.tasks import run_economic_ingestion


@shared_task
def sync_economic_indicators():
    return run_economic_ingestion.delay().id
