from django.contrib import admin

from .models import Country, DataSource


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_eac_member", "currency_code")
    search_fields = ("code", "name")


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "country", "is_active", "last_checked_at")
    list_filter = ("source_type", "is_active", "country")
    search_fields = ("name", "url")
