from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import get_user_organization
from core.models import Country

from .generator import generate_playbook
from .models import Industry, MarketEntryPlaybook, PlaybookStep
from .serializers import (
    IndustrySerializer,
    MarketEntryPlaybookSerializer,
    PlaybookGenerateSerializer,
    PlaybookStepSerializer,
)


class IndustryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Industry.objects.all()
    serializer_class = IndustrySerializer
    lookup_field = "slug"


class MarketEntryPlaybookViewSet(
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = MarketEntryPlaybookSerializer
    filterset_fields = ("target_country", "origin_country", "industry")
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = MarketEntryPlaybook.objects.select_related(            "target_country", "industry", "organization"
        ).prefetch_related("steps")
        org = get_user_organization(self.request)
        if org and self.request.user.is_authenticated:
            return qs.filter(organization=org)
        return qs.none()

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def generate(self, request):
        serializer = PlaybookGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_user_organization(request)
        if not org:
            return Response({"detail": "Organization required"}, status=status.HTTP_403_FORBIDDEN)

        try:
            industry = Industry.objects.get(slug=data["industry_slug"])
            target = Country.objects.get(code=data["target_country_code"].upper())
        except (Industry.DoesNotExist, Country.DoesNotExist) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        playbook = generate_playbook(
            origin_country=data["origin_country"],
            industry=industry,
            target_country=target,
            company_description=data.get("company_description", ""),
            organization=org,
        )

        return Response(
            MarketEntryPlaybookSerializer(playbook).data,
            status=status.HTTP_201_CREATED,
        )


class PlaybookStepViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PlaybookStepSerializer
    http_method_names = ["patch", "head", "options"]

    def get_queryset(self):
        org = get_user_organization(self.request)
        if not org:
            return PlaybookStep.objects.none()
        return PlaybookStep.objects.filter(playbook__organization=org).select_related("playbook")

    def partial_update(self, request, *args, **kwargs):
        allowed = {"is_completed"}
        if set(request.data.keys()) - allowed:
            return Response(
                {"detail": "Only is_completed can be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)
