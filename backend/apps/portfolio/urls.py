from django.urls import path

from apps.portfolio.views import (
    HoldingDetailView,
    HoldingListCreateView,
    PortfolioBacktestView,
    PortfolioDetailView,
    PortfolioListCreateView,
    PortfolioRiskView,
)

urlpatterns = [
    path(
        "",
        PortfolioListCreateView.as_view(),
        name="portfolio-list-create",
    ),
    path(
        "<uuid:pk>/",
        PortfolioDetailView.as_view(),
        name="portfolio-detail",
    ),
    path(
        "<uuid:portfolio_id>/risk/",
        PortfolioRiskView.as_view(),
        name="portfolio-risk",
    ),
    path(
        "<uuid:portfolio_id>/backtest/",
        PortfolioBacktestView.as_view(),
        name="portfolio-backtest",
    ),
    path(
        "<uuid:portfolio_pk>/holdings/",
        HoldingListCreateView.as_view(),
        name="holding-list-create",
    ),
    path(
        "<uuid:portfolio_pk>/holdings/<uuid:pk>/",
        HoldingDetailView.as_view(),
        name="holding-detail",
    ),
    path(
        "holdings/<uuid:pk>/",
        HoldingDetailView.as_view(),
        name="holding-detail-direct",
    ),
]

