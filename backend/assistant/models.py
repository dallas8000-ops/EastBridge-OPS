from django.db import models


class EvidenceDocument(models.Model):
    """Indexed source document for RAG retrieval."""

    title = models.CharField(max_length=500)
    source_url = models.URLField()
    country_code = models.CharField(max_length=2, blank=True)
    category = models.CharField(max_length=64, blank=True)
    content = models.TextField()
    published_at = models.DateField(null=True, blank=True)
    indexed_at = models.DateTimeField(auto_now_add=True)
    embedding = models.JSONField(null=True, blank=True)
    embedding_dims = models.PositiveSmallIntegerField(default=0)
    embedding_model = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-indexed_at"]

    def __str__(self):
        return self.title


class AssistantQuery(models.Model):
    """Audit log: every AI answer must cite evidence."""

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistant_queries",
    )
    question = models.TextField()
    answer = models.TextField(blank=True)
    has_sufficient_evidence = models.BooleanField(default=False)
    refusal_reason = models.TextField(
        blank=True,
        help_text="Set when the assistant cannot answer without evidence.",
    )
    retrieval_method = models.CharField(max_length=32, default="hybrid")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "assistant queries"

    def __str__(self):
        return self.question[:80]


class Citation(models.Model):
    """Link between an assistant answer and source evidence."""

    query = models.ForeignKey(AssistantQuery, on_delete=models.CASCADE, related_name="citations")
    evidence = models.ForeignKey(
        EvidenceDocument, on_delete=models.CASCADE, related_name="citations"
    )
    excerpt = models.TextField()
    relevance_score = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        ordering = ["-relevance_score"]

    def __str__(self):
        return f"Citation for query {self.query_id}"
