from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.portfolio.adapters import ResearchMarketDataAdapter
from apps.ai.portfolio.intelligence import (
    PortfolioIntelligenceService,
    PortfolioMarketDataError,
)
from apps.ai.portfolio.schemas import Holding, Portfolio


class PortfolioIntelligenceTestCase(SimpleTestCase):

    def test_valid_holding(self):
        holding = Holding(
            ticker="reliance",
            market="IN",
            quantity=10,
            average_price=1200,
        )

        self.assertEqual(holding.ticker, "RELIANCE")
        self.assertEqual(holding.market, "IN")

    def test_invalid_quantity(self):
        with self.assertRaises(ValidationError):
            Holding(
                ticker="RELIANCE",
                market="IN",
                quantity=0,
                average_price=1200,
            )

    def test_invalid_average_price(self):
        with self.assertRaises(ValidationError):
            Holding(
                ticker="RELIANCE",
                market="IN",
                quantity=10,
                average_price=0,
            )

    def test_invalid_market(self):
        with self.assertRaises(ValidationError):
            Holding(
                ticker="RELIANCE",
                market="UK",
                quantity=10,
                average_price=1200,
            )

    def test_valid_portfolio(self):
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="RELIANCE",
                    market="IN",
                    quantity=10,
                    average_price=1200,
                )
            ]
        )

        self.assertEqual(len(portfolio.holdings), 1)

    def test_invested_current_and_profit_loss_calculation(self):
        service = PortfolioIntelligenceService(
            market_data_tool=lambda **kwargs: {"last_price": 1300.0}
        )
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="RELIANCE",
                    market="IN",
                    quantity=10,
                    average_price=1200,
                )
            ]
        )

        result = service.analyze(portfolio)

        self.assertEqual(result.invested_value, 12000.0)
        self.assertEqual(result.current_value, 13000.0)
        self.assertEqual(result.profit_loss, 1000.0)
        self.assertAlmostEqual(result.profit_loss_percentage, 8.3333333)
        self.assertEqual(result.holdings_count, 1)

    def test_portfolio_aggregation_across_multiple_in_holdings(self):
        """Pure IN portfolio with multiple holdings aggregates values in INR."""
        prices = {"RELIANCE": 1300.0, "TCS": 3500.0}
        service = PortfolioIntelligenceService(
            market_data_tool=lambda **kwargs: {
                "last_price": prices[kwargs["ticker"]]
            }
        )
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="RELIANCE",
                    market="IN",
                    quantity=10,
                    average_price=1200,
                ),
                Holding(
                    ticker="TCS",
                    market="IN",
                    quantity=5,
                    average_price=3400,
                ),
            ]
        )

        result = service.analyze(portfolio)

        self.assertFalse(result.is_mixed_currency)
        self.assertEqual(result.currency, "INR")
        self.assertEqual(result.invested_value, 29000.0)
        self.assertEqual(result.current_value, 30500.0)
        self.assertEqual(result.profit_loss, 1500.0)
        self.assertAlmostEqual(result.profit_loss_percentage, 5.17241379)
        self.assertEqual(result.holdings_count, 2)
        self.assertIsNotNone(result.currency_totals)
        self.assertIn("INR", result.currency_totals)

    def test_portfolio_aggregation_across_multiple_us_holdings(self):
        """Pure US portfolio with multiple holdings aggregates values in USD."""
        prices = {"AAPL": 200.0, "MSFT": 400.0}
        service = PortfolioIntelligenceService(
            market_data_tool=lambda **kwargs: {
                "last_price": prices[kwargs["ticker"]]
            }
        )
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="AAPL",
                    market="US",
                    quantity=5,
                    average_price=180,
                ),
                Holding(
                    ticker="MSFT",
                    market="US",
                    quantity=2,
                    average_price=350,
                ),
            ]
        )

        result = service.analyze(portfolio)

        self.assertFalse(result.is_mixed_currency)
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.invested_value, 1600.0)  # 5*180 + 2*350 = 900 + 700
        self.assertEqual(result.current_value, 1800.0)   # 5*200 + 2*400 = 1000 + 800
        self.assertEqual(result.profit_loss, 200.0)
        self.assertAlmostEqual(result.profit_loss_percentage, 12.5)
        self.assertEqual(result.holdings_count, 2)
        self.assertIsNotNone(result.currency_totals)
        self.assertIn("USD", result.currency_totals)

    def test_mixed_currency_portfolio_does_not_sum_nominally(self):
        """Mixed IN + US portfolio does NOT create a single nominal sum; returns separated per-currency totals."""
        prices = {"RELIANCE": 1300.0, "AAPL": 200.0}
        service = PortfolioIntelligenceService(
            market_data_tool=lambda **kwargs: {
                "last_price": prices[kwargs["ticker"]]
            }
        )
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="RELIANCE",
                    market="IN",
                    quantity=10,
                    average_price=1200,
                ),
                Holding(
                    ticker="AAPL",
                    market="US",
                    quantity=5,
                    average_price=180,
                ),
            ]
        )

        result = service.analyze(portfolio)

        # Never present a nominal mixed-currency sum as a single monetary total!
        self.assertTrue(result.is_mixed_currency)
        self.assertEqual(result.currency, "MIXED")
        self.assertIsNone(result.invested_value)
        self.assertIsNone(result.current_value)
        self.assertIsNone(result.profit_loss)
        self.assertIsNone(result.profit_loss_percentage)
        self.assertEqual(result.holdings_count, 2)

        # Verify separated per-currency totals
        self.assertIsNotNone(result.currency_totals)
        self.assertIn("INR", result.currency_totals)
        self.assertIn("USD", result.currency_totals)

        inr_totals = result.currency_totals["INR"]
        self.assertEqual(inr_totals.invested_value, 12000.0)
        self.assertEqual(inr_totals.current_value, 13000.0)
        self.assertEqual(inr_totals.profit_loss, 1000.0)
        self.assertAlmostEqual(inr_totals.profit_loss_percentage, 8.3333333)
        self.assertEqual(inr_totals.currency, "INR")
        self.assertEqual(inr_totals.currency_symbol, "₹")

        usd_totals = result.currency_totals["USD"]
        self.assertEqual(usd_totals.invested_value, 900.0)
        self.assertEqual(usd_totals.current_value, 1000.0)
        self.assertEqual(usd_totals.profit_loss, 100.0)
        self.assertAlmostEqual(usd_totals.profit_loss_percentage, 11.1111111)
        self.assertEqual(usd_totals.currency, "USD")
        self.assertEqual(usd_totals.currency_symbol, "$")

    def test_same_ticker_in_different_markets_uses_market_specific_quotes(self):
        """Cross-market ticker collision prevention: same ticker in IN and US uses market-specific quotes."""
        quotes = {
            ("IN", "XYZ"): 150.0,
            ("US", "XYZ"): 60.0,
        }
        service = PortfolioIntelligenceService(
            market_data_tool=lambda **kwargs: {
                "last_price": quotes[(kwargs["market"], kwargs["ticker"])]
            }
        )
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="XYZ",
                    market="IN",
                    quantity=10,
                    average_price=100.0,  # 10 * 100 = 1000 INR
                ),
                Holding(
                    ticker="XYZ",
                    market="US",
                    quantity=5,
                    average_price=50.0,   # 5 * 50 = 250 USD
                ),
            ]
        )

        result = service.analyze(portfolio)

        self.assertTrue(result.is_mixed_currency)
        self.assertIsNotNone(result.currency_totals)

        # Verify INR subtotal uses IN quote (150.0), NOT US quote (60.0)
        inr = result.currency_totals["INR"]
        self.assertEqual(inr.invested_value, 1000.0)
        self.assertEqual(inr.current_value, 1500.0)  # 10 * 150.0
        self.assertEqual(inr.profit_loss, 500.0)
        self.assertAlmostEqual(inr.profit_loss_percentage, 50.0)

        # Verify USD subtotal uses US quote (60.0), NOT IN quote (150.0)
        usd = result.currency_totals["USD"]
        self.assertEqual(usd.invested_value, 250.0)
        self.assertEqual(usd.current_value, 300.0)   # 5 * 60.0
        self.assertEqual(usd.profit_loss, 50.0)
        self.assertAlmostEqual(usd.profit_loss_percentage, 20.0)

        # Verify market_currency_context is keyed by market + ticker
        self.assertIn("IN:XYZ", result.market_currency_context)
        self.assertEqual(result.market_currency_context["IN:XYZ"]["currency"], "INR")
        self.assertIn("US:XYZ", result.market_currency_context)
        self.assertEqual(result.market_currency_context["US:XYZ"]["currency"], "USD")

    def test_zero_investment_edge_case(self):
        service = PortfolioIntelligenceService(
            market_data_tool=lambda **kwargs: {"last_price": 100.0}
        )

        result = service.analyze(Portfolio(holdings=[]))

        self.assertEqual(result.invested_value, 0.0)
        self.assertEqual(result.profit_loss_percentage, 0.0)

    def test_market_data_failure(self):
        def failing_market_data_tool(**kwargs):
            raise ValueError("Market data unavailable")

        service = PortfolioIntelligenceService(
            market_data_tool=failing_market_data_tool
        )
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="RELIANCE",
                    market="IN",
                    quantity=10,
                    average_price=1200,
                )
            ]
        )

        with self.assertRaises(PortfolioMarketDataError) as context:
            service.analyze(portfolio)

        self.assertIn("Market data unavailable", str(context.exception))

    def test_injected_market_data_prevents_external_api_or_llm_calls(self):
        calls = []

        def market_data_tool(**kwargs):
            calls.append(kwargs)
            return {"last_price": 1300.0}

        service = PortfolioIntelligenceService(
            market_data_tool=market_data_tool
        )
        portfolio = Portfolio(
            holdings=[
                Holding(
                    ticker="RELIANCE",
                    market="IN",
                    quantity=10,
                    average_price=1200,
                )
            ]
        )

        service.analyze(portfolio)

        self.assertEqual(
            calls,
            [{"ticker": "RELIANCE", "market": "IN"}],
        )

    def test_empty_ticker(self):
        with self.assertRaises(ValidationError):
            Holding(
                ticker="   ",
                market="IN",
                quantity=10,
                average_price=1200,
            )


