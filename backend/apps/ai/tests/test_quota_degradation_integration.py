"""End-to-end quota/degradation integration tests for FinPilot AI agents."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.agents.financial import FinancialAnalysisAgent
from apps.ai.agents.market import MarketAnalysisAgent
from apps.ai.agents.news import NewsIntelligenceAgent
from apps.ai.agents.portfolio_optimization import PortfolioOptimizationAgent
from apps.ai.agents.risk import RiskAnalysisAgent
from apps.ai.agents.synthesis import FinalSynthesisAgent
from apps.ai.graph.state import AgentState
from apps.ai.portfolio.optimization import (
    OptimizationInput,
    OptimizationResult,
)
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    LLMUsage,
    TokenBudgetManager,
)


def sample_optimization_result():
    return OptimizationResult(
        optimized_weights={"RELIANCE": 1.0},
        expected_return=0.12,
        volatility=0.18,
        sharpe_ratio=0.556,
        total_weight=1.0,
        success=True,
        message="Optimization completed successfully.",
    )


def sample_market_data():
    return {
        "ticker": "RELIANCE",
        "market": "IN",
        "quotes": [
            {
                "exchange": "NSE",
                "price": 1309.0,
                "percent_change": 1.74,
                "year_high": 1611.2,
                "year_low": 1250.55,
            }
        ],
    }


def sample_news_data():
    return {
        "ticker": "RELIANCE",
        "market": "IN",
        "aggregated_sentiment": {
            "positive": 5,
            "neutral": 2,
            "negative": 1,
            "unavailable": 0,
        },
        "articles": [
            {
                "title": "Reliance Expands Energy Footprint",
                "source": "Financial Express",
                "relevance_type": "company",
                "sentiment": {"label": "positive", "confidence": 0.95},
            }
        ],
    }


def sample_financial_data():
    return {
        "ticker": "RELIANCE",
        "market": "IN",
        "key_metrics": [
            {"metric_name": "pe_ratio", "value": 24.5},
            {"metric_name": "pb_ratio", "value": 2.1},
        ],
        "financials": [
            {
                "statement_type": "income",
                "fiscal_year": "2026",
                "metrics": [{"key": "revenue", "value": 900000}],
            }
        ],
    }


class QuotaDegradationIntegrationTestCase(SimpleTestCase):
    """Integration test suite verifying shared TokenBudgetManager degradation across all FinPilot agents."""

    def setUp(self):
        self.shared_manager = TokenBudgetManager(tpd_limit=10000)

    def _create_mock_llm_service(self, model_tier: str, return_value: str = "Mock response"):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = return_value
        mock_llm.token_budget_manager = self.shared_manager
        mock_llm.generate.token_budget_manager = self.shared_manager

        service = LLMService(model=model_tier, token_budget_manager=self.shared_manager)
        service.generate = mock_llm.generate
        return service

    def test_scenario_1_normal_tier_execution(self):
        """Verify NORMAL tier: shared manager reports NORMAL, agents execute normally, no degradation triggered."""
        self.assertEqual(self.shared_manager.get_degradation_tier(), DegradationTier.NORMAL)

        mkt_llm = self._create_mock_llm_service("market", "Market overview response.")
        news_llm = self._create_mock_llm_service("news", "News overview response.")
        port_llm = self._create_mock_llm_service("portfolio", "Portfolio optimization explanation.")
        fin_llm = self._create_mock_llm_service("financial", "Financial analysis response.")
        risk_llm = self._create_mock_llm_service("risk", "Risk assessment response.")
        synth_llm = self._create_mock_llm_service("synthesis", "Final synthesis response.")

        mkt_agent = MarketAnalysisAgent(
            market_data_tool=lambda ticker, market="IN": sample_market_data(),
            historical_data_tool=lambda ticker, market="IN", period="1y": {"candles": []},
            ticker="RELIANCE",
            llm_service=mkt_llm.generate,
        )
        news_agent = NewsIntelligenceAgent(
            news_tool=lambda *args, **kwargs: sample_news_data(),
            ticker="RELIANCE",
            llm_service=news_llm.generate,
        )
        port_agent = PortfolioOptimizationAgent(
            optimizer=lambda input_data: sample_optimization_result(),
            llm_service=port_llm.generate,
        )
        fin_agent = FinancialAnalysisAgent(
            financials_tool=lambda ticker, market="IN": sample_financial_data(),
            key_metrics_tool=lambda ticker, market="IN": {"metrics": []},
            ticker="RELIANCE",
            llm_service=fin_llm.generate,
        )
        risk_agent = RiskAnalysisAgent(llm_service=risk_llm.generate)
        synth_agent = FinalSynthesisAgent(llm_service=synth_llm.generate)

        mkt_res = mkt_agent.run("Market status")
        news_res = news_agent.run("News status")
        port_res = port_agent.run(OptimizationInput(tickers=["RELIANCE", "TCS"], historical_prices={"RELIANCE": [100, 101, 102], "TCS": [200, 201, 202]}, risk_free_rate=0.02, min_weight=0.1, max_weight=0.9))
        fin_res = fin_agent.run("Financial status")
        
        state = AgentState(
            user_message="Assess risk and synthesize",
            ticker="RELIANCE",
            results={"financial": fin_res, "market": mkt_res, "news": news_res, "portfolio_optimization": port_res},
        )
        risk_res = risk_agent.run(state)
        state.results["risk"] = risk_res
        synth_res = synth_agent.run(state)

        self.assertEqual(mkt_res.response, "Market overview response.")
        self.assertIn("News overview response.", news_res.response)
        self.assertEqual(port_res.response, "Portfolio optimization explanation.")
        self.assertEqual(fin_res.response, "Financial analysis response.")
        self.assertEqual(risk_res.response, "Risk assessment response.")
        self.assertEqual(synth_res.response, "Final synthesis response.")

    def test_scenario_2_constrained_tier_execution(self):
        """Verify CONSTRAINED tier: output budgets reduced, essential evidence preserved, no model switching."""
        self.shared_manager.record_actual_usage(
            LLMUsage(prompt_tokens=7500, completion_tokens=0, total_tokens=7500, model="test")
        )
        self.assertEqual(self.shared_manager.get_degradation_tier(), DegradationTier.CONSTRAINED)

        mkt_llm = self._create_mock_llm_service("market", "Constrained market response.")
        news_llm = self._create_mock_llm_service("news", "Constrained news response.")
        port_llm = self._create_mock_llm_service("portfolio", "Constrained portfolio response.")
        fin_llm = self._create_mock_llm_service("financial", "Constrained financial response.")
        risk_llm = self._create_mock_llm_service("risk", "Constrained risk response.")
        synth_llm = self._create_mock_llm_service("synthesis", "Constrained synthesis response.")

        initial_mkt_model = mkt_llm.model
        initial_news_model = news_llm.model
        initial_fin_model = fin_llm.model

        mkt_agent = MarketAnalysisAgent(
            market_data_tool=lambda ticker, market="IN": sample_market_data(),
            historical_data_tool=lambda ticker, market="IN", period="1y": {"candles": [{"close": 1309.0}] * 20},
            ticker="RELIANCE",
            llm_service=mkt_llm.generate,
        )
        news_agent = NewsIntelligenceAgent(
            news_tool=lambda *args, **kwargs: sample_news_data(),
            ticker="RELIANCE",
            llm_service=news_llm.generate,
        )
        port_agent = PortfolioOptimizationAgent(
            optimizer=lambda input_data: sample_optimization_result(),
            llm_service=port_llm.generate,
        )

        mkt_res = mkt_agent.run("Current market")
        news_res = news_agent.run("News summary")
        port_res = port_agent.run(OptimizationInput(tickers=["RELIANCE", "TCS"], historical_prices={"RELIANCE": [100, 101, 102], "TCS": [200, 201, 202]}, risk_free_rate=0.02, min_weight=0.1, max_weight=0.9))

        self.assertEqual(mkt_llm.model, initial_mkt_model)
        self.assertEqual(news_llm.model, initial_news_model)
        self.assertEqual(fin_llm.model, initial_fin_model)

        mkt_llm.generate.assert_called_once()
        _, mkt_kwargs = mkt_llm.generate.call_args
        self.assertEqual(mkt_kwargs.get("max_completion_tokens"), 512)

        news_llm.generate.assert_called_once()
        _, news_kwargs = news_llm.generate.call_args
        self.assertEqual(news_kwargs.get("max_completion_tokens"), 512)

        port_llm.generate.assert_called_once()
        _, port_kwargs = port_llm.generate.call_args
        self.assertEqual(port_kwargs.get("max_completion_tokens"), 512)

        fin_agent = FinancialAnalysisAgent(
            financials_tool=lambda ticker, market="IN": sample_financial_data(),
            key_metrics_tool=lambda ticker, market="IN": {"metrics": []},
            ticker="RELIANCE",
            llm_service=fin_llm.generate,
        )
        fin_res = fin_agent.run("Financial summary")
        self.assertIn("financial_statement_data", fin_res.data)

        state = AgentState(
            user_message="Synthesize constrained",
            ticker="RELIANCE",
            results={"financial": fin_res, "market": mkt_res, "news": news_res, "portfolio_optimization": port_res},
        )
        synth_agent = FinalSynthesisAgent(llm_service=synth_llm.generate)
        synth_res = synth_agent.run(state)

        synth_llm.generate.assert_called_once()
        _, synth_kwargs = synth_llm.generate.call_args
        self.assertEqual(synth_kwargs.get("max_completion_tokens"), 2000)
        self.assertEqual(synth_res.response, "Constrained synthesis response.")

    def test_scenario_3_critical_tier_execution(self):
        """Verify CRITICAL tier: minimal context / output budgets activated, structured deterministic evidence intact."""
        self.shared_manager.record_actual_usage(
            LLMUsage(prompt_tokens=9500, completion_tokens=0, total_tokens=9500, model="test")
        )
        self.assertEqual(self.shared_manager.get_degradation_tier(), DegradationTier.CRITICAL)

        synth_llm = self._create_mock_llm_service("synthesis", "Critical synthesis response.")
        synth_agent = FinalSynthesisAgent(llm_service=synth_llm.generate)

        state = AgentState(
            user_message="Synthesize critical",
            ticker="RELIANCE",
            results={
                "financial": AgentResult(
                    response="Detailed financial explanation " * 30,
                    tools_used=["get_financials"],
                    data=sample_financial_data(),
                ),
                "market": AgentResult(
                    response="Detailed market explanation " * 30,
                    tools_used=["get_market_data"],
                    data=sample_market_data(),
                ),
                "news": AgentResult(
                    response="Detailed news explanation " * 30,
                    tools_used=["get_news"],
                    data=sample_news_data(),
                ),
            },
        )

        synth_res = synth_agent.run(state)
        synth_llm.generate.assert_called_once()
        _, synth_kwargs = synth_llm.generate.call_args
        self.assertEqual(synth_kwargs.get("max_completion_tokens"), 1000)
        self.assertEqual(synth_res.response, "Critical synthesis response.")
        self.assertIn("financial", synth_res.data)
        self.assertIn("market", synth_res.data)
        self.assertIn("news", synth_res.data)

    def test_scenario_4_exhausted_tier_execution(self):
        """Verify EXHAUSTED tier: 0 LLM calls made, deterministic/explicit fallback AgentResults returned."""
        self.shared_manager.record_actual_usage(
            LLMUsage(prompt_tokens=10000, completion_tokens=0, total_tokens=10000, model="test")
        )
        self.assertEqual(self.shared_manager.get_degradation_tier(), DegradationTier.EXHAUSTED)

        mkt_llm = self._create_mock_llm_service("market")
        news_llm = self._create_mock_llm_service("news")
        port_llm = self._create_mock_llm_service("portfolio")
        fin_llm = self._create_mock_llm_service("financial")
        risk_llm = self._create_mock_llm_service("risk")
        synth_llm = self._create_mock_llm_service("synthesis")

        mkt_agent = MarketAnalysisAgent(
            market_data_tool=lambda ticker, market="IN": sample_market_data(),
            ticker="RELIANCE",
            llm_service=mkt_llm.generate,
        )
        news_agent = NewsIntelligenceAgent(
            news_tool=lambda *args, **kwargs: sample_news_data(),
            ticker="RELIANCE",
            llm_service=news_llm.generate,
        )
        port_agent = PortfolioOptimizationAgent(
            optimizer=lambda input_data: sample_optimization_result(),
            llm_service=port_llm.generate,
        )
        fin_agent = FinancialAnalysisAgent(
            financials_tool=lambda ticker, market="IN": sample_financial_data(),
            key_metrics_tool=lambda ticker, market="IN": {"metrics": []},
            ticker="RELIANCE",
            llm_service=fin_llm.generate,
        )
        risk_agent = RiskAnalysisAgent(llm_service=risk_llm.generate)
        synth_agent = FinalSynthesisAgent(llm_service=synth_llm.generate)

        mkt_res = mkt_agent.run("Market status")
        news_res = news_agent.run("News status")
        port_res = port_agent.run(OptimizationInput(tickers=["RELIANCE", "TCS"], historical_prices={"RELIANCE": [100, 101, 102], "TCS": [200, 201, 202]}, risk_free_rate=0.02, min_weight=0.1, max_weight=0.9))
        fin_res = fin_agent.run("Financial status")

        state = AgentState(
            user_message="Synthesize exhausted",
            ticker="RELIANCE",
            results={"financial": fin_res, "market": mkt_res, "news": news_res, "portfolio_optimization": port_res},
        )
        risk_res = risk_agent.run(state)
        state.results["risk"] = risk_res
        synth_res = synth_agent.run(state)

        mkt_llm.generate.assert_not_called()
        news_llm.generate.assert_not_called()
        port_llm.generate.assert_not_called()
        fin_llm.generate.assert_not_called()
        risk_llm.generate.assert_not_called()
        synth_llm.generate.assert_not_called()

        self.assertIn("1309.0", mkt_res.response)
        self.assertIn("Authoritative sentiment", news_res.response)
        self.assertIn("Portfolio optimization completed", port_res.response)
        self.assertIn("could not be completed", fin_res.response)
        self.assertIn("could not be completed", risk_res.response)
        self.assertIn("could not be completed", synth_res.response)

        for res in (mkt_res, news_res, port_res, fin_res, risk_res, synth_res):
            self.assertNotIn("Strong Buy", res.response)
            self.assertNotIn("Guaranteed return", res.response)

        self.assertIn("market_data", mkt_res.data)
        self.assertIn("aggregated_sentiment", news_res.data)
        self.assertIn("optimized_weights", port_res.data)
        self.assertIn("financial", synth_res.data)

    def test_scenario_5_shared_manager_cross_service_accounting(self):
        """Verify shared-manager behavior: token usage recorded on one service is visible across all agent services."""
        services = [
            LLMService(model=model, token_budget_manager=self.shared_manager)
            for model in ("financial", "market", "news", "risk", "portfolio", "synthesis")
        ]

        for service in services:
            self.assertEqual(service.token_budget_manager.get_degradation_tier(), DegradationTier.NORMAL)

        services[0].token_budget_manager.record_actual_usage(
            LLMUsage(prompt_tokens=7500, completion_tokens=0, total_tokens=7500, model="test")
        )

        for service in services:
            self.assertEqual(service.token_budget_manager.get_degradation_tier(), DegradationTier.CONSTRAINED)

        services[3].token_budget_manager.record_actual_usage(
            LLMUsage(prompt_tokens=2500, completion_tokens=0, total_tokens=2500, model="test")
        )

        for service in services:
            self.assertEqual(service.token_budget_manager.get_degradation_tier(), DegradationTier.EXHAUSTED)

    def test_scenario_6_regression_and_agent_result_contracts(self):
        """Verify regression safety: AgentResult contracts remain valid across all degradation tiers."""
        tiers_to_test = [
            (0, DegradationTier.NORMAL),
            (7500, DegradationTier.CONSTRAINED),
            (9500, DegradationTier.CRITICAL),
            (10000, DegradationTier.EXHAUSTED),
        ]

        for usage_tokens, expected_tier in tiers_to_test:
            manager = TokenBudgetManager(tpd_limit=10000)
            if usage_tokens > 0:
                manager.record_actual_usage(
                    LLMUsage(prompt_tokens=usage_tokens, completion_tokens=0, total_tokens=usage_tokens, model="test")
                )
            self.assertEqual(manager.get_degradation_tier(), expected_tier)

            mock_llm = MagicMock()
            mock_llm.generate.return_value = f"Response for {expected_tier.value}"
            mock_llm.token_budget_manager = manager
            mock_llm.generate.token_budget_manager = manager

            mkt_agent = MarketAnalysisAgent(
                market_data_tool=lambda ticker, market="IN": sample_market_data(),
                ticker="RELIANCE",
                llm_service=mock_llm.generate,
            )
            fin_agent = FinancialAnalysisAgent(
                financials_tool=lambda ticker, market="IN": sample_financial_data(),
                key_metrics_tool=lambda ticker, market="IN": {"metrics": []},
                ticker="RELIANCE",
                llm_service=mock_llm.generate,
            )

            mkt_res = mkt_agent.run("Check market")
            fin_res = fin_agent.run("Check financials")

            for res in (mkt_res, fin_res):
                self.assertIsInstance(res, AgentResult)
                self.assertIsInstance(res.response, str)
                self.assertTrue(len(res.response.strip()) > 0)
                self.assertIsInstance(res.tools_used, list)
                self.assertTrue(res.data is None or isinstance(res.data, dict))

