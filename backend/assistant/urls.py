from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssistantQueryViewSet

router = DefaultRouter()
router.register("queries", AssistantQueryViewSet, basename="assistant-query")

urlpatterns = [
    path("", include(router.urls)),
]
