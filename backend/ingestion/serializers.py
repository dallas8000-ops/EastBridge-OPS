from rest_framework import serializers

from .models import IngestedItem, IngestionRun


class IngestionRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionRun
        fields = (
            "id",
            "run_type",
            "started_at",
            "finished_at",
            "items_fetched",
            "items_new",
            "items_failed",
            "summary",
        )


class IngestionStatusSerializer(serializers.Serializer):
    evidence_count = serializers.IntegerField()
    regulatory_changes_count = serializers.IntegerField()
    economic_indicators_count = serializers.IntegerField()
    trade_procedures_count = serializers.IntegerField()
    embedding_provider = serializers.CharField()
    embedding_model = serializers.CharField()
    last_regulatory_run = IngestionRunSerializer(allow_null=True)
    last_economic_run = IngestionRunSerializer(allow_null=True)
