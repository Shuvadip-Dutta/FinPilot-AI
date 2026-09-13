from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import SimpleTestCase, TestCase

from apps.ai.graph.router import WorkflowRouter
from apps.ai.graph.state import AgentState
from apps.ai.portfolio.backtest_extractor import (
    BacktestExtractionError,
    BacktestParameterExtractor,
    ExtractedBacktestConfig,
    extract_backtest_config,
)
from apps.ai.services.agent_service import AgentService
from apps.ai.services.schemas import AgentResult
from apps.portfolio.models import Holding, Portfolio
from apps.research.models import ResearchEvidence, ResearchSession

User = get_user_model()


class ConversationalBacktestRoutingTestCase(SimpleTestCase):
    """Test suite verifying backtest intent routing and non-backtest separation."""

    def setUp(self):
        self.router = WorkflowRouter()

    def test_backtest_my_portfolio_routes_to_portfolio_and_detects_intent(self):
        """Case 1: 'Backtest my portfolio' -> portfolio route and backtest intent."""
        message = "Backtest my portfolio"
        self.assertEqual(self.router.route(message), "portfolio")
        self.assertTrue(self.router.is_backtest_intent(message))

        intent_meta = self.router.classify_intent(message)
        self.assertEqual(intent_meta["route"], "portfolio")
        self.assertTrue(intent_meta["is_backtest"])

    def test_walk_forward_simulation_routes_to_portfolio_and_detects_intent(self):
        """Case 2: 'Run a walk-forward simulation' -> portfolio route and backtest intent."""
        message = "Run a walk-forward simulation"
        self.assertEqual(self.router.route(message), "portfolio")
        self.assertTrue(self.router.is_backtest_intent(message))

    def test_additional_backtest_phrases_detect_intent(self):
        """Verify backtesting and historical simulation phrases."""
        phrases = [
            "Backtesting over the last 2 years",
            "Do a walk-forward simulation",
            "Historically simulate my portfolio",
            "Run a historical simulation on my holdings",
        ]
        for phrase in phrases:
            self.assertEqual(self.router.route(phrase), "portfolio")
            self.assertTrue(self.router.is_backtest_intent(phrase))

    def test_unrelated_test_queries_are_not_backtest_intent(self):
        """Case 3: Unrelated occurrences of 'test' must not trigger backtest intent."""
        unrelated = [
            ("test my API", "general"),
            ("test the portfolio page", "portfolio"),
            ("what does this test mean?", "general"),
            ("unit test results", "general"),
        ]
        for query, expected_route in unrelated:
            self.assertEqual(self.router.route(query), expected_route)
            self.assertFalse(
                self.router.is_backtest_intent(query),
                f"Query '{query}' incorrectly classified as backtest intent.",
            )

    def test_backward_compatibility_existing_routes_unchanged(self):
        """Cases 20 & 21: Existing router classifications remain 100% backward compatible."""
        samples = [
            ("Show Reliance's quarterly revenue and profit.", "financial"),
            ("What is the current share price of TCS?", "market"),
            ("Show me the latest news about Infosys.", "news"),
            ("Assess the downside risk of this investment.", "risk"),
            ("Analyze my portfolio allocation.", "portfolio"),
            ("How can I create a monthly budget?", "general"),
            ("Conduct a complete fundamental and market research analysis of L&T.", "general"),
        ]
        for query, expected_route in samples:
            self.assertEqual(self.router.route(query), expected_route)
            self.assertFalse(self.router.is_backtest_intent(query))


