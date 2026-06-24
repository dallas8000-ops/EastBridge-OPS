from django.contrib import admin

from .models import ChangeAlertSubscription, RegulatoryChange


@admin.register(RegulatoryChange)
class RegulatoryChangeAdmin(admin.ModelAdmin):
    list_display = ("title", "country", "category", "risk_level", "detected_at", "published_at")
    list_filter = ("category", "risk_level", "country")
    search_fields = ("title", "summary", "business_impact")


@admin.register(ChangeAlertSubscription)
class ChangeAlertSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "country", "category", "is_active", "created_at")
    list_filter = ("is_active", "country", "category")
