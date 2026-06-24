from django.db import connection
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Country, DataSource
from .serializers import CountrySerializer, DataSourceSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False

    return Response(
        {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
        }
    )

class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    search_fields = ("code", "name")
    filterset_fields = ("is_eac_member",)


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DataSource.objects.select_related("country").filter(is_active=True)
    serializer_class = DataSourceSerializer
    search_fields = ("name", "url")
    filterset_fields = ("source_type", "country")
