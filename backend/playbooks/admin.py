from django.contrib import admin

from .models import Industry, MarketEntryPlaybook, PlaybookStep


class PlaybookStepInline(admin.TabularInline):
    model = PlaybookStep
    extra = 0


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")
    search_fields = ("slug", "name")


@admin.register(MarketEntryPlaybook)
class MarketEntryPlaybookAdmin(admin.ModelAdmin):
    list_display = ("origin_country", "target_country", "industry", "estimated_timeline_weeks", "generated_at")
    list_filter = ("target_country", "industry")
    inlines = [PlaybookStepInline]
