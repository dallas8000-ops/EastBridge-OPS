from rest_framework import serializers

from core.serializers import CountrySerializer

from .models import Industry, MarketEntryPlaybook, PlaybookStep


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ("id", "slug", "name")


class PlaybookStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaybookStep
        fields = (
            "id",
            "step_type",
            "title",
            "description",
            "source_url",
            "sort_order",
            "is_completed",
        )


class MarketEntryPlaybookSerializer(serializers.ModelSerializer):
    target_country = CountrySerializer(read_only=True)
    industry = IndustrySerializer(read_only=True)
    steps = PlaybookStepSerializer(many=True, read_only=True)

    class Meta:
        model = MarketEntryPlaybook
        fields = (
            "id",
            "origin_country",
            "industry",
            "target_country",
            "company_description",
            "estimated_timeline_weeks",
            "generated_at",
            "steps",
        )


class PlaybookGenerateSerializer(serializers.Serializer):
    origin_country = serializers.CharField(max_length=2)
    industry_slug = serializers.SlugField()
    target_country_code = serializers.CharField(max_length=2)
    company_description = serializers.CharField(required=False, allow_blank=True)
