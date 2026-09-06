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

    def test_portfolio_aggregation_across_multiple_holdings(self):
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

        self.assertEqual(result.invested_value, 12900.0)
        self.assertEqual(result.current_value, 14000.0)
        self.assertEqual(result.profit_loss, 1100.0)
        self.assertAlmostEqual(result.profit_loss_percentage, 8.5271318)
        self.assertEqual(result.holdings_count, 2)

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
