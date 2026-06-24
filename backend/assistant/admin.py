from django.contrib import admin

from .models import AssistantQuery, Citation, EvidenceDocument


class CitationInline(admin.TabularInline):
    model = Citation
    extra = 0


@admin.register(EvidenceDocument)
class EvidenceDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "country_code", "category", "published_at", "indexed_at")
    list_filter = ("country_code", "category")
    search_fields = ("title", "content")


@admin.register(AssistantQuery)
class AssistantQueryAdmin(admin.ModelAdmin):
    list_display = ("question", "has_sufficient_evidence", "created_at")
    inlines = [CitationInline]
