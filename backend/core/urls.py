from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CountryViewSet, DataSourceViewSet, health

router = DefaultRouter()
router.register("countries", CountryViewSet)
router.register("sources", DataSourceViewSet)

urlpatterns = [
    path("health/", health),
    path("", include(router.urls)),
]