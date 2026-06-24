from rest_framework import serializers

from .models import Country, DataSource


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("id", "code", "name", "is_eac_member", "currency_code")


class DataSourceSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = DataSource
        fields = (
            "id",
            "name",
            "source_type",
            "url",
            "country",
            "is_active",
            "last_checked_at",
        )
