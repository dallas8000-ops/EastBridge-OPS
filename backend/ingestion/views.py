from rest_framework.decorators import api_view
from rest_framework.response import Response

from assistant.embeddings import active_model_name, resolve_provider
from assistant.models import EvidenceDocument
from intelligence.models import EconomicIndicator
from regulatory.models import RegulatoryChange
from trade.models import TradeProcedure

from .models import IngestionRun
from .serializers import IngestionStatusSerializer


@api_view(["GET"])
def ingestion_status(request):
    last_reg = IngestionRun.objects.filter(run_type=IngestionRun.RunType.REGULATORY).first()
    last_econ = IngestionRun.objects.filter(run_type=IngestionRun.RunType.ECONOMIC).first()
    provider = resolve_provider()
    data = {
        "evidence_count": EvidenceDocument.objects.count(),
        "regulatory_changes_count": RegulatoryChange.objects.count(),
        "economic_indicators_count": EconomicIndicator.objects.count(),
        "trade_procedures_count": TradeProcedure.objects.count(),
        "embedding_provider": provider,
        "embedding_model": active_model_name(provider),
        "last_regulatory_run": last_reg,
        "last_economic_run": last_econ,
    }
    return Response(IngestionStatusSerializer(data).data)
