from django.db import models

from core.models import Country


class TradeProcedure(models.Model):
    """Structured trade procedure from EAC Trade Information Portal."""

    class ActivityType(models.TextChoices):
        IMPORT = "import", "Import"
        EXPORT = "export", "Export"
        TRANSIT = "transit", "Transit"
        REGISTRATION = "registration", "Business Registration"
        LICENSING = "licensing", "Licensing"
        CUSTOMS = "customs", "Customs Clearance"
        OTHER = "other", "Other"

    external_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="trade_procedures")
    activity_type = models.CharField(max_length=32, choices=ActivityType.choices, default=ActivityType.OTHER)
    summary = models.TextField(blank=True)
    source_url = models.URLField()
    source_portal = models.CharField(max_length=100, default="EAC TIP")
    estimated_days = models.PositiveIntegerField(null=True, blank=True)
    estimated_cost = models.CharField(max_length=255, blank=True)
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["country__code", "title"]
        indexes = [
            models.Index(fields=["country", "activity_type"]),
        ]

    def __str__(self):
        return f"{self.country.code}: {self.title}"


class TradeProcedureStep(models.Model):
    procedure = models.ForeignKey(
        TradeProcedure, on_delete=models.CASCADE, related_name="steps"
    )
    sort_order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    description = models.TextField()
    responsible_agency = models.CharField(max_length=255, blank=True)
    documents_required = models.JSONField(default=list, blank=True)
    estimated_days = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title
