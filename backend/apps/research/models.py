import uuid
from django.conf import settings
from django.db import models


class Company(models.Model):
    ticker = models.CharField(max_length=20)
    name = models.CharField(max_length=255)

    isin = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        unique=True,
    )

    exchange = models.CharField(max_length=50)
    country = models.CharField(max_length=50)

    sector = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    industry = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    sec_cik = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
    )

    instrument_key = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    provider_symbols = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ticker"]
        constraints = [
            models.UniqueConstraint(
                fields=["ticker", "exchange"],
                name="unique_ticker_exchange",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.ticker})"


class ResearchSession(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_sessions",
    )
    thread_id = models.CharField(
        max_length=255,
        db_index=True,
    )
    user_message = models.TextField()

    ticker = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
    )

    market = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    route = models.CharField(max_length=50)

    status = models.CharField(
        max_length=20,
        default="COMPLETED",
    )

    final_synthesis = models.TextField(
        blank=True,
        null=True,
    )

    latency_ms = models.FloatField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        ticker_str = f" for {self.ticker}" if self.ticker else ""
        return f"ResearchSession {self.id}{ticker_str} ({self.route})"


class ResearchEvidence(models.Model):
    id = models.AutoField(primary_key=True)

    session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name="evidence_items",
    )

    agent_name = models.CharField(max_length=50)
    response = models.TextField()

    tools_used = models.JSONField(default=list)

    structured_data = models.JSONField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"ResearchEvidence {self.agent_name} (Session {self.session_id})"


class FinancialDocument(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PROCESSING = "PROCESSING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_FAILED = "FAILED"

    INGESTION_STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    SOURCE_UPLOAD = "UPLOAD"
    SOURCE_SEC_EDGAR = "SEC_EDGAR"

    SOURCE_TYPE_CHOICES = [
        (SOURCE_UPLOAD, "User Upload"),
        (SOURCE_SEC_EDGAR, "SEC EDGAR Filing"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="financial_documents",
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPE_CHOICES,
        default=SOURCE_UPLOAD,
        db_index=True,
    )
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveBigIntegerField()
    file_path = models.CharField(max_length=512)
    ticker = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    market = models.CharField(max_length=10, blank=True, null=True)
    ingestion_status = models.CharField(
        max_length=20,
        choices=INGESTION_STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    chunk_count = models.PositiveIntegerField(default=0)
    ingestion_error = models.TextField(blank=True, null=True)

    # SEC EDGAR metadata fields
    sec_form = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    sec_accession_number = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    sec_filing_date = models.DateField(blank=True, null=True)
    sec_report_date = models.DateField(blank=True, null=True)
    sec_cik = models.CharField(max_length=20, blank=True, null=True)
    source_url = models.URLField(max_length=1024, blank=True, null=True)
    primary_doc_description = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "sec_accession_number"],
                condition=models.Q(sec_accession_number__isnull=False),
                name="unique_user_sec_accession",
            )
        ]

    def __str__(self):
        source_label = f" [{self.source_type}]" if self.source_type != self.SOURCE_UPLOAD else ""
        return f"{self.filename}{source_label} ({self.ingestion_status})"
