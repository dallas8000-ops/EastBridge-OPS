from django.db import models


class Country(models.Model):
    """EAC and East Africa target markets."""

    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)
    is_eac_member = models.BooleanField(default=False)
    currency_code = models.CharField(max_length=3, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class DataSource(models.Model):
    """Official portal, API, RSS feed, or document repository."""

    class SourceType(models.TextChoices):
        TAX_AUTHORITY = "tax_authority", "Tax Authority"
        INVESTMENT_AUTHORITY = "investment_authority", "Investment Authority"
        CUSTOMS = "customs", "Customs"
        EAC_TRADE = "eac_trade", "EAC Trade Portal"
        DATA_PROTECTION = "data_protection", "Data Protection"
        LABOR = "labor", "Labor / Employment"
        CENTRAL_BANK = "central_bank", "Central Bank"
        TRADE_PORTAL = "trade_portal", "Trade Information Portal"
        WORLD_BANK = "world_bank", "World Bank"
        IMF = "imf", "IMF"
        RSS = "rss", "RSS Feed"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    url = models.URLField()
    feed_url = models.URLField(
        blank=True,
        help_text="RSS/Atom feed URL when different from the portal URL.",
    )
    ingestion_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Fetcher config, e.g. {"type": "rss"} or {"type": "html_list", "list_url": "..."}',
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True, related_name="data_sources"
    )
    is_active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
