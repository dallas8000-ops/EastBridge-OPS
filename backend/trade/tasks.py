from celery import shared_task

from trade.services import sync_trade_procedures


@shared_task
def sync_trade_procedures_task():
    return sync_trade_procedures()
