from django.urls import path

from apps.research.document_views import (
    FinancialDocumentDetailView,
    FinancialDocumentListCreateView,
    FinancialDocumentSearchView,
)
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
        "documents/",
        FinancialDocumentListCreateView.as_view(),
        name="financial-documents-list-create",
    ),
    path(
        "documents/search/",
        FinancialDocumentSearchView.as_view(),
        name="financial-documents-search",
    ),
    path(
        "documents/<uuid:document_id>/",
        FinancialDocumentDetailView.as_view(),
        name="financial-documents-detail",
    ),
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
