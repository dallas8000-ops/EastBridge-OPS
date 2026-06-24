from rest_framework import viewsets

from .models import CountryRiskSnapshot, EconomicIndicator
from .serializers import CountryRiskSnapshotSerializer, EconomicIndicatorSerializer


class EconomicIndicatorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EconomicIndicator.objects.select_related("country", "source")
    serializer_class = EconomicIndicatorSerializer
    filterset_fields = ("country", "indicator_type")
    ordering_fields = ("period", "fetched_at")


class CountryRiskSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CountryRiskSnapshot.objects.select_related("country")
    serializer_class = CountryRiskSnapshotSerializer
    filterset_fields = ("country",)
    ordering_fields = ("as_of",)
