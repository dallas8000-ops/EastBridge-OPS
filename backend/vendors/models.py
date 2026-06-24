from django.db import models

from core.models import Country


class Vendor(models.Model):
    """Local supplier or contractor for due diligence."""

    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_REVIEW = "in_review", "In Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        FLAGGED = "flagged", "Flagged"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="vendors",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="vendors")
    business_profile = models.TextField(blank=True)
    verification_status = models.CharField(
        max_length=16,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=50.0)
    red_flags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class VendorDocument(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=100)
    file = models.FileField(upload_to="vendor_documents/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.vendor.name} — {self.document_type}"


class VendorContractRecord(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="contracts")
    contract_ref = models.CharField(max_length=100)
    value_usd = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.contract_ref


class VendorPaymentRecord(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="payments")
    amount_usd = models.DecimalField(max_digits=14, decimal_places=2)
    payment_date = models.DateField()
    status = models.CharField(max_length=32, default="completed")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.vendor.name} — {self.payment_date}"
