from django.contrib import admin

from .models import Vendor, VendorContractRecord, VendorDocument, VendorPaymentRecord


class VendorDocumentInline(admin.TabularInline):
    model = VendorDocument
    extra = 0


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "verification_status", "risk_score", "updated_at")
    list_filter = ("verification_status", "country")
    search_fields = ("name", "registration_number")
    inlines = [VendorDocumentInline]


admin.site.register(VendorContractRecord)
admin.site.register(VendorPaymentRecord)
