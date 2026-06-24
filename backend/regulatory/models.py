from django.db import models

from core.models import Country, DataSource


class RegulatoryChange(models.Model):
    """Detected regulatory, tax, customs, or compliance change."""

    class Category(models.TextChoices):
        TAX = "tax", "Tax"
        INVESTMENT = "investment", "Investment"
        CUSTOMS = "customs", "Customs / Import-Export"
        EAC_TRADE = "eac_trade", "EAC Trade"
        DATA_PROTECTION = "data_protection", "Data Protection"
        LABOR = "labor", "Labor / Contractor"
        OTHER = "other", "Other"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    title = models.CharField(max_length=500)
    summary = models.TextField()
    business_impact = models.TextField()
    required_action = models.TextField()
    category = models.CharField(max_length=32, choices=Category.choices)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.choices, default=RiskLevel.MEDIUM)
    source_url = models.URLField()
    source = models.ForeignKey(
        DataSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="changes"
    )
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="regulatory_changes")
    published_at = models.DateField(null=True, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [
            models.Index(fields=["country", "category", "-detected_at"]),
        ]

    def __str__(self):
        return self.title


class ChangeAlertSubscription(models.Model):
    """User/org alert when rules update in a country or category."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="alert_subscriptions",
        null=True,
        blank=True,
    )
    email = models.EmailField()
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True, related_name="alert_subscriptions"
    )
    category = models.CharField(
        max_length=32, choices=RegulatoryChange.Category.choices, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
