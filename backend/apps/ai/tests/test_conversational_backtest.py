"""Unit and integration tests for Module 14 Phase 1: Conversational Backtest Intent & Extraction."""

from datetime import date
from django.test import SimpleTestCase

from apps.ai.graph.router import WorkflowRouter
from apps.ai.portfolio.backtest_extractor import (
    BacktestExtractionError,
    BacktestParameterExtractor,
    ExtractedBacktestConfig,
    extract_backtest_config,
)


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
