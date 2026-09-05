import json
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase

from apps.ai.agents.financial import FinancialAnalysisAgent, FinancialAnalysisContextBuilder
from apps.ai.exceptions import LLMError
from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    LLMUsage,
    TokenBudgetManager,
)
from apps.research.services.schemas import (
    CompanyProfile,
    FinancialMetric,
    FinancialStatement,
    KeyMetric,
    KeyMetricsResearch,
)


class FinancialAnalysisAgentTestCase(SimpleTestCase):


    def test_agent_name(self):
        agent = FinancialAnalysisAgent()

        self.assertEqual(agent.name, "financial")

    def test_successful_financial_analysis(self):
        financials_tool = self._financials_tool()
        key_metrics_tool = self._key_metrics_tool()
        llm_service = MagicMock(return_value="Reliance revenue is stable and margins are healthy.")

        agent = FinancialAnalysisAgent(
            financials_tool=financials_tool,
            key_metrics_tool=key_metrics_tool,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Analyze Reliance financials.")

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(
            result.response,
            "Reliance revenue is stable and margins are healthy.",
        )
        self.assertEqual(
            result.tools_used,
            ["get_financials", "get_key_metrics"],
        )
        llm_service.assert_called_once()

        messages = llm_service.call_args[0][0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("financial data provided in this prompt", messages[0]["content"])
        self.assertIn("RELIANCE", messages[1]["content"])
        self.assertIn("financial_statement_data", messages[1]["content"])
        self.assertIn("key_metrics_data", messages[1]["content"])
        self.assertEqual(result.data["ticker"], "RELIANCE")
        self.assertEqual(result.data["financial_statement_data"][0]["period"], "2024")
        self.assertEqual(result.data["key_metrics_data"][0]["key"], "pe_ratio")

    @patch("apps.ai.agents.financial.LLMService")
    def test_uses_reasoning_model_by_default(self, mock_llm_service):
        financials_tool = self._financials_tool()
        key_metrics_tool = self._key_metrics_tool()

        FinancialAnalysisAgent(
            financials_tool=financials_tool,
            key_metrics_tool=key_metrics_tool,
            ticker="RELIANCE",
        )

        mock_llm_service.assert_called_once_with(model="financial")

    def test_research_tool_failure_is_returned_in_result(self):
        def failing_financials_tool(**kwargs):
            raise ValueError("Financial data unavailable")

        agent = FinancialAnalysisAgent(
            financials_tool=failing_financials_tool,
            key_metrics_tool=self._key_metrics_tool(),
            ticker="RELIANCE",
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIn("Financial data unavailable", result.response)
        self.assertEqual(result.tools_used, [])

    def test_run_returns_agent_result(self):
        agent = FinancialAnalysisAgent(
            financials_tool=self._financials_tool(),
            key_metrics_tool=self._key_metrics_tool(),
            ticker="RELIANCE",
            llm_service=lambda messages: "Analysis complete.",
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIsInstance(result, AgentResult)

    def test_injected_tools_avoid_real_api_or_llm_calls(self):
        calls = []

        def financials_tool(**kwargs):
            calls.append(("financials", kwargs))
            return {"financials": [{"period": "2024", "metrics": []}]}

        def key_metrics_tool(**kwargs):
            calls.append(("key_metrics", kwargs))
            return {"metrics": [{"key": "pe_ratio"}]}

        llm_service = MagicMock(return_value="Financial metrics look healthy.")

        agent = FinancialAnalysisAgent(
            financials_tool=financials_tool,
            key_metrics_tool=key_metrics_tool,
            ticker="TCS",
            llm_service=llm_service,
        )

        agent.run("Analyze TCS financials.")

        self.assertEqual(
            calls,
            [
                ("financials", {"ticker": "TCS", "market": "IN"}),
                ("key_metrics", {"ticker": "TCS", "market": "IN"}),
            ],
        )
        self.assertEqual(llm_service.call_count, 1)

    def test_missing_ticker_does_not_call_llm(self):
        llm_service = MagicMock()
        agent = FinancialAnalysisAgent(
            financials_tool=self._financials_tool(),
            key_metrics_tool=self._key_metrics_tool(),
            llm_service=llm_service,
        )

        result = agent.run("Analyze company financials.")

        self.assertEqual(
            result.response,
            "Please provide a ticker symbol to analyze financials.",
        )
        self.assertEqual(result.tools_used, [])
        llm_service.assert_not_called()

    def test_llm_failure_is_observable(self):
        llm_service = MagicMock(side_effect=LLMError("Groq unavailable"))
        agent = FinancialAnalysisAgent(
            financials_tool=self._financials_tool(),
            key_metrics_tool=self._key_metrics_tool(),
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        with self.assertRaises(LLMError):
            agent.run("Analyze RELIANCE financials.")

    def test_empty_financial_data_is_passed_to_llm_context(self):
        llm_service = MagicMock(return_value="No financial data was available, so only the available context was analyzed.")
        agent = FinancialAnalysisAgent(
            financials_tool=lambda **kwargs: {"financials": []},
            key_metrics_tool=lambda **kwargs: {"metrics": []},
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        agent.run("Analyze RELIANCE financials.")

        messages = llm_service.call_args[0][0]
        self.assertIn("No financial statement data was returned.", messages[1]["content"])
        self.assertIn("No key metrics were returned.", messages[1]["content"])

    def test_multiple_financial_periods_are_provided_to_llm_context(self):
        llm_service = MagicMock(return_value="The trend is visible across periods.")
        financial_data = {
            "financials": [
                {"period": "2023", "metrics": [{"name": "revenue", "value": 100}]},
                {"period": "2024", "metrics": [{"name": "revenue", "value": 120}]},
            ]
        }
        metrics_data = {"metrics": [{"name": "operating_margin", "value": 0.15}]}

        agent = FinancialAnalysisAgent(
            financials_tool=lambda **kwargs: financial_data,
            key_metrics_tool=lambda **kwargs: metrics_data,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        agent.run("Compare RELIANCE revenue over time.")

        context_content = llm_service.call_args[0][0][1]["content"]
        self.assertIn("2023", context_content)
        self.assertIn("2024", context_content)
        self.assertIn("operating_margin", context_content)

    def test_context_builder_small_dataset_is_minimally_transformed(self):
        builder = FinancialAnalysisContextBuilder(max_chars=20000)
        context = builder.prepare(
            message="Analyze RELIANCE financials.",
            ticker="RELIANCE",
            financials={
                "financials": [
                    {
                        "statement_type": "INC",
                        "fiscal_year": "2024",
                        "end_date": "2024-03-31",
                        "metrics": [
                            {"name": "Revenue", "key": "revenue", "value": 1000},
                            {"name": "Net Income", "key": "net_income", "value": 150},
                        ],
                    }
                ]
            },
            key_metrics={
                "metrics": [
                    {"name": "Operating Margin", "key": "operating_margin", "value": 0.18}
                ]
            },
        )

        self.assertNotIn("context_reduction_applied", context)
        self.assertEqual(context["ticker"], "RELIANCE")
        self.assertEqual(context["financial_statement_data"][0]["statement_type"], "INC")
        self.assertEqual(context["financial_statement_data"][0]["metrics"][0]["key"], "revenue")
        self.assertEqual(context["key_metrics_data"][0]["key"], "operating_margin")

    def test_context_builder_large_dataset_is_deterministically_reduced(self):
        builder = FinancialAnalysisContextBuilder(max_chars=1200)
        large_financials = {
            "financials": [
                {
                    "statement_type": "INC",
                    "fiscal_year": str(year),
                    "end_date": f"{year}-03-31",
                    "metrics": [
                        {"name": "Revenue", "key": "revenue", "value": 1000 + year},
                        {"name": "Net Income", "key": "net_income", "value": 200 + year},
                        {"name": "Operating Margin", "key": "operating_margin", "value": 0.15},
                    ],
                }
                for year in range(2010, 2026)
            ]
        }
        context = builder.prepare(
            message="Analyze RELIANCE financials.",
            ticker="RELIANCE",
            financials=large_financials,
            key_metrics={
                "metrics": [
                    {"name": "Revenue", "key": "revenue", "value": 1200},
                    {"name": "Gross Margin", "key": "gross_margin", "value": 0.34},
                    {"name": "Debt To Equity", "key": "debt_to_equity", "value": 1.2},
                ]
            },
        )

        serialized = json.dumps(context, ensure_ascii=False, default=str)
        self.assertTrue(context["context_reduction_applied"])
        self.assertIn("omitted_information", context)
        self.assertLess(len(serialized), 1200)
        self.assertIn("2025", serialized)
        self.assertNotIn("2010", serialized)
        self.assertIn("revenue", serialized)
        self.assertIn("net_income", serialized)

    def test_context_builder_reduces_structurally_not_by_string_cut(self):
        builder = FinancialAnalysisContextBuilder(max_chars=700)
        context = builder.prepare(
            message="Analyze RELIANCE financials.",
            ticker="RELIANCE",
            financials={
                "financials": [
                    {
                        "statement_type": "INC",
                        "fiscal_year": "2024",
                        "metrics": [{"name": "Revenue", "key": "revenue", "value": 1000}],
                    },
                    {
                        "statement_type": "BAL",
                        "fiscal_year": "2023",
                        "metrics": [{"name": "Assets", "key": "total_assets", "value": 2000}],
                    },
                ]
            },
            key_metrics={
                "metrics": [{"name": "Operating Margin", "key": "operating_margin", "value": 0.18}]
            },
        )

        self.assertIsInstance(context["financial_statement_data"], list)
        self.assertIsInstance(context["financial_statement_data"][0], dict)
        self.assertIn("metrics", context["financial_statement_data"][0])
        self.assertNotIn("context_reduction_applied", context)

    def test_context_builder_keeps_recent_periods_and_key_metrics(self):
        builder = FinancialAnalysisContextBuilder(max_chars=2500)
        context = builder.prepare(
            message="Compare RELIANCE by period.",
            ticker="RELIANCE",
            financials={
                "financials": [
                    {"statement_type": "INC", "fiscal_year": "2022", "metrics": [{"name": "Revenue", "key": "revenue", "value": 800}]},
                    {"statement_type": "INC", "fiscal_year": "2023", "metrics": [{"name": "Revenue", "key": "revenue", "value": 900}]},
                    {"statement_type": "INC", "fiscal_year": "2024", "metrics": [{"name": "Revenue", "key": "revenue", "value": 1000}]},
                ]
            },
            key_metrics={
                "metrics": [
                    {"name": "Revenue", "key": "revenue", "value": 1000},
                    {"name": "Operating Margin", "key": "operating_margin", "value": 0.18},
                ]
            },
        )

        serialized = json.dumps(context, ensure_ascii=False, default=str)
        self.assertIn("2024", serialized)
        self.assertIn("2023", serialized)
        self.assertIn("operating_margin", serialized)
        self.assertIn("revenue", serialized)

    def test_context_budget_is_observed_before_llm_call(self):
        llm_service = MagicMock(return_value="Context bounded")
        agent = FinancialAnalysisAgent(
            financials_tool=lambda **kwargs: {"financials": [{"statement_type": "INC", "fiscal_year": "2024", "metrics": [{"name": "Revenue", "key": "revenue", "value": 1000}]}]},
            key_metrics_tool=lambda **kwargs: {"metrics": [{"name": "Revenue", "key": "revenue", "value": 1000}]},
            ticker="RELIANCE",
            llm_service=llm_service,
        )
        with self.settings(FINANCIAL_ANALYSIS_CONTEXT_CHAR_LIMIT=200):
            agent.max_context_chars = 200
            with self.assertRaises(ValueError):
                agent.run("Analyze RELIANCE financials.")
            llm_service.assert_not_called()

    @staticmethod
    def _financials_tool():
        return lambda **kwargs: {"financials": [{"period": "2024", "metrics": []}]}

    @staticmethod
    def _key_metrics_tool():
        return lambda **kwargs: {"metrics": [{"key": "pe_ratio"}]}

    def test_constrained_tier_reduces_periods_and_caps_output(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
        )
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=3750,
                completion_tokens=3750,
                total_tokens=7500,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CONSTRAINED)

        financials = {
            "financials": [
                {"statement_type": "INC", "fiscal_year": "2022", "metrics": [{"name": "Revenue", "key": "revenue", "value": 800}]},
                {"statement_type": "INC", "fiscal_year": "2024", "metrics": [{"name": "Revenue", "key": "revenue", "value": 1000}]},
            ]
        }
        key_metrics = {"metrics": [{"name": "PE Ratio", "key": "pe_ratio", "value": 25.0}]}

        llm_service = MagicMock(return_value="Constrained financial analysis.")
        llm_service.token_budget_manager = manager

        agent = FinancialAnalysisAgent(
            financials_tool=lambda **kwargs: financials,
            key_metrics_tool=lambda **kwargs: key_metrics,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Constrained financial analysis.")
        self.assertEqual(result.tools_used, ["get_financials", "get_key_metrics"])
        llm_service.assert_called_once()

        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 2000)

        messages = llm_service.call_args[0][0]
        context = json.loads(messages[1]["content"])
        self.assertTrue(context["context_reduction_applied"])
        self.assertIn("2024", json.dumps(context["financial_statement_data"]))
        self.assertNotIn("2022", json.dumps(context["financial_statement_data"]))

    def test_critical_tier_uses_minimal_context_and_1000_token_limit(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
        )
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=4750,
                completion_tokens=4750,
                total_tokens=9500,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CRITICAL)

        financials = {
            "financials": [
                {"statement_type": "INC", "fiscal_year": "2022", "metrics": [{"name": "Revenue", "key": "revenue", "value": 800}]},
                {"statement_type": "INC", "fiscal_year": "2024", "metrics": [{"name": "Revenue", "key": "revenue", "value": 1000}]},
            ]
        }
        key_metrics = {"metrics": [{"name": "PE Ratio", "key": "pe_ratio", "value": 25.0}]}

        llm_service = MagicMock(return_value="Critical financial analysis.")
        llm_service.token_budget_manager = manager

        agent = FinancialAnalysisAgent(
            financials_tool=lambda **kwargs: financials,
            key_metrics_tool=lambda **kwargs: key_metrics,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Critical financial analysis.")
        self.assertEqual(result.tools_used, ["get_financials", "get_key_metrics"])
        llm_service.assert_called_once()

        _, kwargs = llm_service.call_args
        self.assertEqual(kwargs.get("max_completion_tokens"), 1000)

        messages = llm_service.call_args[0][0]
        context = json.loads(messages[1]["content"])
        self.assertTrue(context["context_reduction_applied"])

    def test_exhausted_tier_bypasses_llm_and_returns_valid_agent_result(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
        )
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=5000,
                completion_tokens=5000,
                total_tokens=10000,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.EXHAUSTED)

        financials = {"financials": [{"statement_type": "INC", "fiscal_year": "2024", "metrics": [{"name": "Revenue", "key": "revenue", "value": 1000}]}]}
        key_metrics = {"metrics": [{"name": "PE Ratio", "key": "pe_ratio", "value": 25.0}]}

        llm_service = MagicMock(return_value="Should not be called.")
        llm_service.token_budget_manager = manager

        agent = FinancialAnalysisAgent(
            financials_tool=lambda **kwargs: financials,
            key_metrics_tool=lambda **kwargs: key_metrics,
            ticker="RELIANCE",
            llm_service=llm_service,
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(
            result.response,
            "Financial analysis for RELIANCE could not be completed: the LLM budget is exhausted.",
        )
        self.assertEqual(result.tools_used, ["get_financials", "get_key_metrics"])
        self.assertEqual(result.data["ticker"], "RELIANCE")
        self.assertIn("financial_statement_data", result.data)
        self.assertIn("key_metrics_data", result.data)
        llm_service.assert_not_called()

    def test_financial_agent_consumes_canonical_research_context(self):
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
            metrics=[KeyMetric(category="valuation", name="P/E", key="pe_ratio", value=30.0)],
        )
        prov = {
            "financials": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }

        ctx = ResearchContext(
            ticker="LT",
            market="IN",
            company_profile=profile,
            financials=[statement],
            key_metrics=key_metrics,
            provenance=prov,
        )

        llm_service = MagicMock(return_value="L&T financials are robust.")
        agent = FinancialAnalysisAgent(llm_service=llm_service)

        result = agent.run(ctx)

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "L&T financials are robust.")
        self.assertEqual(result.data["ticker"], "LT")
        self.assertIn("provenance", result.data)
        self.assertEqual(result.data["provenance"]["financials"]["source"], "upstox")
        self.assertEqual(result.data["company_profile"]["name"], "Larsen & Toubro Ltd")

    def test_provenance_survives_from_tool_dict_into_agent_context(self):
        financials_dict = {
            "ticker": "LT",
            "market": "IN",
            "primary_provider": "upstox",
            "source": "indian_api",
            "fallback_used": True,
            "data_status": "complete",
            "fallback_reason": "upstox_exception",
            "provenance": {
                "primary_provider": "upstox",
                "source": "indian_api",
                "fallback_used": True,
                "data_status": "complete",
                "fallback_reason": "upstox_exception",
            },
            "financials": [
                {
                    "statement_type": "INC",
                    "fiscal_year": "2026",
                    "end_date": "2026-03-31",
                    "period_type": "annual",
                    "period_length": 12,
                    "metrics": [{"name": "Revenue", "key": "revenue", "value": 150000.0}],
                }
            ],
        }

        key_metrics_dict = {
            "ticker": "LT",
            "market": "IN",
            "primary_provider": "upstox",
            "source": "upstox",
            "fallback_used": False,
            "data_status": "complete",
            "metrics": [{"category": "valuation", "name": "P/E", "key": "pe_ratio", "value": 28.0}],
        }

        llm_service = MagicMock(return_value="Fallback analysis complete.")
        agent = FinancialAnalysisAgent(
            financials_tool=lambda **kwargs: financials_dict,
            key_metrics_tool=lambda **kwargs: key_metrics_dict,
            ticker="LT",
            llm_service=llm_service,
        )

        result = agent.run("Analyze LT financials.")

        self.assertIn("provenance", result.data)
        self.assertTrue(result.data["provenance"]["financials"]["fallback_used"])
        self.assertEqual(result.data["provenance"]["financials"]["source"], "indian_api")
        self.assertEqual(result.data["provenance"]["financials"]["fallback_reason"], "upstox_exception")
        self.assertEqual(result.data["provenance"]["key_metrics"]["source"], "upstox")

    def test_missing_optional_sections_do_not_break_agent(self):
        ctx = ResearchContext(
            ticker="INFY",
            market="IN",
            company_profile=None,
            financials=None,
            key_metrics=None,
        )

        builder = FinancialAnalysisContextBuilder()
        prepared = builder.prepare(
            message="Analyze INFY financials.",
            ticker="INFY",
            research_context=ctx,
        )

        self.assertEqual(prepared["ticker"], "INFY")
        self.assertEqual(prepared["financial_statement_data"], "No financial statement data was returned.")
        self.assertEqual(prepared["key_metrics_data"], "No key metrics were returned.")
        self.assertNotIn("company_profile", prepared)

    def test_context_payload_is_smaller_than_raw_dict(self):
        builder = FinancialAnalysisContextBuilder()

        raw_financials = {
            "ticker": "LT",
            "market": "IN",
            "extra_unused_provider_metadata": "x" * 500,
            "raw_debug_payload": {"raw_unparsed_buffer": "y" * 1000},
            "financials": [
                {
                    "statement_type": "INC",
                    "fiscal_year": "2026",
                    "end_date": "2026-03-31",
                    "period_type": "annual",
                    "period_length": 12,
                    "unnecessary_internal_flag": True,
                    "metrics": [
                        {"name": "Revenue", "key": "revenue", "value": 150000.0, "unused_raw_field": "abc"},
                    ],
                }
            ],
        }

        raw_json_len = len(json.dumps(raw_financials))

        prepared = builder.prepare(
            message="Analyze LT financials",
            ticker="LT",
            financials=raw_financials,
        )

        canonical_json_len = len(json.dumps(prepared))
        self.assertLess(canonical_json_len, raw_json_len)

