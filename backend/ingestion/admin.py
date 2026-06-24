from django.contrib import admin

from .models import IngestedItem, IngestionRun


@admin.register(IngestedItem)
class IngestedItemAdmin(admin.ModelAdmin):
    list_display = ("title", "data_source", "status", "published_at", "fetched_at")
    list_filter = ("status", "data_source")
    search_fields = ("title", "url", "external_id")


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("run_type", "started_at", "finished_at", "items_new", "items_failed")
