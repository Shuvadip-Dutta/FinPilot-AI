import json
from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.research.services.schemas import (
    CompanyProfile,
    FinancialMetric,
    FinancialStatement,
    HistoricalCandle,
    HistoricalMarketData,
    KeyMetric,
    KeyMetricsResearch,
    NewsArticle,
    NewsResearch,
)


class ResearchContextContractTestCase(SimpleTestCase):

    def test_minimal_research_context_creation(self):
        ctx = ResearchContext(ticker="LT", market="IN")

        self.assertEqual(ctx.ticker, "LT")
        self.assertEqual(ctx.market, "IN")
        self.assertIsNone(ctx.company_profile)
        self.assertIsNone(ctx.financials)
        self.assertIsNone(ctx.key_metrics)
        self.assertIsNone(ctx.market_data)
        self.assertIsNone(ctx.news)
        self.assertEqual(ctx.provenance, {})

    def test_full_research_context_creation(self):
        profile = CompanyProfile(
            ticker="LT",
            name="Larsen & Toubro Ltd",
            exchange="NSE",
            country="India",
            sector="Industrials",
        )

        statement = FinancialStatement(
            statement_type="INC",
            fiscal_year="2026",
            end_date="2026-03-31",
            period_type="Annual",
            period_length=12,
            metrics=[FinancialMetric(name="Revenue", key="revenue", value=200000.0)],
        )

        key_metrics = KeyMetricsResearch(
            ticker="LT",
            metrics=[
                KeyMetric(
                    category="valuation",
                    name="P/E Ratio",
                    key="pe_ratio",
                    value=32.5,
                )
            ],
        )

        market_data = HistoricalMarketData(
            ticker="LT",
            candles=[
                HistoricalCandle(
                    timestamp="2026-09-01T00:00:00+05:30",
                    open=3500.0,
                    high=3550.0,
                    low=3480.0,
                    close=3520.0,
                    volume=1500000,
                    open_interest=0,
                )
            ],
        )

        news = NewsResearch(
            ticker="LT",
            articles=[
                NewsArticle(
                    title="L&T wins new infrastructure order",
                    summary="L&T secures major order in Middle East.",
                    url="https://example.com/lt-news",
                    source="Moneycontrol",
                    published_at="2026-09-02T10:00:00Z",
                )
            ],
        )

        prov = {
            "financials": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            ),
            "news": ProviderProvenance(
                primary_provider="news_aggregator",
                source="marketaux",
                fallback_used=True,
                data_status="partial",
                fallback_reason="indian_api_unavailable",
            ),
        }

        ctx = ResearchContext(
            ticker="LT",
            market="IN",
            company_profile=profile,
            financials=[statement],
            key_metrics=key_metrics,
            market_data=market_data,
            news=news,
            provenance=prov,
        )

        self.assertEqual(ctx.company_profile.name, "Larsen & Toubro Ltd")
        self.assertEqual(len(ctx.financials), 1)
        self.assertEqual(ctx.key_metrics.metrics[0].value, 32.5)
        self.assertEqual(len(ctx.market_data.candles), 1)
        self.assertEqual(len(ctx.news.articles), 1)
        self.assertEqual(ctx.provenance["financials"].source, "upstox")
        self.assertTrue(ctx.provenance["news"].fallback_used)

    def test_optional_missing_sections(self):
        profile = CompanyProfile(
            ticker="RELIANCE",
            name="Reliance Industries",
            exchange="NSE",
            country="India",
        )

        ctx = ResearchContext(
            ticker="RELIANCE",
            market="IN",
            company_profile=profile,
        )

        self.assertIsNotNone(ctx.company_profile)
        self.assertIsNone(ctx.financials)
        self.assertIsNone(ctx.key_metrics)
        self.assertIsNone(ctx.market_data)
        self.assertIsNone(ctx.news)

    def test_model_dump_json_serializable(self):
        profile = CompanyProfile(
            ticker="TCS",
            name="Tata Consultancy Services",
            exchange="NSE",
            country="India",
        )

        statement = FinancialStatement(
            statement_type="INC",
            fiscal_year="2026",
            end_date="2026-03-31",
            period_type="Annual",
            period_length=12,
            metrics=[FinancialMetric(name="Revenue", key="revenue", value=150000.0)],
        )

        prov = {
            "company_profile": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }

        ctx = ResearchContext(
            ticker="TCS",
            market="IN",
            company_profile=profile,
            financials=[statement],
            provenance=prov,
        )

        dump = ctx.model_dump()
        self.assertIsInstance(dump, dict)
        self.assertEqual(dump["ticker"], "TCS")
        self.assertEqual(dump["company_profile"]["name"], "Tata Consultancy Services")
        self.assertEqual(dump["financials"][0]["metrics"][0]["value"], 150000.0)
        self.assertEqual(dump["provenance"]["company_profile"]["source"], "upstox")

        # Verify JSON serialization works without error
        json_str = json.dumps(dump, default=str)
        self.assertIn("Tata Consultancy Services", json_str)

    def test_invalid_data_status_validation(self):
        with self.assertRaises(ValidationError) as err:
            ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                data_status="invalid_status_value",
            )

        self.assertIn("Invalid data_status", str(err.exception))