class ResearchMarketDataAdapterTestCase(SimpleTestCase):
    """Focused unit tests for ResearchMarketDataAdapter."""

    def test_valid_quote_conversion(self):
        def get_market_data(ticker: str, market: str):
            return {
                "ticker": ticker,
                "market": market,
                "quotes": [
                    {
                        "exchange": "NSE",
                        "price": 1350.5,
                        "percent_change": 1.5,
                    }
                ],
            }

        adapter = ResearchMarketDataAdapter(get_market_data_fn=get_market_data)
        res = adapter(ticker="RELIANCE", market="IN")

        self.assertEqual(res, {"last_price": 1350.5})

    def test_multiple_quotes_deterministic_priority(self):
        def get_market_data(ticker: str, market: str):
            return {
                "ticker": ticker,
                "market": market,
                "quotes": [
                    {"exchange": "BSE", "price": 1348.0},
                    {"exchange": "NSE", "price": 1350.0},
                ],
            }

        adapter = ResearchMarketDataAdapter(get_market_data_fn=get_market_data)
        # Indian market defaults priority to NSE over BSE
        res = adapter(ticker="RELIANCE", market="IN")
        self.assertEqual(res, {"last_price": 1350.0})

        # US market priority (NASDAQ over NYSE)
        def get_us_market_data(ticker: str, market: str):
            return {
                "ticker": ticker,
                "market": market,
                "quotes": [
                    {"exchange": "NYSE", "price": 180.0},
                    {"exchange": "NASDAQ", "price": 182.5},
                ],
            }

        adapter_us = ResearchMarketDataAdapter(get_market_data_fn=get_us_market_data)
        res_us = adapter_us(ticker="AAPL", market="US")
        self.assertEqual(res_us, {"last_price": 182.5})

    def test_missing_quotes(self):
        def empty_quotes_data(ticker: str, market: str):
            return {"ticker": ticker, "market": market, "quotes": []}

        adapter = ResearchMarketDataAdapter(get_market_data_fn=empty_quotes_data)
        with self.assertRaises(PortfolioMarketDataError) as ctx:
            adapter(ticker="RELIANCE", market="IN")
        self.assertIn("contains no quotes", str(ctx.exception))

    def test_missing_or_invalid_price(self):
        def invalid_price_data(ticker: str, market: str):
            return {
                "ticker": ticker,
                "market": market,
                "quotes": [
                    {"exchange": "NSE", "price": None},
                    {"exchange": "BSE", "price": -50.0},
                    {"exchange": "MCX", "price": "invalid"},
                ],
            }

        adapter = ResearchMarketDataAdapter(get_market_data_fn=invalid_price_data)
        with self.assertRaises(PortfolioMarketDataError) as ctx:
            adapter(ticker="RELIANCE", market="IN")
        self.assertIn("does not contain a valid positive price", str(ctx.exception))

    def test_underlying_research_tool_failure(self):
        def failing_tool(ticker: str, market: str):
            raise ValueError("Upstox provider timeout")

        adapter = ResearchMarketDataAdapter(get_market_data_fn=failing_tool)
        with self.assertRaises(PortfolioMarketDataError) as ctx:
            adapter(ticker="RELIANCE", market="IN")
        self.assertIn("Upstox provider timeout", str(ctx.exception))

    def test_correct_ticker_market_forwarding(self):
        calls = []

        def tracking_tool(ticker: str, market: str):
            calls.append((ticker, market))
            return {
                "quotes": [{"exchange": "NSE", "price": 500.0}]
            }

        adapter = ResearchMarketDataAdapter(get_market_data_fn=tracking_tool)
        res = adapter(ticker="TCS", market="IN")

        self.assertEqual(calls, [("TCS", "IN")])
        self.assertEqual(res, {"last_price": 500.0})

    def test_integration_with_portfolio_intelligence_service(self):
        def mock_research_tool(ticker: str, market: str):
            prices = {"RELIANCE": 1300.0, "TCS": 3500.0}
            return {
                "ticker": ticker,
                "market": market,
                "quotes": [{"exchange": "NSE", "price": prices[ticker]}],
            }

        adapter = ResearchMarketDataAdapter(get_market_data_fn=mock_research_tool)
        service = PortfolioIntelligenceService(market_data_tool=adapter)

        portfolio = Portfolio(
            holdings=[
                Holding(ticker="RELIANCE", market="IN", quantity=10, average_price=1200),
                Holding(ticker="TCS", market="IN", quantity=5, average_price=3400),
            ]
        )

        result = service.analyze(portfolio)

        self.assertEqual(result.invested_value, 12000.0 + 17000.0)  # 29000.0
        self.assertEqual(result.current_value, 13000.0 + 17500.0)   # 30500.0
        self.assertEqual(result.profit_loss, 1500.0)
        self.assertAlmostEqual(result.profit_loss_percentage, (1500.0 / 29000.0) * 100)
        self.assertEqual(result.holdings_count, 2)
