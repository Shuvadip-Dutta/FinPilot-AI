from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import Holding, Portfolio


class PortfolioWorkflowInputTestCase(SimpleTestCase):

    @staticmethod
    def _portfolio() -> Portfolio:
        return Portfolio(
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
                    average_price=3500,
                ),
            ]
        )

    @staticmethod
    def _optimization_input() -> OptimizationInput:
        return OptimizationInput(
            tickers=["RELIANCE", "TCS"],
            historical_prices={
                "RELIANCE": [1200, 1210, 1190, 1220],
                "TCS": [3500, 3520, 3480, 3510],
            },
            risk_free_rate=0.02,
        )

    def test_portfolio_is_required(self):
        workflow_input = PortfolioWorkflowInput(
            portfolio=self._portfolio(),
        )

        self.assertEqual(
            len(workflow_input.portfolio.holdings),
            2,
        )

        self.assertIsNone(
            workflow_input.optimization_input,
        )

    def test_optimization_input_is_optional(self):
        workflow_input = PortfolioWorkflowInput(
            portfolio=self._portfolio(),
            optimization_input=self._optimization_input(),
        )

        self.assertIsNotNone(
            workflow_input.optimization_input,
        )

    def test_invalid_portfolio_is_rejected(self):
        with self.assertRaises(ValidationError):
            PortfolioWorkflowInput(
                portfolio=None,
            )