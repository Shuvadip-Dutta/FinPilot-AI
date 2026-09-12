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

    def test_backward_compatibility_document_evidence_default(self):
        """Verify ResearchContext defaults document_evidence to empty list when omitted."""
        ctx = ResearchContext(ticker="AAPL", market="US")
        self.assertEqual(ctx.document_evidence, [])
        dump = ctx.model_dump()
        self.assertIn("document_evidence", dump)
        self.assertEqual(dump["document_evidence"], [])

    def test_sec_evidence_serialization_and_deserialization(self):
        """Verify ResearchContext with SEC document evidence serializes and deserializes successfully."""
        sec_evidence = {
            "document_id": "11111111-2222-3333-4444-555555555555",
            "chunk_id": "sec-chunk-001",
            "text": "Apple Inc. reports record quarterly revenue of $89.5 billion for Q4 2023.",
            "score": 0.92,
            "source_type": "SEC_EDGAR",
            "sec_form": "10-K",
            "sec_cik": "0000320193",
            "sec_accession_number": "0000320193-23-000106",
            "sec_filing_date": "2023-11-03",
            "sec_report_date": "2023-09-30",
            "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
            "metadata": {
                "document_name": "AAPL 10-K (2023-11-03)",
                "ticker": "AAPL",
                "market": "US",
                "page_start": 1,
                "page_count": 120,
            },
        }

        ctx = ResearchContext(
            ticker="AAPL",
            market="US",
            document_evidence=[sec_evidence],
        )

        self.assertEqual(len(ctx.document_evidence), 1)
        self.assertEqual(ctx.document_evidence[0]["sec_form"], "10-K")
        self.assertEqual(ctx.document_evidence[0]["sec_accession_number"], "0000320193-23-000106")

        dump = ctx.model_dump()
        json_str = json.dumps(dump, default=str)
        self.assertIn("0000320193-23-000106", json_str)
        self.assertIn("SEC_EDGAR", json_str)

        # Deserialize back to ResearchContext
        reloaded = ResearchContext.model_validate(json.loads(json_str))
        self.assertEqual(len(reloaded.document_evidence), 1)
        self.assertEqual(reloaded.document_evidence[0]["chunk_id"], "sec-chunk-001")
        self.assertEqual(reloaded.document_evidence[0]["score"], 0.92)
        self.assertEqual(reloaded.document_evidence[0]["source_type"], "SEC_EDGAR")
        self.assertEqual(reloaded.document_evidence[0]["sec_cik"], "0000320193")

    def test_sec_provenance_acceptance(self):
        """Verify sec_edgar is accepted as the canonical SEC provider identifier in ProviderProvenance."""
        prov = ProviderProvenance(
            primary_provider="sec_edgar",
            source="sec_edgar",
            fallback_used=False,
            data_status="complete",
        )
        ctx = ResearchContext(
            ticker="MSFT",
            market="US",
            provenance={"sec_filings": prov},
        )

        self.assertEqual(ctx.provenance["sec_filings"].primary_provider, "sec_edgar")
        self.assertEqual(ctx.provenance["sec_filings"].source, "sec_edgar")
        self.assertFalse(ctx.provenance["sec_filings"].fallback_used)
        self.assertEqual(ctx.provenance["sec_filings"].data_status, "complete")

        dump = ctx.model_dump()
        self.assertEqual(dump["provenance"]["sec_filings"]["primary_provider"], "sec_edgar")

    def test_financial_document_serializer_exposes_sec_fields(self):
        """Verify FinancialDocumentSerializer includes all 8 SEC metadata fields for an SEC filing."""
        import datetime
        import uuid
        from apps.research.document_serializers import FinancialDocumentSerializer
        from apps.research.models import FinancialDocument

        doc = FinancialDocument(
            id=uuid.uuid4(),
            filename="AAPL_0000320193-23-000106_filing.htm",
            content_type="text/html",
            file_size=2048576,
            file_path="/media/documents/sec/filing.htm",
            ticker="AAPL",
            market="US",
            ingestion_status=FinancialDocument.STATUS_COMPLETED,
            chunk_count=85,
            ingestion_error=None,
            source_type=FinancialDocument.SOURCE_SEC_EDGAR,
            sec_form="10-K",
            sec_filing_date=datetime.date(2023, 11, 3),
            sec_report_date=datetime.date(2023, 9, 30),
            sec_cik="0000320193",
            sec_accession_number="0000320193-23-000106",
            primary_doc_description="Annual Report for Year Ended September 30, 2023",
            source_url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
        )

        serializer = FinancialDocumentSerializer(doc)
        data = serializer.data

        # Verify all 8 SEC fields are present and accurate
        self.assertEqual(data["source_type"], "SEC_EDGAR")
        self.assertEqual(data["sec_form"], "10-K")
        self.assertEqual(data["sec_filing_date"], "2023-11-03")
        self.assertEqual(data["sec_report_date"], "2023-09-30")
        self.assertEqual(data["sec_cik"], "0000320193")
        self.assertEqual(data["sec_accession_number"], "0000320193-23-000106")
        self.assertEqual(data["primary_doc_description"], "Annual Report for Year Ended September 30, 2023")
        self.assertEqual(data["source_url"], "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm")

        # Verify base fields are still present
        self.assertEqual(data["ticker"], "AAPL")
        self.assertEqual(data["market"], "US")
        self.assertEqual(data["chunk_count"], 85)
        self.assertEqual(data["ingestion_status"], "COMPLETED")

    def test_financial_document_serializer_uploaded_document_defaults(self):
        """Verify FinancialDocumentSerializer retains null/default SEC fields for uploaded documents."""
        import uuid
        from apps.research.document_serializers import FinancialDocumentSerializer
        from apps.research.models import FinancialDocument

        doc = FinancialDocument(
            id=uuid.uuid4(),
            filename="quarterly_report.pdf",
            content_type="application/pdf",
            file_size=512000,
            file_path="/media/documents/upload.pdf",
            ticker="INFY",
            market="IN",
            ingestion_status=FinancialDocument.STATUS_COMPLETED,
            chunk_count=12,
            ingestion_error=None,
            source_type=FinancialDocument.SOURCE_UPLOAD,
        )

        serializer = FinancialDocumentSerializer(doc)
        data = serializer.data

        self.assertEqual(data["source_type"], "UPLOAD")
        self.assertIsNone(data["sec_form"])
        self.assertIsNone(data["sec_filing_date"])
        self.assertIsNone(data["sec_report_date"])
        self.assertIsNone(data["sec_cik"])
        self.assertIsNone(data["sec_accession_number"])
        self.assertIsNone(data["primary_doc_description"])
        self.assertIsNone(data["source_url"])
