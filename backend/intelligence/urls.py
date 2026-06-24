from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CountryRiskSnapshotViewSet, EconomicIndicatorViewSet

router = DefaultRouter()
router.register("indicators", EconomicIndicatorViewSet)
router.register("risk", CountryRiskSnapshotViewSet, basename="risk")

urlpatterns = [
    path("", include(router.urls)),
]
