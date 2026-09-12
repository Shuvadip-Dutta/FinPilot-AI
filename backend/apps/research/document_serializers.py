"""Serializers for financial document upload, search, and retrieval."""

from rest_framework import serializers
from apps.research.models import FinancialDocument


class FinancialDocumentSerializer(serializers.ModelSerializer):
    """Serializer for FinancialDocument details."""

    class Meta:
        model = FinancialDocument
        fields = [
            "id",
            "filename",
            "content_type",
            "file_size",
            "ticker",
            "market",
            "ingestion_status",
            "chunk_count",
            "ingestion_error",
            "created_at",
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for validating document uploads."""

    file = serializers.FileField(required=True)
    ticker = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    market = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError("File is required.")

        if value.size == 0:
            raise serializers.ValidationError("Uploaded file is empty.")

        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File exceeds maximum allowed size of 10 MB.")

        filename = value.name.lower() if value.name else ""
        valid_extensions = (".pdf", ".txt", ".text")
        valid_content_types = ("application/pdf", "text/plain", "text/csv")

        content_type = getattr(value, "content_type", "").lower()
        has_valid_ext = any(filename.endswith(ext) for ext in valid_extensions)
        has_valid_mime = content_type in valid_content_types or not content_type or content_type == "application/octet-stream"

        if not (has_valid_ext and has_valid_mime):
            raise serializers.ValidationError("Only PDF and TXT files are supported.")

        return value

    def validate_ticker(self, value):
        if value:
            return value.strip().upper()
        return None

    def validate_market(self, value):
        if value:
            return value.strip().upper()
        return None


class DocumentSearchSerializer(serializers.Serializer):
    """Serializer for searching indexed financial documents."""

    query = serializers.CharField(required=True, min_length=1, trim_whitespace=True)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=10)
    ticker = serializers.CharField(required=False, allow_blank=True, max_length=20)
    market = serializers.CharField(required=False, allow_blank=True, max_length=10)
    source_type = serializers.CharField(required=False, allow_blank=True, max_length=20)
    sec_form = serializers.CharField(required=False, allow_blank=True, max_length=20)
    sec_cik = serializers.CharField(required=False, allow_blank=True, max_length=20)
    sec_accession_number = serializers.CharField(required=False, allow_blank=True, max_length=50)
    document_id = serializers.UUIDField(required=False, allow_null=True)
    filing_date_from = serializers.DateField(required=False, allow_null=True)
    filing_date_to = serializers.DateField(required=False, allow_null=True)
    report_date_from = serializers.DateField(required=False, allow_null=True)
    report_date_to = serializers.DateField(required=False, allow_null=True)

    def validate_query(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Query must not be blank.")
        return cleaned

    def validate_ticker(self, value):
        if value:
            cleaned = value.strip().upper()
            return cleaned if cleaned else None
        return None

    def validate_market(self, value):
        if value:
            cleaned = value.strip().upper()
            return cleaned if cleaned else None
        return None

    def validate_source_type(self, value):
        if value:
            cleaned = value.strip().upper()
            return cleaned if cleaned else None
        return None

    def validate_sec_form(self, value):
        if value:
            cleaned = value.strip()
            return cleaned if cleaned else None
        return None

    def validate_sec_cik(self, value):
        if value:
            cleaned = value.strip()
            return cleaned if cleaned else None
        return None

    def validate_sec_accession_number(self, value):
        if value:
            cleaned = value.strip()
            return cleaned if cleaned else None
        return None

    def validate(self, attrs):
        filing_from = attrs.get("filing_date_from")
        filing_to = attrs.get("filing_date_to")
        if filing_from and filing_to and filing_from > filing_to:
            raise serializers.ValidationError(
                {"filing_date_from": "filing_date_from must be before or equal to filing_date_to."}
            )

        report_from = attrs.get("report_date_from")
        report_to = attrs.get("report_date_to")
        if report_from and report_to and report_from > report_to:
            raise serializers.ValidationError(
                {"report_date_from": "report_date_from must be before or equal to report_date_to."}
            )

        return attrs
