from django.urls import path

from apps.research.views import (
    CompanyResearchView,
    FinancialResearchView,
    HistoricalResearchView,
    KeyMetricsResearchView,
    NewsResearchView,
    ResearchSessionDetailView,
    ResearchSessionListView,
)


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
    path(
        "sessions/",
        ResearchSessionListView.as_view(),
        name="research-session-list",
    ),
    path(
        "sessions/<uuid:session_id>/",
        ResearchSessionDetailView.as_view(),
        name="research-session-detail",
    ),
]