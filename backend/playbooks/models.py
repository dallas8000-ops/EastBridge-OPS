from django.db import models

from core.models import Country


class Industry(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "industries"

    def __str__(self):
        return self.name


class MarketEntryPlaybook(models.Model):
    """Generated market-entry guide for a company profile entering a country."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="playbooks",
        null=True,
        blank=True,
    )
    origin_country = models.CharField(max_length=2, help_text="ISO country code, e.g. DE")
    industry = models.ForeignKey(Industry, on_delete=models.PROTECT, related_name="playbooks")
    target_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="playbooks")
    company_description = models.TextField(blank=True)
    estimated_timeline_weeks = models.PositiveIntegerField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.origin_country} → {self.target_country.code} ({self.industry.name})"


class PlaybookStep(models.Model):
    class StepType(models.TextChoices):
        REGISTRATION = "registration", "Registration"
        TAX = "tax", "Tax Obligations"
        IMPORT = "import", "Import Rules"
        PERMIT = "permit", "Permits & Licenses"
        PAYMENT = "payment", "Payment Options"
        PARTNER_RISK = "partner_risk", "Local Partner Risks"
        DOCUMENT = "document", "Required Documents"
        COMPLIANCE = "compliance", "Compliance Checklist"
        LOGISTICS = "logistics", "Logistics / Customs"

    playbook = models.ForeignKey(MarketEntryPlaybook, on_delete=models.CASCADE, related_name="steps")
    step_type = models.CharField(max_length=32, choices=StepType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField()
    source_url = models.URLField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title
