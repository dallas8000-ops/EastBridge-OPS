from django.contrib import admin

from .models import CountryRiskSnapshot, EconomicIndicator


@admin.register(EconomicIndicator)
class EconomicIndicatorAdmin(admin.ModelAdmin):
    list_display = ("country", "indicator_type", "label", "value", "unit", "period")
    list_filter = ("indicator_type", "country")


@admin.register(CountryRiskSnapshot)
class CountryRiskSnapshotAdmin(admin.ModelAdmin):
    list_display = ("country", "overall_score", "as_of")
    list_filter = ("country",)
