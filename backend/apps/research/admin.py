from django.contrib import admin

from .models import Company, ResearchEvidence, ResearchSession


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "ticker",
        "name",
        "exchange",
        "country",
        "sector",
        "industry",
    )

    search_fields = (
        "ticker",
        "name",
        "isin",
        "sec_cik",
    )

    list_filter = (
        "country",
        "exchange",
        "sector",
    )


class ResearchEvidenceInline(admin.TabularInline):
    model = ResearchEvidence
    extra = 0
    readonly_fields = (
        "agent_name",
        "response",
        "tools_used",
        "structured_data",
        "created_at",
    )


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "thread_id",
        "ticker",
        "market",
        "route",
        "status",
        "latency_ms",
        "created_at",
    )

    search_fields = (
        "id",
        "thread_id",
        "ticker",
        "user_message",
    )

    list_filter = (
        "status",
        "route",
        "market",
        "created_at",
    )

    inlines = [ResearchEvidenceInline]


@admin.register(ResearchEvidence)
class ResearchEvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "agent_name",
        "created_at",
    )

    search_fields = (
        "agent_name",
        "session__ticker",
        "session__id",
    )

    list_filter = (
        "agent_name",
        "created_at",
    )