from rest_framework import serializers

from core.serializers import CountrySerializer

from .models import CountryRiskSnapshot, EconomicIndicator


class EconomicIndicatorSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = EconomicIndicator
        fields = (
            "id",
            "country",
            "indicator_type",
            "label",
            "value",
            "unit",
            "period",
            "source_url",
            "fetched_at",
        )


class CountryRiskSnapshotSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = CountryRiskSnapshot
        fields = (
            "id",
            "country",
            "overall_score",
            "political_risk",
            "regulatory_risk",
            "trade_risk",
            "summary",
            "as_of",
        )
