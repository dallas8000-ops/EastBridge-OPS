from rest_framework import serializers

from core.models import Country
from core.serializers import CountrySerializer

from .models import Vendor, VendorContractRecord, VendorDocument, VendorPaymentRecord


class VendorDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorDocument
        fields = ("id", "document_type", "file", "uploaded_at", "verified")
        read_only_fields = ("uploaded_at", "verified")


class VendorContractRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContractRecord
        fields = ("id", "contract_ref", "value_usd", "start_date", "end_date", "notes")


class VendorPaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorPaymentRecord
        fields = ("id", "amount_usd", "payment_date", "status", "notes")


class VendorContractWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContractRecord
        fields = ("contract_ref", "value_usd", "start_date", "end_date", "notes")


class VendorPaymentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorPaymentRecord
        fields = ("amount_usd", "payment_date", "status", "notes")


class VendorSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    documents = VendorDocumentSerializer(many=True, read_only=True)
    contracts = VendorContractRecordSerializer(many=True, read_only=True)
    payments = VendorPaymentRecordSerializer(many=True, read_only=True)

    class Meta:
        model = Vendor
        fields = (
            "id",
            "name",
            "registration_number",
            "country",
            "business_profile",
            "verification_status",
            "risk_score",
            "red_flags",
            "documents",
            "contracts",
            "payments",
            "created_at",
            "updated_at",
        )


class VendorWriteSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(write_only=True)

    class Meta:
        model = Vendor
        fields = (
            "name",
            "registration_number",
            "country_code",
            "business_profile",
            "verification_status",
            "risk_score",
            "red_flags",
        )

    def validate_country_code(self, value):
        code = value.upper()
        if not Country.objects.filter(code=code).exists():
            raise serializers.ValidationError(f"Unknown country code: {code}")
        return code

    def create(self, validated_data):
        country = Country.objects.get(code=validated_data.pop("country_code"))
        return Vendor.objects.create(country=country, **validated_data)

    def update(self, instance, validated_data):
        if "country_code" in validated_data:
            country = Country.objects.get(code=validated_data.pop("country_code"))
            instance.country = country
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance


class VendorDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorDocument
        fields = ("document_type", "file")
