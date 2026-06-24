from django.db import models


class IngestedItem(models.Model):
    """Tracks fetched content for deduplication and audit."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        INDEXED = "indexed", "Indexed"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    data_source = models.ForeignKey(
        "core.DataSource", on_delete=models.CASCADE, related_name="ingested_items"
    )
    external_id = models.CharField(max_length=512)
    content_hash = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=2048)
    raw_content = models.TextField(blank=True)
    published_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    error_message = models.TextField(blank=True)
    evidence_id = models.PositiveIntegerField(null=True, blank=True)
    regulatory_change_id = models.PositiveIntegerField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["data_source", "external_id"],
                name="unique_source_external_id",
            ),
        ]

    def __str__(self):
        return self.title


class IngestionRun(models.Model):
    """Log of each ingestion batch execution."""

    class RunType(models.TextChoices):
        REGULATORY = "regulatory", "Regulatory"
        ECONOMIC = "economic", "Economic"
        FULL = "full", "Full"

    run_type = models.CharField(max_length=16, choices=RunType.choices)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    items_fetched = models.PositiveIntegerField(default=0)
    items_new = models.PositiveIntegerField(default=0)
    items_failed = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.run_type} @ {self.started_at}"
