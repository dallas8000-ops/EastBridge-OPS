from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import IndustryViewSet, MarketEntryPlaybookViewSet, PlaybookStepViewSet

router = DefaultRouter()
router.register("industries", IndustryViewSet)
router.register("steps", PlaybookStepViewSet, basename="playbook-step")
router.register("", MarketEntryPlaybookViewSet, basename="playbook")

urlpatterns = [
    path("", include(router.urls)),
]
