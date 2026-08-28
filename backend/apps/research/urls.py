from django.urls import path

from apps.research.views import CompanyResearchView, FinancialResearchView, KeyMetricsResearchView, NewsResearchView, HistoricalResearchView


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
    path(
        "news/",
        NewsResearchView.as_view(),
        name="research-news",
    ),
    path(
        "historical/",
        HistoricalResearchView.as_view(),
        name="research-historical",
    ),
]