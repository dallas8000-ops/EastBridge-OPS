from django.contrib import admin
from django.conf import settings
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),
    path("api/v1/regulatory/", include("regulatory.urls")),
    path("api/v1/playbooks/", include("playbooks.urls")),
    path("api/v1/vendors/", include("vendors.urls")),
    path("api/v1/intelligence/", include("intelligence.urls")),
    path("api/v1/assistant/", include("assistant.urls")),
    path("api/v1/ingestion/", include("ingestion.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/trade/", include("trade.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
