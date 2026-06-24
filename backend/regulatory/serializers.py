from rest_framework import serializers

from core.serializers import CountrySerializer

from .models import ChangeAlertSubscription, RegulatoryChange


class RegulatoryChangeSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = RegulatoryChange
        fields = (
            "id",
            "title",
            "summary",
            "business_impact",
            "required_action",
            "category",
            "risk_level",
            "source_url",
            "country",
            "published_at",
            "detected_at",
        )


class ChangeAlertSubscriptionSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    country_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ChangeAlertSubscription
        fields = (
            "id",
            "email",
            "country",
            "country_code",
            "category",
            "is_active",
            "created_at",
        )
        read_only_fields = ("created_at",)

    def create(self, validated_data):
        country_code = validated_data.pop("country_code", "")
        country = None
        if country_code:
            from core.models import Country

            country = Country.objects.get(code=country_code.upper())
        return ChangeAlertSubscription.objects.create(country=country, **validated_data)