from django.contrib import admin

from .models import Company


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