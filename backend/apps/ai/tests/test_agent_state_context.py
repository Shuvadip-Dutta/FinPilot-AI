"""Focused unit tests for AgentState and ResearchContext integration (Phase 12D Step 2E)."""

import json
from unittest.mock import MagicMock
from django.test import SimpleTestCase

from apps.ai.agents.base import AgentResult
from apps.ai.agents.synthesis import FinalSynthesisAgent
from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.ai.graph.langgraph_workflow import (
    _extract_research_context_from_result,
    _merge_graph_state,
    _merge_research_context,
)
from apps.ai.graph.state import AgentState
from apps.research.services.schemas import (
    CompanyProfile,
    FinancialStatement,
    HistoricalCandle,
    HistoricalMarketData,
    NewsArticle,
    NewsResearch,
)


class AgentStateResearchContextTestCase(SimpleTestCase):
    """Test suite covering AgentState and ResearchContext propagation requirements."""

    def test_agent_state_backward_compatibility_without_research_context(self):
        """Verify AgentState can be created without research_context."""
        state = AgentState(user_message="Analyze LT", ticker="LT", market="IN")
        self.assertIsNone(state.research_context)
        self.assertEqual(state.user_message, "Analyze LT")
        self.assertEqual(state.ticker, "LT")
        self.assertEqual(state.results, {})
        self.assertEqual(state.errors, [])

    def test_agent_state_carrying_complete_research_context(self):
        """Verify AgentState can carry a full canonical ResearchContext."""
        profile = CompanyProfile(
            ticker="LT",
            name="Larsen & Toubro Limited",
            exchange="NSE",
            country="IN",
            sector="Industrials",
        )
        prov = {
            "financial": ProviderProvenance(
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
            provenance=prov,
        )
        state = AgentState(
            user_message="Analyze LT",
            ticker="LT",
            market="IN",
            research_context=ctx,
        )
        self.assertIsNotNone(state.research_context)
        self.assertEqual(state.research_context.ticker, "LT")
        self.assertEqual(state.research_context.company_profile.name, "Larsen & Toubro Limited")
        self.assertIn("financial", state.research_context.provenance)
        self.assertEqual(state.research_context.provenance["financial"].primary_provider, "upstox")

    def test_specialist_node_output_populates_research_context(self):
        """Verify specialist node output populates/updates research context."""
        profile = CompanyProfile(
            ticker="RELIANCE",
            name="Reliance Industries",
            exchange="NSE",
            country="IN",
        )
        data_payload = {
            "ticker": "RELIANCE",
            "company_profile": profile,
            "provenance": {
                "financial": {
                    "primary_provider": "upstox",
                    "source": "upstox",
                    "fallback_used": False,
                    "data_status": "complete",
                }
            },
        }
        result = AgentResult(
            response="Financial summary for Reliance.",
            tools_used=["get_company_profile"],
            data=data_payload,
        )
        extracted = _extract_research_context_from_result("RELIANCE", "IN", result)
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.company_profile.name, "Reliance Industries")
        self.assertIn("financial", extracted.provenance)
        self.assertEqual(extracted.provenance["financial"].source, "upstox")

    def test_provenance_survives_state_propagation(self):
        """Verify section-level provenance survives graph state merging."""
        prov1 = {
            "financial": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }
        prov2 = {
            "market": ProviderProvenance(
                primary_provider="upstox",
                source="indian_api",
                fallback_used=True,
                data_status="complete",
                fallback_reason="Upstox quote rate limited",
            )
        }
        ctx1 = ResearchContext(ticker="TCS", market="IN", provenance=prov1)
        ctx2 = ResearchContext(ticker="TCS", market="IN", provenance=prov2)

        merged_ctx = _merge_research_context(ctx1, ctx2)
        self.assertIsNotNone(merged_ctx)
        self.assertIn("financial", merged_ctx.provenance)
        self.assertIn("market", merged_ctx.provenance)
        self.assertFalse(merged_ctx.provenance["financial"].fallback_used)
        self.assertTrue(merged_ctx.provenance["market"].fallback_used)
        self.assertEqual(merged_ctx.provenance["market"].fallback_reason, "Upstox quote rate limited")

    def test_multiple_specialists_contribute_without_overwriting(self):
        """Verify multiple specialists update different sections without overwriting unrelated sections."""
        profile = CompanyProfile(ticker="INFY", name="Infosys", exchange="NSE", country="IN")
        market_data = HistoricalMarketData(
            ticker="INFY",
            candles=[HistoricalCandle(timestamp="2026-09-01", open=1500.0, high=1550.0, low=1490.0, close=1530.0, volume=1000, open_interest=None)]
        )
        ctx1 = ResearchContext(ticker="INFY", market="IN", company_profile=profile)
        ctx2 = ResearchContext(ticker="INFY", market="IN", market_data=market_data)

        state1 = {"research_context": ctx1, "results": {"financial": "fin_result"}}
        state2 = {"research_context": ctx2, "results": {"market": "mkt_result"}}

        merged_graph = _merge_graph_state(state1, state2)

        merged_rc: ResearchContext = merged_graph["research_context"]
        self.assertIsNotNone(merged_rc.company_profile)
        self.assertEqual(merged_rc.company_profile.name, "Infosys")
        self.assertIsNotNone(merged_rc.market_data)
        self.assertEqual(len(merged_rc.market_data.candles), 1)
        self.assertEqual(merged_graph["results"]["financial"], "fin_result")
        self.assertEqual(merged_graph["results"]["market"], "mkt_result")

    def test_portfolio_optimization_remains_in_results(self):
        """Verify portfolio optimization remains in native state.results container."""
        opt_data = {
            "portfolio": {"allocations": {"TCS": 0.6, "INFY": 0.4}},
            "metrics": {"expected_return": 0.12, "sharpe_ratio": 1.4},
        }
        state = AgentState(
            user_message="Optimize portfolio",
            results={"portfolio_optimization": opt_data},
        )
        self.assertIn("portfolio_optimization", state.results)
        self.assertEqual(state.results["portfolio_optimization"], opt_data)
        self.assertIsNone(state.research_context)

    def test_synthesis_consumes_research_context(self):
        """Verify FinalSynthesisAgent consumes state.research_context directly."""
        profile = CompanyProfile(ticker="WIPRO", name="Wipro Limited", exchange="NSE", country="IN")
        prov = {
            "financial": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }
        rc = ResearchContext(ticker="WIPRO", market="IN", company_profile=profile, provenance=prov)
        state = AgentState(
            user_message="Overview for WIPRO",
            ticker="WIPRO",
            market="IN",
            research_context=rc,
            results={"financial": AgentResult(response="Wipro financials are stable.", tools_used=["get_financials"], data={"provenance": prov})},
        )

        built_ctx = FinalSynthesisAgent.build_canonical_context(state)
        self.assertEqual(built_ctx.ticker, "WIPRO")
        self.assertEqual(built_ctx.company_profile.name, "Wipro Limited")
        self.assertIn("financial", built_ctx.provenance)

    def test_existing_results_only_workflows_still_work(self):
        """Verify legacy workflows passing only state.results function without error."""
        state = AgentState(
            user_message="Overview for HDFC",
            ticker="HDFCBANK",
            market="IN",
            results={
                "financial": AgentResult(response="HDFC bank revenue grew 15%.", tools_used=["get_financials"]),
                "market": AgentResult(response="HDFC stock price is 1600.", tools_used=["get_market_quote"]),
            },
        )
        self.assertIsNone(state.research_context)

        llm_service = MagicMock(return_value="Combined HDFC synthesis report.")
        agent = FinalSynthesisAgent(llm_service=llm_service)
        result = agent.run(state)

        self.assertIsInstance(result, AgentResult)
        self.assertIn("Combined HDFC synthesis report.", result.response)

    def test_pydantic_serialization_of_agent_state(self):
        """Verify Pydantic serialization (model_dump and model_dump_json) works with ResearchContext."""
        profile = CompanyProfile(ticker="TATAMOTORS", name="Tata Motors", exchange="NSE", country="IN")
        prov = {
            "financial": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }
        rc = ResearchContext(ticker="TATAMOTORS", market="IN", company_profile=profile, provenance=prov)
        state = AgentState(
            user_message="Analyze Tata Motors",
            ticker="TATAMOTORS",
            market="IN",
            research_context=rc,
            results={"financial": {"status": "ok"}},
            errors=[],
        )

        dumped = state.model_dump(mode="json")
        self.assertEqual(dumped["ticker"], "TATAMOTORS")
        self.assertIn("research_context", dumped)
        self.assertEqual(dumped["research_context"]["company_profile"]["name"], "Tata Motors")

        json_str = state.model_dump_json()
        deserialized = json.loads(json_str)
        self.assertEqual(deserialized["research_context"]["ticker"], "TATAMOTORS")
        self.assertEqual(deserialized["research_context"]["provenance"]["financial"]["primary_provider"], "upstox")