class BacktestParameterExtractionTestCase(SimpleTestCase):
    """Test suite verifying deterministic parameter extraction and boundary validation."""

    def setUp(self):
        self.fixed_ref_date = date(2026, 9, 13)

    # -------------------------------------------------------------------------
    # Benchmark Extraction
    # -------------------------------------------------------------------------

    def test_extract_against_nifty_50(self):
        """Case 4: 'against NIFTY 50' -> canonical benchmark 'NIFTY 50'."""
        cfg = extract_backtest_config(
            "Backtest my portfolio against NIFTY 50 for the last 2 years.",
            reference_date=self.fixed_ref_date,
        )
        self.assertEqual(cfg.benchmark_ticker, "NIFTY 50")

    def test_extract_against_sensex(self):
        """Case 5: 'against SENSEX' -> canonical benchmark 'SENSEX'."""
        cfg = extract_backtest_config(
            "Run backtest versus SENSEX",
            reference_date=self.fixed_ref_date,
        )
        self.assertEqual(cfg.benchmark_ticker, "SENSEX")

    def test_extract_benchmark_aliases_normalized(self):
        """Verify benchmark aliases (NIFTY50, BANKNIFTY, NIFTY 500)."""
        cases = [
            ("compare with NIFTY50", "NIFTY 50"),
            ("benchmark is BANKNIFTY", "BANKNIFTY"),
            ("versus NIFTY 500", "NIFTY 500"),
            ("against NIFTY BANK", "BANKNIFTY"),
        ]
        for text, expected in cases:
            cfg = extract_backtest_config(text, reference_date=self.fixed_ref_date)
            self.assertEqual(cfg.benchmark_ticker, expected)

    def test_negative_benchmark_phrasing_does_not_produce_benchmark(self):
        """Negative comparison phrasing and non-comparison mentions must not produce a benchmark."""
        negative_cases = [
            "Backtest my portfolio, but don't compare against NIFTY 50",
            "Backtest my portfolio, do not compare against NIFTY 50",
            "Backtest my portfolio, don't compare with NIFTY 50",
            "Backtest my portfolio without comparing against NIFTY 50",
            "Backtest my portfolio, not against NIFTY 50",
            "Backtest my portfolio holding NIFTY 50 ETF",
        ]
        for message in negative_cases:
            cfg = extract_backtest_config(message, reference_date=self.fixed_ref_date)
            self.assertIsNone(
                cfg.benchmark_ticker,
                f"Negative/unrelated query '{message}' incorrectly extracted benchmark: {cfg.benchmark_ticker}",
            )

    # -------------------------------------------------------------------------
    # Date Extraction & Semantics
    # -------------------------------------------------------------------------

    def test_relative_dates_last_2_years(self):
        """Case 6: 'last 2 years' -> from 2 years prior to reference date."""
        cfg = extract_backtest_config(
            "Backtest for the last 2 years",
            reference_date=self.fixed_ref_date,
        )
        self.assertEqual(cfg.from_date, "2024-09-13")
        self.assertEqual(cfg.to_date, "2026-09-13")

    def test_relative_dates_past_1_year_and_6_months(self):
        """Verify 1 year and 6 months relative date derivation."""
        cfg_1y = extract_backtest_config(
            "past 1 year historical simulation",
            reference_date=self.fixed_ref_date,
        )
        self.assertEqual(cfg_1y.from_date, "2025-09-13")
        self.assertEqual(cfg_1y.to_date, "2026-09-13")

        cfg_6m = extract_backtest_config(
            "last 6 months walk forward",
            reference_date=self.fixed_ref_date,
        )
        self.assertEqual(cfg_6m.from_date, "2026-03-13")
        self.assertEqual(cfg_6m.to_date, "2026-09-13")

    def test_explicit_date_ranges(self):
        """Case 7: Explicit date ranges in ISO and Month-Year formats."""
        # ISO format
        cfg_iso = extract_backtest_config("from 2024-01-01 to 2025-06-01")
        self.assertEqual(cfg_iso.from_date, "2024-01-01")
        self.assertEqual(cfg_iso.to_date, "2025-06-01")

        # Month Year format
        cfg_month = extract_backtest_config("from January 2024 to December 2025")
        self.assertEqual(cfg_month.from_date, "2024-01-01")
        self.assertEqual(cfg_month.to_date, "2025-12-31")

    def test_conflicting_dates_raises_validation_error(self):
        """Case 8: Conflicting relative date specifications raise BacktestExtractionError."""
        with self.assertRaises(BacktestExtractionError) as ctx:
            extract_backtest_config("last 2 years and past 5 years")
        self.assertIn("Conflicting", str(ctx.exception))

    def test_invalid_date_range_start_after_end_rejected(self):
        """Case 19: start date after end date raises BacktestExtractionError."""
        with self.assertRaises(BacktestExtractionError) as ctx:
            extract_backtest_config("from 2025-12-31 to 2024-01-01")
        self.assertIn("cannot be after end date", str(ctx.exception))

    def test_invalid_calendar_date_raises_extraction_error(self):
        """Explicit invalid calendar dates must raise BacktestExtractionError."""
        invalid_cases = [
            "from 2024-99-99 to 2025-01-01",
            "from 2024-01-01 to 2025-99-99",
            "from 2024-02-30 to 2024-03-31",
            "from 2023-02-29 to 2024-01-01",
        ]
        for query in invalid_cases:
            with self.assertRaises(BacktestExtractionError):
                extract_backtest_config(query, reference_date=self.fixed_ref_date)

        # Also test direct instantiation on model validator
        with self.assertRaises(BacktestExtractionError):
            ExtractedBacktestConfig(from_date="2024-99-99", to_date="2025-01-01")
        with self.assertRaises(BacktestExtractionError):
            ExtractedBacktestConfig(from_date="2024-01-01", to_date="2025-99-99")

    # -------------------------------------------------------------------------
    # Capital Extraction & Normalization
    # -------------------------------------------------------------------------

    def test_extract_capital_with_50k(self):
        """Case 9: 'with 50k' -> 50000.0."""
        cfg = extract_backtest_config("Backtest my portfolio with 50k")
        self.assertEqual(cfg.initial_capital, 50000.0)

    def test_explicit_initial_capital(self):
        """Case 10: 'initial capital 250000' and '1 lakh' notation."""
        cfg1 = extract_backtest_config("initial capital 250000 against NIFTY 50")
        self.assertEqual(cfg1.initial_capital, 250000.0)

        cfg2 = extract_backtest_config("start with 100k")
        self.assertEqual(cfg2.initial_capital, 100000.0)

        cfg3 = extract_backtest_config("starting with 1 lakh")
        self.assertEqual(cfg3.initial_capital, 100000.0)

    def test_negative_capital_rejected(self):
        """Case 17: Negative initial capital raises BacktestExtractionError."""
        with self.assertRaises(BacktestExtractionError) as ctx:
            extract_backtest_config("start with -50000")
        self.assertIn("strictly positive", str(ctx.exception))

    # -------------------------------------------------------------------------
    # Rebalance Frequency
    # -------------------------------------------------------------------------

    def test_rebalance_frequency_monthly_quarterly_annually(self):
        """Cases 11, 12, 13: Rebalance frequencies recognized."""
        cfg_m = extract_backtest_config("rebalance monthly")
        self.assertEqual(cfg_m.rebalance_frequency, "monthly")

        cfg_q = extract_backtest_config("rebalance quarterly")
        self.assertEqual(cfg_q.rebalance_frequency, "quarterly")

        cfg_a = extract_backtest_config("rebalance annually")
        self.assertEqual(cfg_a.rebalance_frequency, "annually")

        cfg_p = extract_backtest_config("periodic rebalancing")
        self.assertEqual(cfg_p.rebalance_frequency, "periodic")

    # -------------------------------------------------------------------------
    # Numerical Parameters
    # -------------------------------------------------------------------------

    def test_transaction_cost_bps_and_pct(self):
        """Case 14: Transaction cost in bps and percentage."""
        cfg_bps = extract_backtest_config("with 10 bps transaction cost")
        self.assertEqual(cfg_bps.transaction_cost_bps, 10.0)

        cfg_pct = extract_backtest_config("with 0.1% transaction cost")
        self.assertEqual(cfg_pct.transaction_cost_bps, 10.0)

    def test_risk_free_rate(self):
        """Case 15: Risk-free rate in percentage and decimal."""
        cfg_pct = extract_backtest_config("risk free rate 6.5%")
        self.assertEqual(cfg_pct.risk_free_rate, 0.065)

        cfg_dec = extract_backtest_config("risk-free rate 0.05")
        self.assertEqual(cfg_dec.risk_free_rate, 0.05)

    def test_min_and_max_weights(self):
        """Case 16: Min and max weight bounds in percentage and decimal."""
        cfg = extract_backtest_config("minimum weight 10%, maximum weight 70%")
        self.assertEqual(cfg.min_weight, 0.10)
        self.assertEqual(cfg.max_weight, 0.70)

    def test_window_and_step_days(self):
        """Verify in-sample window and out-of-sample step days."""
        cfg = extract_backtest_config("252 day window and 21 day step")
        self.assertEqual(cfg.in_sample_window_days, 252)
        self.assertEqual(cfg.out_of_sample_step_days, 21)

    def test_min_weight_exceeding_max_weight_rejected(self):
        """Case 18: min_weight > max_weight raises BacktestExtractionError."""
        with self.assertRaises(BacktestExtractionError) as ctx:
            extract_backtest_config("min weight 50% and max weight 20%")
        self.assertIn("cannot exceed maximum weight", str(ctx.exception))

    # -------------------------------------------------------------------------
    # Workflow Kwargs Conversion
    # -------------------------------------------------------------------------

    def test_to_workflow_kwargs_mapping(self):
        """Verify ExtractedBacktestConfig maps correctly to PortfolioWorkflowInput fields."""
        cfg = extract_backtest_config(
            "Backtest my portfolio against NIFTY 50 for the last 2 years with 50k quarterly, 10 bps, risk free rate 6.5%",
            reference_date=self.fixed_ref_date,
        )
        kwargs = cfg.to_workflow_kwargs()
        expected = {
            "backtest_benchmark_ticker": "NIFTY 50",
            "backtest_from_date": "2024-09-13",
            "backtest_to_date": "2026-09-13",
            "backtest_initial_capital": 50000.0,
            "backtest_rebalance_frequency": "quarterly",
            "backtest_transaction_cost_bps": 10.0,
            "backtest_risk_free_rate": 0.065,
        }
        self.assertEqual(kwargs, expected)


