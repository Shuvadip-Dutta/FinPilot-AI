from django.urls import path

from apps.research.views import CompanyResearchView, FinancialResearchView, KeyMetricsResearchView


urlpatterns = [
    path(
        "company/",
        CompanyResearchView.as_view(),
        name="company-research",
    ),
    path(
        "financials/",
        FinancialResearchView.as_view(),
        name="research-financials",
    ),
    path(
        "metrics/",
        KeyMetricsResearchView.as_view(),
        name="research-metrics",
    ),
]