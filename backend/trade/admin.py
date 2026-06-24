from django.contrib import admin

from .models import TradeProcedure, TradeProcedureStep


class TradeProcedureStepInline(admin.TabularInline):
    model = TradeProcedureStep
    extra = 0


@admin.register(TradeProcedure)
class TradeProcedureAdmin(admin.ModelAdmin):
    list_display = ("title", "country", "activity_type", "estimated_days", "last_synced_at")
    list_filter = ("country", "activity_type", "source_portal")
    search_fields = ("title", "summary")
    inlines = [TradeProcedureStepInline]
