from django.test import SimpleTestCase
from pydantic import ValidationError

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
