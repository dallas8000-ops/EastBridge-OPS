from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from accounts.permissions import get_user_organization

from .models import ChangeAlertSubscription, RegulatoryChange
from .serializers import ChangeAlertSubscriptionSerializer, RegulatoryChangeSerializer


class RegulatoryChangeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = RegulatoryChange.objects.select_related("country", "source")
    serializer_class = RegulatoryChangeSerializer
    search_fields = ("title", "summary", "business_impact")
    filterset_fields = ("country", "category", "risk_level")
    ordering_fields = ("detected_at", "published_at", "risk_level")


class ChangeAlertSubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangeAlertSubscriptionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        org = get_user_organization(self.request)
        if not org:
            return ChangeAlertSubscription.objects.none()
        return ChangeAlertSubscription.objects.filter(organization=org).select_related("country")

    def create(self, request, *args, **kwargs):
        org = get_user_organization(request)
        if not org:
            return Response({"detail": "Organization required"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = serializer.save(organization=org)
        return Response(ChangeAlertSubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)
