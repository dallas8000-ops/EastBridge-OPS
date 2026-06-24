from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import get_user_organization

from .models import Vendor, VendorContractRecord, VendorDocument, VendorPaymentRecord
from .serializers import (
    VendorContractRecordSerializer,
    VendorContractWriteSerializer,
    VendorDocumentSerializer,
    VendorDocumentUploadSerializer,
    VendorPaymentRecordSerializer,
    VendorPaymentWriteSerializer,
    VendorSerializer,
    VendorWriteSerializer,
)


class VendorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ("name", "registration_number")
    filterset_fields = ("country", "verification_status")
    ordering_fields = ("risk_score", "updated_at", "name")
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        org = get_user_organization(self.request)
        if not org:
            return Vendor.objects.none()
        return Vendor.objects.filter(organization=org).select_related(
            "country", "organization"
        ).prefetch_related("documents", "contracts", "payments")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return VendorWriteSerializer
        return VendorSerializer

    def perform_create(self, serializer):
        org = get_user_organization(self.request)
        if not org:
            raise PermissionError("Organization required")
        serializer.save(organization=org)

    def create(self, request, *args, **kwargs):
        write = VendorWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        org = get_user_organization(request)
        if not org:
            return Response({"detail": "Organization required"}, status=status.HTTP_403_FORBIDDEN)
        country_code = write.validated_data.pop("country_code")
        from core.models import Country

        vendor = Vendor.objects.create(
            organization=org,
            country=Country.objects.get(code=country_code),
            **write.validated_data,
        )
        return Response(VendorSerializer(vendor).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        vendor = self.get_object()
        write = VendorWriteSerializer(vendor, data=request.data, partial=True)
        write.is_valid(raise_exception=True)
        vendor = write.save()
        return Response(VendorSerializer(vendor).data)

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_document(self, request, pk=None):
        vendor = self.get_object()
        upload = VendorDocumentUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)
        doc = VendorDocument.objects.create(vendor=vendor, **upload.validated_data)
        return Response(VendorDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_contract(self, request, pk=None):
        vendor = self.get_object()
        write = VendorContractWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        record = VendorContractRecord.objects.create(vendor=vendor, **write.validated_data)
        return Response(
            VendorContractRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def add_payment(self, request, pk=None):
        vendor = self.get_object()
        write = VendorPaymentWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        record = VendorPaymentRecord.objects.create(vendor=vendor, **write.validated_data)
        return Response(
            VendorPaymentRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )
