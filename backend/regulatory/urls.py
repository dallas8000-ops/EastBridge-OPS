from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChangeAlertSubscriptionViewSet, RegulatoryChangeViewSet

router = DefaultRouter()
router.register("changes", RegulatoryChangeViewSet)
router.register("alerts", ChangeAlertSubscriptionViewSet, basename="alert")

urlpatterns = [
    path("", include(router.urls)),
]
