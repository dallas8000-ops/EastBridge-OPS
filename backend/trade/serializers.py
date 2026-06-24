from rest_framework import serializers

from core.serializers import CountrySerializer

from .models import TradeProcedure, TradeProcedureStep


class TradeProcedureStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeProcedureStep
        fields = (
            "id",
            "sort_order",
            "title",
            "description",
            "responsible_agency",
            "documents_required",
            "estimated_days",
        )


class TradeProcedureSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    steps = TradeProcedureStepSerializer(many=True, read_only=True)

    class Meta:
        model = TradeProcedure
        fields = (
            "id",
            "external_id",
            "title",
            "slug",
            "country",
            "activity_type",
            "summary",
            "source_url",
            "source_portal",
            "estimated_days",
            "estimated_cost",
            "last_synced_at",
            "steps",
        )
