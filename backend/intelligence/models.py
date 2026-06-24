from django.db import models

from core.models import Country, DataSource


class EconomicIndicator(models.Model):
    """Time-series metric from World Bank, IMF, central banks, etc."""

    class IndicatorType(models.TextChoices):
        GDP_GROWTH = "gdp_growth", "GDP Growth"
        INFLATION = "inflation", "Inflation"
        FX_RATE = "fx_rate", "FX Rate"
        TRADE_BALANCE = "trade_balance", "Trade Balance"
        CORRUPTION_INDEX = "corruption_index", "Corruption Perception"
        ELECTRICITY_ACCESS = "electricity_access", "Electricity Access"
        CUSTOM = "custom", "Custom"

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="indicators")
    indicator_type = models.CharField(max_length=32, choices=IndicatorType.choices)
    label = models.CharField(max_length=255)
    value = models.DecimalField(max_digits=18, decimal_places=6)
    unit = models.CharField(max_length=50, blank=True)
    period = models.DateField(help_text="Observation date or period end")
    source = models.ForeignKey(
        DataSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="indicators"
    )
    source_url = models.URLField(blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period"]
        indexes = [
            models.Index(fields=["country", "indicator_type", "-period"]),
        ]

    def __str__(self):
        return f"{self.country.code} — {self.label} ({self.period})"


class CountryRiskSnapshot(models.Model):
    """Aggregated risk view for dashboard display."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="risk_snapshots")
    overall_score = models.DecimalField(max_digits=5, decimal_places=2)
    political_risk = models.DecimalField(max_digits=5, decimal_places=2)
    regulatory_risk = models.DecimalField(max_digits=5, decimal_places=2)
    trade_risk = models.DecimalField(max_digits=5, decimal_places=2)
    summary = models.TextField(blank=True)
    as_of = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-as_of"]
        get_latest_by = "as_of"

    def __str__(self):
        return f"{self.country.code} risk @ {self.as_of}"
