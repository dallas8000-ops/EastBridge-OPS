from celery import shared_task

from ingestion.tasks import run_economic_ingestion, run_regulatory_ingestion


@shared_task
def monitor_regulatory_sources():
    return run_regulatory_ingestion.delay().id


@shared_task
def sync_economic_indicators():
    return run_economic_ingestion.delay().id
