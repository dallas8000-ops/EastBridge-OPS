from rest_framework import viewsets

from .models import TradeProcedure
from .serializers import TradeProcedureSerializer


class TradeProcedureViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TradeProcedure.objects.select_related("country").prefetch_related("steps")
    serializer_class = TradeProcedureSerializer
    search_fields = ("title", "summary")
    filterset_fields = ("country", "activity_type", "source_portal")
    ordering_fields = ("title", "last_synced_at", "estimated_days")