class ConversationalBacktestAgentServiceTestCase(TestCase):
    """Test suite for Module 14 Phase 2: AgentService & Portfolio Workflow Input Alignment."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="test_backtest_user",
            email="backtest@example.com",
            password="password123",
        )
        self.other_user = User.objects.create_user(
            username="other_backtest_user",
            email="other@example.com",
            password="password123",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="My Growth Portfolio",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("2500.00"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5.0"),
            average_price=Decimal("3500.00"),
        )

        self.other_portfolio = Portfolio.objects.create(
            user=self.other_user,
            name="Other Portfolio",
        )
        Holding.objects.create(
            portfolio=self.other_portfolio,
            ticker="INFY",
            market="IN",
            quantity=Decimal("20.0"),
            average_price=Decimal("1500.00"),
        )

        self.fixed_ref_date = date(2026, 9, 13)
        self.mock_workflow = MagicMock()
        self.mock_workflow.run.return_value = AgentState(
            user_message="mock message",
            route="portfolio",
            results={
                "synthesis": AgentResult(response="Synthesized backtest output", tools_used=[])
            },
        )
        self.service = AgentService(workflow=self.mock_workflow)

    def test_1_backtest_request_detected_and_extractor_invoked(self):
        """Case 1: Backtest request detected and extractor invoked."""
        self.service.run(
            message="Backtest my portfolio against NIFTY 50",
            user=self.user,
            portfolio_id=self.portfolio.id,
            reference_date=self.fixed_ref_date,
        )
        self.mock_workflow.run.assert_called_once()
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertTrue(p_input.include_backtest)
        self.assertEqual(p_input.backtest_benchmark_ticker, "NIFTY 50")

    def test_2_normal_portfolio_request_does_not_enable_backtesting(self):
        """Case 2: Normal portfolio request does not enable backtesting."""
        self.service.run(
            message="Analyze my portfolio allocation",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        self.mock_workflow.run.assert_called_once()
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertFalse(p_input.include_backtest)

    def test_3_trusted_portfolio_id_attached_to_workflow_input(self):
        """Case 3: Trusted portfolio id is attached to PortfolioWorkflowInput."""
        self.service.run(
            message="Backtest my portfolio against NIFTY 50",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertEqual(p_input.django_portfolio_id, str(self.portfolio.id))

    def test_4_portfolio_belonging_to_another_user_is_rejected(self):
        """Case 4: A portfolio belonging to another user is rejected with 404."""
        with self.assertRaises(Http404):
            self.service.run(
                message="Backtest my portfolio against NIFTY 50",
                user=self.user,
                portfolio_id=self.other_portfolio.id,
            )
        self.mock_workflow.run.assert_not_called()

    def test_5_natural_language_prompt_cannot_override_trusted_portfolio_id(self):
        """Case 5: Natural-language prompt cannot override the trusted portfolio id."""
        message = f"Backtest portfolio {self.other_portfolio.id} against NIFTY 50"
        self.service.run(
            message=message,
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertEqual(p_input.django_portfolio_id, str(self.portfolio.id))
        self.assertNotEqual(p_input.django_portfolio_id, str(self.other_portfolio.id))

    def test_6_backtest_benchmark_and_relative_dates(self):
        """Case 6: 'Backtest my portfolio against NIFTY 50 for the last 2 years' results."""
        self.service.run(
            message="Backtest my portfolio against NIFTY 50 for the last 2 years",
            user=self.user,
            portfolio_id=self.portfolio.id,
            reference_date=self.fixed_ref_date,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertTrue(p_input.include_backtest)
        self.assertEqual(p_input.backtest_benchmark_ticker, "NIFTY 50")
        self.assertEqual(p_input.backtest_from_date, "2024-09-13")
        self.assertEqual(p_input.backtest_to_date, "2026-09-13")

    def test_7_explicit_initial_capital_propagated(self):
        """Case 7: Explicit initial capital is propagated."""
        self.service.run(
            message="Backtest my portfolio with 50k",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertEqual(p_input.backtest_initial_capital, 50000.0)

    def test_8_explicit_rebalance_frequency_propagated(self):
        """Case 8: Explicit rebalance frequency is propagated."""
        self.service.run(
            message="Backtest my portfolio quarterly",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertEqual(p_input.backtest_rebalance_frequency, "quarterly")

    def test_9_explicit_numerics_and_weights_propagated(self):
        """Case 9: Explicit transaction cost, risk-free rate, and weights propagated."""
        self.service.run(
            message="Backtest with 15 bps, risk free rate 6%, min weight 5%, max weight 40%",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertEqual(p_input.backtest_transaction_cost_bps, 15.0)
        self.assertAlmostEqual(p_input.backtest_risk_free_rate, 0.06)
        self.assertAlmostEqual(p_input.backtest_min_weight, 0.05)
        self.assertAlmostEqual(p_input.backtest_max_weight, 0.40)

    def test_10_omitted_optional_parameters_remain_default(self):
        """Case 10: Omitted optional parameters remain unset so canonical downstream defaults apply."""
        self.service.run(
            message="Backtest my portfolio against NIFTY 50",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertEqual(p_input.backtest_benchmark_ticker, "NIFTY 50")
        self.assertIsNone(p_input.backtest_from_date)
        self.assertIsNone(p_input.backtest_to_date)
        self.assertEqual(p_input.backtest_initial_capital, 100_000.0)
        self.assertEqual(p_input.backtest_rebalance_frequency, "monthly")
        self.assertEqual(p_input.backtest_in_sample_window_days, 252)
        self.assertEqual(p_input.backtest_out_of_sample_step_days, 21)
        self.assertEqual(p_input.backtest_transaction_cost_bps, 10.0)
        self.assertEqual(p_input.backtest_risk_free_rate, 0.0)
        self.assertEqual(p_input.backtest_min_weight, 0.0)
        self.assertEqual(p_input.backtest_max_weight, 1.0)

    def test_11_invalid_extracted_capital_prevents_workflow_execution(self):
        """Case 11: Invalid extracted capital prevents workflow execution."""
        with self.assertRaises(BacktestExtractionError):
            self.service.run(
                message="Backtest my portfolio start with -50000",
                user=self.user,
                portfolio_id=self.portfolio.id,
            )
        self.mock_workflow.run.assert_not_called()

    def test_12_invalid_date_range_prevents_workflow_execution(self):
        """Case 12: Invalid date range and calendar dates prevent workflow execution."""
        with self.assertRaises(BacktestExtractionError):
            self.service.run(
                message="Backtest my portfolio from 2025-12-31 to 2024-01-01",
                user=self.user,
                portfolio_id=self.portfolio.id,
            )
        self.mock_workflow.run.assert_not_called()

        with self.assertRaises(BacktestExtractionError):
            self.service.run(
                message="Backtest my portfolio from 2024-99-99 to 2025-01-01",
                user=self.user,
                portfolio_id=self.portfolio.id,
            )
        self.mock_workflow.run.assert_not_called()

    def test_13_invalid_weight_bounds_prevents_workflow_execution(self):
        """Case 13: Invalid weight bounds prevent workflow execution."""
        with self.assertRaises(BacktestExtractionError):
            self.service.run(
                message="Backtest my portfolio with min weight 50% and max weight 20%",
                user=self.user,
                portfolio_id=self.portfolio.id,
            )
        self.mock_workflow.run.assert_not_called()

    def test_14_existing_portfolio_request_behavior_unchanged(self):
        """Case 14: Existing portfolio request behavior unchanged."""
        self.service.run(
            message="Analyze my portfolio",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertFalse(p_input.include_backtest)
        self.assertIsNone(p_input.optimization_input)

    def test_15_existing_financial_market_news_routing_unchanged(self):
        """Case 15: Existing financial/market/news routing unchanged."""
        self.service.run(
            message="Show Reliance's quarterly revenue",
            ticker="RELIANCE",
            market="IN",
        )
        _, kwargs = self.mock_workflow.run.call_args
        self.assertNotIn("portfolio_input", kwargs)

    def test_16_existing_portfolio_optimization_does_not_enable_backtest(self):
        """Case 16: Existing portfolio optimization/risk requests do not accidentally enable backtest."""
        self.service.run(
            message="Optimize my portfolio",
            user=self.user,
            portfolio_id=self.portfolio.id,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertIsNotNone(p_input.optimization_input)
        self.assertFalse(p_input.include_backtest)

    def test_17_final_portfolio_workflow_input_contains_all_aligned_fields(self):
        """Case 17: Final PortfolioWorkflowInput contains correct django_portfolio_id, include_backtest, and parameters."""
        self.service.run(
            message="Backtest my portfolio against NIFTY 50 for the last 2 years with 50k quarterly",
            user=self.user,
            portfolio_id=self.portfolio.id,
            reference_date=self.fixed_ref_date,
        )
        _, kwargs = self.mock_workflow.run.call_args
        p_input = kwargs["portfolio_input"]
        self.assertEqual(p_input.django_portfolio_id, str(self.portfolio.id))
        self.assertTrue(p_input.include_backtest)
        self.assertEqual(p_input.backtest_benchmark_ticker, "NIFTY 50")
        self.assertEqual(p_input.backtest_from_date, "2024-09-13")
        self.assertEqual(p_input.backtest_to_date, "2026-09-13")
        self.assertEqual(p_input.backtest_initial_capital, 50000.0)
        self.assertEqual(p_input.backtest_rebalance_frequency, "quarterly")

    def test_unauthenticated_user_access_portfolio_raises_error(self):
        """Authentication is required to access portfolio."""
        with self.assertRaises(ValueError) as ctx:
            self.service.run(
                message="Backtest my portfolio",
                user=None,
                portfolio_id=self.portfolio.id,
            )
        self.assertIn("Authentication is required", str(ctx.exception))

    def test_backtest_without_portfolio_context_raises_error(self):
        """Conversational backtest without portfolio_id or portfolio_input raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.service.run(
                message="Backtest my portfolio against NIFTY 50",
                user=self.user,
            )
        self.assertIn("portfolio is required for backtesting", str(ctx.exception).lower())

    def test_backtest_with_foreign_portfolio_input_rejected(self):
        """A portfolio_input pointing to another user's database portfolio is rejected."""
        from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
        from apps.ai.portfolio.schemas import Portfolio as PortfolioSchema, Holding as HoldingSchema

        p_schema = PortfolioSchema(
            id=str(self.other_portfolio.id),
            name=self.other_portfolio.name,
            holdings=[
                HoldingSchema(ticker="INFY", market="IN", quantity=20.0, average_price=1500.0)
            ],
        )
        p_input = PortfolioWorkflowInput(
            portfolio=p_schema,
            django_portfolio_id=str(self.other_portfolio.id),
        )

        with self.assertRaises(Http404):
            self.service.run(
                message="Backtest my portfolio against NIFTY 50",
                user=self.user,
                portfolio_input=p_input,
            )

    def test_backtest_with_internal_synthetic_portfolio_input_preserved(self):
        """Internal/test synthetic portfolio_inputs not matching DB records are preserved."""
        from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
        from apps.ai.portfolio.schemas import Portfolio as PortfolioSchema, Holding as HoldingSchema

        p_schema = PortfolioSchema(
            id="synth-001",
            name="Synthetic Portfolio",
            holdings=[
                HoldingSchema(ticker="RELIANCE", market="IN", quantity=10.0, average_price=2500.0)
            ],
        )
        p_input = PortfolioWorkflowInput(
            portfolio=p_schema,
            django_portfolio_id="synth-001",
        )

        self.service.run(
            message="Backtest my portfolio against NIFTY 50",
            user=self.user,
            portfolio_input=p_input,
        )
        _, kwargs = self.mock_workflow.run.call_args
        inp = kwargs["portfolio_input"]
        self.assertTrue(inp.include_backtest)
        self.assertEqual(inp.django_portfolio_id, "synth-001")

    def test_backtest_with_malformed_portfolio_id_in_portfolio_input_rejected(self):
        """A malformed django_portfolio_id supplied to an authenticated caller raises ValueError."""
        from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
        from apps.ai.portfolio.schemas import Portfolio as PortfolioSchema, Holding as HoldingSchema

        p_schema = PortfolioSchema(
            id="non-uuid-portfolio",
            name="Malformed Portfolio",
            holdings=[
                HoldingSchema(ticker="RELIANCE", market="IN", quantity=10.0, average_price=2500.0)
            ],
        )
        p_input = PortfolioWorkflowInput(
            portfolio=p_schema,
            django_portfolio_id="malformed-non-uuid-id",
        )

        with self.assertRaises(ValueError) as ctx:
            self.service.run(
                message="Backtest my portfolio against NIFTY 50",
                user=self.user,
                portfolio_input=p_input,
            )
        self.assertIn("Invalid portfolio id", str(ctx.exception))
        self.mock_workflow.run.assert_not_called()

    def test_backtest_session_evidence_contract(self):
        """Verify portfolio_backtest appears consistently across AgentState, ResearchEvidence, and synthesis."""
        from apps.research.services.session_service import ResearchSessionService
        from apps.ai.agents.synthesis import FinalSynthesisAgent

        # 1. State with portfolio_backtest deterministic payload
        bt_payload = {
            "success": True,
            "benchmark_ticker": "NIFTY 50",
            "tickers": ["RELIANCE", "TCS"],
            "strategy_metrics": {
                "cagr": 0.152,
                "volatility": 0.12,
                "sharpe_ratio": 1.25,
                "max_drawdown": 0.08,
            },
            "buy_and_hold_metrics": {"cagr": 0.11},
            "benchmark_metrics": {"cagr": 0.12},
            "rebalance_count": 4,
            "equity_curve_sample": [{"date": "2024-01-01", "portfolio_value": 100000.0}],
        }
        thread_id = f"contract-thread-{self.portfolio.id}"
        state = AgentState(
            user_message="Backtest my portfolio against NIFTY 50",
            route="portfolio",
            results={
                "portfolio_backtest": bt_payload,
            },
        )

        # 2. Synthesis context includes PORTFOLIO BACKTEST EVIDENCE
        synth_context = FinalSynthesisAgent._build_context(state)
        self.assertIn("PORTFOLIO BACKTEST EVIDENCE", synth_context)
        self.assertEqual(synth_context["PORTFOLIO BACKTEST EVIDENCE"], bt_payload)

        # 3. Structured evidence collection preserves portfolio_backtest verbatim
        structured_evidence = FinalSynthesisAgent._collect_structured_evidence(state)
        self.assertIn("portfolio_backtest", structured_evidence)
        self.assertEqual(structured_evidence["portfolio_backtest"]["benchmark_ticker"], "NIFTY 50")

        # 4. ResearchSessionService persistence preserves portfolio_backtest evidence
        session = ResearchSessionService.create_session(
            user_message=state.user_message,
            user=self.user,
            route="portfolio",
            thread_id=thread_id,
        )
        ResearchSessionService.save_workflow_result(
            session_id=session.id,
            agent_state=state,
        )

        evidence = ResearchEvidence.objects.filter(session=session, agent_name="portfolio_backtest").first()
        self.assertIsNotNone(evidence)
        self.assertIsInstance(evidence.structured_data, dict)
        self.assertEqual(evidence.structured_data["benchmark_ticker"], "NIFTY 50")
        self.assertEqual(evidence.structured_data["strategy_metrics"]["cagr"], 0.152)

    def test_other_routes_regression_financial_market_news_general(self):
        """Verify financial, market, news, general requests remain unchanged."""
        cases = [
            ("Show Reliance quarterly revenue", "RELIANCE", "IN"),
            ("What is the current stock price of Apple?", "AAPL", "US"),
            ("Latest news about semiconductor tariffs", None, None),
            ("Explain price to earnings ratio", None, None),
        ]
        router = WorkflowRouter()
        for message, ticker, market in cases:
            # Router does not classify these as backtest
            self.assertFalse(router.is_backtest_intent(message))
            self.service.run(
                message=message,
                user=self.user,
                ticker=ticker,
                market=market,
            )
            _, kwargs = self.mock_workflow.run.call_args
            self.assertIsNone(kwargs.get("portfolio_input"))
