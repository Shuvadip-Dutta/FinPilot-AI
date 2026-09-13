import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import (
    Holding as HoldingSchema,
    Portfolio as PortfolioSchema,
)
from apps.portfolio.builder import PortfolioWorkflowInputBuilder
from django.urls import reverse
from unittest.mock import MagicMock, patch

from apps.portfolio.alert_service import AlertService
from apps.portfolio.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertType,
    Holding,
    Portfolio,
    holding_to_schema,
    portfolio_to_schema,
)
from apps.portfolio.monitor import (
    MonitoringConfig,
    MonitoringEvent,
    MonitoringResult,
    PortfolioMonitorService,
)
from apps.portfolio.serializers import AlertSerializer

User = get_user_model()


class PortfolioModelTestCase(TestCase):
    """Test suite for Portfolio and Holding models and their schema conversion."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="investor1",
            email="investor1@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="investor2",
            email="investor2@example.com",
            password="securepassword456",
        )

    def test_portfolio_creation(self):
        """Test creating a portfolio with UUID pk and default/custom fields."""
        portfolio = Portfolio.objects.create(
            user=self.user,
            name="Retirement Fund",
        )

        self.assertIsInstance(portfolio.id, uuid.UUID)
        self.assertEqual(portfolio.name, "Retirement Fund")
        self.assertEqual(portfolio.user, self.user)
        self.assertIsNotNone(portfolio.created_at)
        self.assertIsNotNone(portfolio.updated_at)
        self.assertIn("Retirement Fund", str(portfolio))

    def test_holding_creation(self):
        """Test creating a holding with DecimalField quantity and average_price."""
        portfolio = Portfolio.objects.create(user=self.user, name="Tech Growth")
        holding = Holding.objects.create(
            portfolio=portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("15.5000"),
            average_price=Decimal("1250.7500"),
        )

        self.assertIsInstance(holding.id, uuid.UUID)
        self.assertEqual(holding.portfolio, portfolio)
        self.assertEqual(holding.ticker, "RELIANCE")
        self.assertEqual(holding.market, "IN")
        self.assertEqual(holding.quantity, Decimal("15.5000"))
        self.assertEqual(holding.average_price, Decimal("1250.7500"))
        self.assertIsNotNone(holding.created_at)
        self.assertIsNotNone(holding.updated_at)
        self.assertIn("RELIANCE", str(holding))

    def test_user_relationship(self):
        """Test relationship between User and Portfolio."""
        p1 = Portfolio.objects.create(user=self.user, name="Portfolio A")
        p2 = Portfolio.objects.create(user=self.user, name="Portfolio B")
        p3 = Portfolio.objects.create(user=self.other_user, name="Portfolio C")

        user_portfolios = self.user.portfolios.all()
        self.assertEqual(user_portfolios.count(), 2)
        self.assertIn(p1, user_portfolios)
        self.assertIn(p2, user_portfolios)
        self.assertNotIn(p3, user_portfolios)

        # Cascade delete when user is deleted
        self.other_user.delete()
        self.assertFalse(Portfolio.objects.filter(id=p3.id).exists())

    def test_portfolio_holding_relationship(self):
        """Test relationship between Portfolio and Holding."""
        portfolio = Portfolio.objects.create(user=self.user, name="Core Mix")
        h1 = Holding.objects.create(
            portfolio=portfolio,
            ticker="TCS",
            market="IN",
            quantity=Decimal("10.0000"),
            average_price=Decimal("3500.0000"),
        )
        h2 = Holding.objects.create(
            portfolio=portfolio,
            ticker="INFY",
            market="IN",
            quantity=Decimal("20.0000"),
            average_price=Decimal("1400.0000"),
        )

        holdings = portfolio.holdings.all()
        self.assertEqual(holdings.count(), 2)
        self.assertIn(h1, holdings)
        self.assertIn(h2, holdings)

        # Cascade delete when portfolio is deleted
        portfolio.delete()
        self.assertFalse(Holding.objects.filter(id=h1.id).exists())
        self.assertFalse(Holding.objects.filter(id=h2.id).exists())

    def test_unique_portfolio_ticker_market_constraint(self):
        """Test that a portfolio cannot have duplicate ticker in the same market."""
        portfolio = Portfolio.objects.create(user=self.user, name="Indexed")
        Holding.objects.create(
            portfolio=portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("5.0000"),
            average_price=Decimal("1200.0000"),
        )

        # Duplicate in the same portfolio and market must fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Holding.objects.create(
                    portfolio=portfolio,
                    ticker="RELIANCE",
                    market="IN",
                    quantity=Decimal("10.0000"),
                    average_price=Decimal("1250.0000"),
                )

        # Same ticker but different market (US) is permitted
        h_us = Holding.objects.create(
            portfolio=portfolio,
            ticker="RELIANCE",
            market="US",
            quantity=Decimal("2.0000"),
            average_price=Decimal("30.0000"),
        )
        self.assertIsNotNone(h_us.id)

        # Same ticker and market in a different portfolio is permitted
        portfolio_2 = Portfolio.objects.create(user=self.user, name="Indexed 2")
        h_other_portfolio = Holding.objects.create(
            portfolio=portfolio_2,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("5.0000"),
            average_price=Decimal("1200.0000"),
        )
        self.assertIsNotNone(h_other_portfolio.id)

    def test_positive_quantity(self):
        """Test that zero or negative quantity is rejected by clean() and constraints."""
        portfolio = Portfolio.objects.create(user=self.user, name="Validator Test")

        # Zero quantity
        holding_zero = Holding(
            portfolio=portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("0.0000"),
            average_price=Decimal("150.0000"),
        )
        with self.assertRaises(ValidationError):
            holding_zero.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                holding_zero.save()

        # Negative quantity
        holding_neg = Holding(
            portfolio=portfolio,
            ticker="MSFT",
            market="US",
            quantity=Decimal("-2.5000"),
            average_price=Decimal("200.0000"),
        )
        with self.assertRaises(ValidationError):
            holding_neg.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                holding_neg.save()

    def test_positive_average_price(self):
        """Test that zero or negative average_price is rejected by clean() and constraints."""
        portfolio = Portfolio.objects.create(user=self.user, name="Validator Test Price")

        # Zero average price
        holding_zero = Holding(
            portfolio=portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("10.0000"),
            average_price=Decimal("0.0000"),
        )
        with self.assertRaises(ValidationError):
            holding_zero.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                holding_zero.save()

        # Negative average price
        holding_neg = Holding(
            portfolio=portfolio,
            ticker="MSFT",
            market="US",
            quantity=Decimal("10.0000"),
            average_price=Decimal("-15.0000"),
        )
        with self.assertRaises(ValidationError):
            holding_neg.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                holding_neg.save()

    def test_orm_to_pydantic_conversion(self):
        """Test converting Django Portfolio and Holding into canonical Pydantic models."""
        portfolio = Portfolio.objects.create(user=self.user, name="Pydantic Bridge")
        h1 = Holding.objects.create(
            portfolio=portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("25.5000"),
            average_price=Decimal("1280.5000"),
        )
        h2 = Holding.objects.create(
            portfolio=portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("10.0000"),
            average_price=Decimal("175.2500"),
        )

        # Single holding conversion via model method
        schema_holding = h1.to_pydantic()
        self.assertIsInstance(schema_holding, HoldingSchema)

        # Single holding conversion via standalone function
        standalone_schema_holding = holding_to_schema(h2)
        self.assertIsInstance(standalone_schema_holding, HoldingSchema)

        # Portfolio conversion via model method
        schema_portfolio = portfolio.to_pydantic()
        self.assertIsInstance(schema_portfolio, PortfolioSchema)
        self.assertEqual(len(schema_portfolio.holdings), 2)

        # Portfolio conversion via standalone function
        standalone_portfolio = portfolio_to_schema(portfolio)
        self.assertIsInstance(standalone_portfolio, PortfolioSchema)
        self.assertEqual(len(standalone_portfolio.holdings), 2)

    def test_conversion_preserves_attributes(self):
        """Test that ticker, market, quantity, and average_price are accurately preserved."""
        portfolio = Portfolio.objects.create(user=self.user, name="Accuracy Test")
        holding = Holding.objects.create(
            portfolio=portfolio,
            ticker="tcs",  # lowercase, should be normalized to TCS on save
            market="IN",
            quantity=Decimal("42.1234"),
            average_price=Decimal("3456.7890"),
        )

        schema_holding = holding.to_pydantic()

        # Check exact values preserved
        self.assertEqual(schema_holding.ticker, "TCS")
        self.assertEqual(schema_holding.market, "IN")
        self.assertAlmostEqual(schema_holding.quantity, 42.1234, places=4)
        self.assertAlmostEqual(schema_holding.average_price, 3456.7890, places=4)

        # Ensure types are floats as defined in Pydantic Holding contract
        self.assertIsInstance(schema_holding.quantity, float)
        self.assertIsInstance(schema_holding.average_price, float)


class PortfolioAPITestCase(TestCase):
    """Test suite for Portfolio and Holding REST API endpoints."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            username="user_a",
            email="usera@example.com",
            password="password123",
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            email="userb@example.com",
            password="password123",
        )

    def test_unauthenticated_access(self):
        """Test unauthenticated requests are rejected with 401 Unauthorized."""
        res_list = self.client.get("/api/v1/portfolio/")
        self.assertEqual(res_list.status_code, status.HTTP_401_UNAUTHORIZED)

        res_create = self.client.post("/api/v1/portfolio/", {"name": "New Portfolio"})
        self.assertEqual(res_create.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_portfolio_creation(self):
        """Test creating a portfolio as an authenticated user."""
        self.client.force_authenticate(user=self.user_a)
        res = self.client.post(
            "/api/v1/portfolio/",
            {"name": "Growth Fund"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["name"], "Growth Fund")
        self.assertIn("id", res.data)
        self.assertEqual(Portfolio.objects.filter(user=self.user_a).count(), 1)

    def test_portfolio_listing(self):
        """Test listing only portfolios belonging to the authenticated user."""
        Portfolio.objects.create(user=self.user_a, name="User A Portfolio 1")
        Portfolio.objects.create(user=self.user_a, name="User A Portfolio 2")
        Portfolio.objects.create(user=self.user_b, name="User B Portfolio")

        self.client.force_authenticate(user=self.user_a)
        res = self.client.get("/api/v1/portfolio/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        names = [p["name"] for p in res.data]
        self.assertIn("User A Portfolio 1", names)
        self.assertIn("User A Portfolio 2", names)
        self.assertNotIn("User B Portfolio", names)

    def test_portfolio_retrieval(self):
        """Test retrieving a portfolio by ID."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Main Portfolio")
        self.client.force_authenticate(user=self.user_a)

        res = self.client.get(f"/api/v1/portfolio/{portfolio.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], str(portfolio.id))
        self.assertEqual(res.data["name"], "Main Portfolio")

    def test_portfolio_update(self):
        """Test updating portfolio name via PATCH."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Old Name")
        self.client.force_authenticate(user=self.user_a)

        res = self.client.patch(
            f"/api/v1/portfolio/{portfolio.id}/",
            {"name": "New Updated Name"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "New Updated Name")

        portfolio.refresh_from_db()
        self.assertEqual(portfolio.name, "New Updated Name")

    def test_portfolio_deletion(self):
        """Test deleting a portfolio by ID."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="To Be Deleted")
        self.client.force_authenticate(user=self.user_a)

        res = self.client.delete(f"/api/v1/portfolio/{portfolio.id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Portfolio.objects.filter(id=portfolio.id).exists())

    def test_holding_creation(self):
        """Test adding a holding to a user's portfolio."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Holdings Test")
        self.client.force_authenticate(user=self.user_a)

        payload = {
            "ticker": "reliance",
            "market": "IN",
            "quantity": "10.5000",
            "average_price": "1200.7500",
        }
        res = self.client.post(
            f"/api/v1/portfolio/{portfolio.id}/holdings/",
            payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["ticker"], "RELIANCE")
        self.assertEqual(res.data["market"], "IN")
        self.assertEqual(res.data["quantity"], "10.5000")
        self.assertEqual(res.data["average_price"], "1200.7500")

    def test_holding_update(self):
        """Test updating holding fields."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Holdings Test")
        holding = Holding.objects.create(
            portfolio=portfolio,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5.0000"),
            average_price=Decimal("3400.0000"),
        )
        self.client.force_authenticate(user=self.user_a)

        res = self.client.patch(
            f"/api/v1/portfolio/{portfolio.id}/holdings/{holding.id}/",
            {"quantity": "15.0000", "average_price": "3500.0000"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["quantity"], "15.0000")

        holding.refresh_from_db()
        self.assertEqual(holding.quantity, Decimal("15.0000"))

    def test_holding_deletion(self):
        """Test deleting a holding."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Holdings Test")
        holding = Holding.objects.create(
            portfolio=portfolio,
            ticker="INFY",
            market="IN",
            quantity=Decimal("10.0000"),
            average_price=Decimal("1400.0000"),
        )
        self.client.force_authenticate(user=self.user_a)

        res = self.client.delete(
            f"/api/v1/portfolio/{portfolio.id}/holdings/{holding.id}/"
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Holding.objects.filter(id=holding.id).exists())

    def test_user_a_cannot_access_user_b_portfolio(self):
        """Test User A receives 404 when attempting to access User B's portfolio."""
        portfolio_b = Portfolio.objects.create(user=self.user_b, name="User B Portfolio")
        self.client.force_authenticate(user=self.user_a)

        res_get = self.client.get(f"/api/v1/portfolio/{portfolio_b.id}/")
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        res_patch = self.client.patch(
            f"/api/v1/portfolio/{portfolio_b.id}/",
            {"name": "Hacked"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_404_NOT_FOUND)

        res_delete = self.client.delete(f"/api/v1/portfolio/{portfolio_b.id}/")
        self.assertEqual(res_delete.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_modify_user_b_holding(self):
        """Test User A cannot list, create, update, or delete User B's holdings."""
        portfolio_b = Portfolio.objects.create(user=self.user_b, name="User B Portfolio")
        holding_b = Holding.objects.create(
            portfolio=portfolio_b,
            ticker="AAPL",
            market="US",
            quantity=Decimal("5.0000"),
            average_price=Decimal("170.0000"),
        )
        self.client.force_authenticate(user=self.user_a)

        res_list = self.client.get(f"/api/v1/portfolio/{portfolio_b.id}/holdings/")
        self.assertEqual(res_list.status_code, status.HTTP_404_NOT_FOUND)

        res_create = self.client.post(
            f"/api/v1/portfolio/{portfolio_b.id}/holdings/",
            {"ticker": "MSFT", "market": "US", "quantity": "10", "average_price": "200"},
            format="json",
        )
        self.assertEqual(res_create.status_code, status.HTTP_404_NOT_FOUND)

        res_patch = self.client.patch(
            f"/api/v1/portfolio/{portfolio_b.id}/holdings/{holding_b.id}/",
            {"quantity": "100.0000"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_404_NOT_FOUND)

        res_delete = self.client.delete(
            f"/api/v1/portfolio/{portfolio_b.id}/holdings/{holding_b.id}/"
        )
        self.assertEqual(res_delete.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_quantity(self):
        """Test creating or updating a holding with non-positive quantity fails validation."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Validation Test")
        self.client.force_authenticate(user=self.user_a)

        payload_zero = {
            "ticker": "RELIANCE",
            "market": "IN",
            "quantity": "0.0000",
            "average_price": "1200.0000",
        }
        res_zero = self.client.post(
            f"/api/v1/portfolio/{portfolio.id}/holdings/",
            payload_zero,
            format="json",
        )
        self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", res_zero.data)

        payload_neg = {
            "ticker": "RELIANCE",
            "market": "IN",
            "quantity": "-5.0000",
            "average_price": "1200.0000",
        }
        res_neg = self.client.post(
            f"/api/v1/portfolio/{portfolio.id}/holdings/",
            payload_neg,
            format="json",
        )
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_average_price(self):
        """Test creating or updating a holding with non-positive average_price fails validation."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Validation Test Price")
        self.client.force_authenticate(user=self.user_a)

        payload_zero = {
            "ticker": "RELIANCE",
            "market": "IN",
            "quantity": "10.0000",
            "average_price": "0.0000",
        }
        res_zero = self.client.post(
            f"/api/v1/portfolio/{portfolio.id}/holdings/",
            payload_zero,
            format="json",
        )
        self.assertEqual(res_zero.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("average_price", res_zero.data)

        payload_neg = {
            "ticker": "RELIANCE",
            "market": "IN",
            "quantity": "10.0000",
            "average_price": "-100.0000",
        }
        res_neg = self.client.post(
            f"/api/v1/portfolio/{portfolio.id}/holdings/",
            payload_neg,
            format="json",
        )
        self.assertEqual(res_neg.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_holding_constraint(self):
        """Test creating a duplicate holding for same portfolio, ticker, and market fails."""
        portfolio = Portfolio.objects.create(user=self.user_a, name="Duplicate Test")
        Holding.objects.create(
            portfolio=portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0000"),
            average_price=Decimal("1200.0000"),
        )
        self.client.force_authenticate(user=self.user_a)

        payload_duplicate = {
            "ticker": "RELIANCE",
            "market": "IN",
            "quantity": "5.0000",
            "average_price": "1250.0000",
        }
        res = self.client.post(
            f"/api/v1/portfolio/{portfolio.id}/holdings/",
            payload_duplicate,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", res.data)


class PortfolioWorkflowInputBuilderTestCase(TestCase):
    """Test suite for PortfolioWorkflowInputBuilder."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="builder_user",
            email="builder@example.com",
            password="password123",
        )

    @staticmethod
    def _mock_historical_data(
        ticker: str, to_date: str, from_date: str | None = None, market: str = "IN"
    ):
        prices_map = {
            "RELIANCE": [1200.0, 1210.0, 1220.0, 1215.0, 1230.0],
            "TCS": [3400.0, 3420.0, 3410.0, 3450.0, 3480.0],
            "INFY": [1400.0, 1410.0, 1420.0, 1430.0],
        }
        prices = prices_map.get(ticker.upper(), [100.0, 102.0, 104.0, 105.0])
        return {
            "ticker": ticker,
            "market": market,
            "candles": [{"close": p} for p in prices],
        }

    def test_orm_portfolio_to_canonical_analysis_input(self):
        portfolio_orm = Portfolio.objects.create(user=self.user, name="ORM Test")
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=self._mock_historical_data
        )
        res = builder.build_analysis_input(portfolio_orm)

        self.assertIsInstance(res, PortfolioWorkflowInput)
        self.assertEqual(len(res.portfolio.holdings), 1)
        self.assertEqual(res.portfolio.holdings[0].ticker, "RELIANCE")
        self.assertIsNone(res.optimization_input)

    def test_one_holding_portfolio_analysis_input(self):
        portfolio_orm = Portfolio.objects.create(user=self.user, name="Single Holding")
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=self._mock_historical_data
        )
        res = builder.build_workflow_input(portfolio_orm, include_optimization=False)

        self.assertIsInstance(res, PortfolioWorkflowInput)
        self.assertIsNone(res.optimization_input)

    def test_multi_holding_optimization_input(self):
        portfolio_orm = Portfolio.objects.create(user=self.user, name="Multi Holding")
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=self._mock_historical_data
        )
        res = builder.build_workflow_input(
            portfolio_orm,
            include_optimization=True,
            risk_free_rate=0.03,
            min_weight=0.1,
            max_weight=0.9,
        )

        self.assertIsInstance(res, PortfolioWorkflowInput)
        self.assertIsNotNone(res.optimization_input)
        self.assertIsInstance(res.optimization_input, OptimizationInput)
        self.assertEqual(res.optimization_input.tickers, ["RELIANCE", "TCS"])
        self.assertEqual(res.optimization_input.risk_free_rate, 0.03)
        self.assertEqual(res.optimization_input.min_weight, 0.1)
        self.assertEqual(res.optimization_input.max_weight, 0.9)

    def test_ticker_normalization_and_deterministic_order(self):
        portfolio_orm = Portfolio.objects.create(user=self.user, name="Order Test")
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="tcs",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="reliance",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=self._mock_historical_data
        )
        opt_input = builder.build_optimization_input(portfolio_orm)

        self.assertEqual(opt_input.tickers, ["RELIANCE", "TCS"])

    def test_historical_data_forwarding(self):
        calls = []

        def tracking_fetcher(
            ticker: str, to_date: str, from_date: str | None = None, market: str = "IN"
        ):
            calls.append((ticker, to_date, from_date, market))
            return {"candles": [{"close": 100.0}, {"close": 102.0}, {"close": 104.0}]}

        portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Forwarding Test"
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=tracking_fetcher)
        builder.build_optimization_input(
            portfolio_orm,
            to_date="2026-09-01",
            from_date="2026-01-01",
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], ("RELIANCE", "2026-09-01", "2026-01-01", "IN"))
        self.assertEqual(calls[1], ("TCS", "2026-09-01", "2026-01-01", "IN"))

    def test_missing_historical_data(self):
        def missing_fetcher(
            ticker: str, to_date: str, from_date: str | None = None, market: str = "IN"
        ):
            return {"ticker": ticker, "candles": []}

        portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Missing Data Test"
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=missing_fetcher)
        with self.assertRaises(ValueError) as ctx:
            builder.build_optimization_input(portfolio_orm)
        self.assertIn("contains no candles", str(ctx.exception))

    def test_insufficient_history(self):
        def short_fetcher(
            ticker: str, to_date: str, from_date: str | None = None, market: str = "IN"
        ):
            return {"candles": [{"close": 100.0}, {"close": 102.0}]}  # only 2 observations

        portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Short Data Test"
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=short_fetcher)
        with self.assertRaises(ValueError) as ctx:
            builder.build_optimization_input(portfolio_orm)
        self.assertIn(
            "At least three historical prices per asset are required", str(ctx.exception)
        )

    def test_fewer_than_two_assets(self):
        portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Single Asset Test"
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=self._mock_historical_data
        )
        with self.assertRaises(ValueError) as ctx:
            builder.build_optimization_input(portfolio_orm)
        self.assertIn(
            "Optimization requires at least two unique assets", str(ctx.exception)
        )

    def test_mismatched_historical_series_alignment(self):
        def mismatched_fetcher(
            ticker: str, to_date: str, from_date: str | None = None, market: str = "IN"
        ):
            if ticker == "RELIANCE":
                return {
                    "candles": [
                        {"close": p} for p in [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
                    ]
                }
            return {
                "candles": [{"close": p} for p in [200.0, 202.0, 204.0, 206.0]]
            }

        portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Alignment Test"
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=mismatched_fetcher
        )
        opt_input = builder.build_optimization_input(portfolio_orm)

        self.assertEqual(len(opt_input.historical_prices["RELIANCE"]), 4)
        self.assertEqual(len(opt_input.historical_prices["TCS"]), 4)
        self.assertEqual(
            opt_input.historical_prices["RELIANCE"], [102.0, 103.0, 104.0, 105.0]
        )
        self.assertEqual(
            opt_input.historical_prices["TCS"], [200.0, 202.0, 204.0, 206.0]
        )

    def test_invalid_non_positive_prices(self):
        def negative_price_fetcher(
            ticker: str, to_date: str, from_date: str | None = None, market: str = "IN"
        ):
            return {"candles": [{"close": 100.0}, {"close": -10.0}, {"close": 105.0}]}

        portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Negative Price Test"
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=negative_price_fetcher
        )
        with self.assertRaises(ValueError) as ctx:
            builder.build_optimization_input(portfolio_orm)
        self.assertIn("contains invalid or non-positive price", str(ctx.exception))

    def test_preservation_of_risk_free_min_max_parameters(self):
        portfolio_orm = Portfolio.objects.create(user=self.user, name="Params Test")
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("3400"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=self._mock_historical_data
        )
        opt_input = builder.build_optimization_input(
            portfolio_orm,
            risk_free_rate=0.05,
            min_weight=0.15,
            max_weight=0.85,
        )

        self.assertEqual(opt_input.risk_free_rate, 0.05)
        self.assertEqual(opt_input.min_weight, 0.15)
        self.assertEqual(opt_input.max_weight, 0.85)

    def test_mixed_markets_validation(self):
        portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Mixed Markets Test"
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("1200"),
        )
        Holding.objects.create(
            portfolio=portfolio_orm,
            ticker="AAPL",
            market="US",
            quantity=Decimal("5"),
            average_price=Decimal("180"),
        )
        builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=self._mock_historical_data
        )
        with self.assertRaises(ValueError) as ctx:
            builder.build_optimization_input(portfolio_orm)
        self.assertIn(
            "across mixed markets/currencies", str(ctx.exception)
        )


class PortfolioWorkflowInputBuilderHistoricalPricesTestCase(TestCase):
    """Test suite for historical price fetching and sharing in PortfolioWorkflowInputBuilder."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="hist_user",
            email="hist@example.com",
            password="password123",
        )
        self.portfolio_orm = Portfolio.objects.create(
            user=self.user, name="History Test Portfolio"
        )
        Holding.objects.create(
            portfolio=self.portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("3000"),
        )
        Holding.objects.create(
            portfolio=self.portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("2500"),
        )

    def test_history_fetched_for_analysis_only_request(self):
        calls = []

        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            calls.append(ticker)
            return {"candles": [{"close": 100.0}, {"close": 102.0}, {"close": 105.0}]}

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        workflow_input = builder.build_workflow_input(
            self.portfolio_orm,
            include_optimization=False,
        )

        self.assertIsNone(workflow_input.optimization_input)
        self.assertIsNotNone(workflow_input.historical_prices)
        self.assertIn("RELIANCE", workflow_input.historical_prices)
        self.assertIn("TCS", workflow_input.historical_prices)

        # Deterministic ordering check (RELIANCE, TCS sorted alphabetically)
        tickers_in_dict = list(workflow_input.historical_prices.keys())
        self.assertEqual(tickers_in_dict, ["RELIANCE", "TCS"])

    def test_history_reused_for_optimization_request_without_duplicates(self):
        calls = []

        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            calls.append(ticker)
            return {"candles": [{"close": 100.0}, {"close": 102.0}, {"close": 105.0}]}

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        workflow_input = builder.build_workflow_input(
            self.portfolio_orm,
            include_optimization=True,
        )

        self.assertIsNotNone(workflow_input.optimization_input)
        self.assertIsNotNone(workflow_input.historical_prices)
        self.assertEqual(
            workflow_input.historical_prices,
            workflow_input.optimization_input.historical_prices,
        )
        # Should call mock_fetcher exactly twice (once per unique holding, RELIANCE & TCS)
        self.assertEqual(len(calls), 2)
        self.assertEqual(sorted(calls), ["RELIANCE", "TCS"])


class PortfolioWorkflowInputBuilderDateAwareCandlesTestCase(TestCase):
    """Test suite for date-aware historical candle fetching and alignment in PortfolioWorkflowInputBuilder."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="date_aware_user",
            email="date_aware@example.com",
            password="password123",
        )
        self.portfolio_orm = Portfolio.objects.create(
            user=self.user, name="Date Aware Portfolio"
        )
        Holding.objects.create(
            portfolio=self.portfolio_orm,
            ticker="TCS",
            market="IN",
            quantity=Decimal("10"),
            average_price=Decimal("3000"),
        )
        Holding.objects.create(
            portfolio=self.portfolio_orm,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("5"),
            average_price=Decimal("2500"),
        )

    def test_timestamp_extraction_and_iso_normalization(self):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            return {
                "candles": [
                    {"timestamp": "2025-01-02T09:15:00+05:30", "close": 100.0},
                    {"timestamp": "2025-01-03 15:30:00", "close": 102.0},
                    {"timestamp": "2025-01-06", "close": 105.0},
                ]
            }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        candles = builder.fetch_portfolio_historical_candles(self.portfolio_orm)

        self.assertIn("RELIANCE", candles)
        self.assertIn("TCS", candles)
        self.assertEqual(
            list(candles["RELIANCE"].keys()),
            ["2025-01-02", "2025-01-03", "2025-01-06"],
        )

    def test_deterministic_ordering(self):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            # Return out-of-order dates
            return {
                "candles": [
                    {"timestamp": "2025-01-06", "close": 105.0},
                    {"timestamp": "2025-01-02", "close": 100.0},
                    {"timestamp": "2025-01-03", "close": 102.0},
                ]
            }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        candles = builder.fetch_portfolio_historical_candles(self.portfolio_orm)

        # Outer dict tickers sorted alphabetically: RELIANCE before TCS
        self.assertEqual(list(candles.keys()), ["RELIANCE", "TCS"])
        # Inner dict dates sorted chronologically
        self.assertEqual(
            list(candles["RELIANCE"].keys()),
            ["2025-01-02", "2025-01-03", "2025-01-06"],
        )

    def test_duplicate_date_handling(self):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            return {
                "candles": [
                    {"timestamp": "2025-01-02", "close": 100.0},
                    {"timestamp": "2025-01-02", "close": 101.0},
                ]
            }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        with self.assertRaises(ValueError) as ctx:
            builder.fetch_portfolio_historical_candles(self.portfolio_orm)
        self.assertIn("Duplicate date observation", str(ctx.exception))

    def test_date_filtering(self):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            return {
                "candles": [
                    {"timestamp": "2025-01-01", "close": 98.0},
                    {"timestamp": "2025-01-02", "close": 100.0},
                    {"timestamp": "2025-01-03", "close": 102.0},
                    {"timestamp": "2025-01-06", "close": 105.0},
                    {"timestamp": "2025-01-07", "close": 107.0},
                ]
            }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        candles = builder.fetch_portfolio_historical_candles(
            self.portfolio_orm,
            from_date="2025-01-02",
            to_date="2025-01-06",
        )

        dates = list(candles["RELIANCE"].keys())
        self.assertEqual(dates, ["2025-01-02", "2025-01-03", "2025-01-06"])

    def test_multi_asset_intersection_and_trading_calendars(self):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            if ticker == "RELIANCE":
                return {
                    "candles": [
                        {"timestamp": "2025-01-02", "close": 100.0},
                        {"timestamp": "2025-01-03", "close": 102.0},
                        {"timestamp": "2025-01-06", "close": 105.0},
                    ]
                }
            else:  # TCS (holiday on Jan 3, has Jan 7 instead)
                return {
                    "candles": [
                        {"timestamp": "2025-01-02", "close": 200.0},
                        {"timestamp": "2025-01-06", "close": 205.0},
                        {"timestamp": "2025-01-07", "close": 207.0},
                    ]
                }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        candles = builder.fetch_portfolio_historical_candles(self.portfolio_orm)

        # Common intersection dates are only Jan 2 and Jan 6
        self.assertEqual(list(candles["RELIANCE"].keys()), ["2025-01-02", "2025-01-06"])
        self.assertEqual(list(candles["TCS"].keys()), ["2025-01-02", "2025-01-06"])

        # No synthetic values or extra dates created
        self.assertEqual(candles["RELIANCE"]["2025-01-02"], 100.0)
        self.assertEqual(candles["TCS"]["2025-01-02"], 200.0)
        self.assertEqual(candles["RELIANCE"]["2025-01-06"], 105.0)
        self.assertEqual(candles["TCS"]["2025-01-06"], 205.0)

    def test_invalid_timestamp(self):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            return {
                "candles": [
                    {"timestamp": "INVALID-DATE", "close": 100.0},
                ]
            }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        with self.assertRaises(ValueError) as ctx:
            builder.fetch_portfolio_historical_candles(self.portfolio_orm)
        self.assertIn("Invalid date format", str(ctx.exception))

    def test_invalid_price(self):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            return {
                "candles": [
                    {"timestamp": "2025-01-02", "close": -10.0},
                ]
            }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        with self.assertRaises(ValueError) as ctx:
            builder.fetch_portfolio_historical_candles(self.portfolio_orm)
        self.assertIn("invalid or non-positive price", str(ctx.exception))

    def test_historical_api_argument_forwarding(self):
        forwarded_args = []

        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            forwarded_args.append({
                "ticker": ticker,
                "to_date": to_date,
                "from_date": from_date,
                "market": market,
            })
            return {
                "candles": [
                    {"timestamp": "2025-01-02", "close": 100.0},
                ]
            }

        builder = PortfolioWorkflowInputBuilder(historical_data_fetcher=mock_fetcher)
        builder.fetch_portfolio_historical_candles(
            self.portfolio_orm,
            from_date="2025-01-01",
            to_date="2025-01-31",
        )

        self.assertEqual(len(forwarded_args), 2)
        tickers_forwarded = [arg["ticker"] for arg in forwarded_args]
        self.assertEqual(sorted(tickers_forwarded), ["RELIANCE", "TCS"])
        for arg in forwarded_args:
            self.assertEqual(arg["from_date"], "2025-01-01")
            self.assertEqual(arg["to_date"], "2025-01-31")
            self.assertEqual(arg["market"], "IN")


from apps.portfolio.backtest_builder import PortfolioBacktestInputBuilder


class PortfolioBacktestInputBuilderTestCase(TestCase):
    """Test suite for PortfolioBacktestInputBuilder."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="builder_user",
            email="builder_user@example.com",
            password="securepassword123",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Backtest Test Portfolio",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_A",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("100.0"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_B",
            market="IN",
            quantity=Decimal("30.0"),
            average_price=Decimal("50.0"),
        )

        # Generate 10 consecutive date strings for testing
        self.dates = [f"2025-01-{i:02d}" for i in range(1, 11)]

    def _make_mock_fetcher(self, prices_a=None, prices_b=None, benchmark_prices=None):
        def mock_fetcher(ticker, to_date, from_date=None, market="IN"):
            norm_ticker = ticker.upper()
            if norm_ticker == "ASSET_A":
                p_list = prices_a or [100.0 + i for i in range(len(self.dates))]
                candles = [{"timestamp": d, "close": p} for d, p in zip(self.dates, p_list)]
                return {"candles": candles}
            elif norm_ticker == "ASSET_B":
                p_list = prices_b or [50.0 + i * 0.5 for i in range(len(self.dates))]
                candles = [{"timestamp": d, "close": p} for d, p in zip(self.dates, p_list)]
                return {"candles": candles}
            elif "NSE_INDEX" in norm_ticker or norm_ticker in ("NIFTY 50", "BENCHMARK"):
                p_list = benchmark_prices or [200.0 + i * 2 for i in range(len(self.dates))]
                candles = [{"timestamp": d, "close": p} for d, p in zip(self.dates, p_list)]
                return {"candles": candles}
            return {"candles": []}

        return mock_fetcher

    def test_django_portfolio_to_backtest_input(self):
        """Test converting Django Portfolio to PortfolioBacktestInput."""
        mock_fetcher = self._make_mock_fetcher()
        builder = PortfolioBacktestInputBuilder(historical_data_fetcher=mock_fetcher)

        backtest_input = builder.build_backtest_input(
            portfolio=self.portfolio,
            in_sample_window_days=5,
            out_of_sample_step_days=2,
            initial_capital=50000.0,
        )

        self.assertEqual(backtest_input.tickers, ["ASSET_A", "ASSET_B"])
        self.assertEqual(backtest_input.initial_capital, 50000.0)
        self.assertEqual(backtest_input.in_sample_window_days, 5)
        self.assertEqual(backtest_input.out_of_sample_step_days, 2)

    def test_actual_initial_market_value_weights_unequal(self):
        """Verify actual initial market-value weights are calculated without equal-weight fallback."""
        # ASSET_A: 10 qty * 100.0 price at t0 = 1000.0
        # ASSET_B: 30 qty * 50.0 price at t0 = 1500.0
        # Total value = 2500.0 -> Weight A = 1000/2500 = 0.40, Weight B = 1500/2500 = 0.60
        mock_fetcher = self._make_mock_fetcher()
        builder = PortfolioBacktestInputBuilder(historical_data_fetcher=mock_fetcher)

        backtest_input = builder.build_backtest_input(
            portfolio=self.portfolio,
            in_sample_window_days=5,
            out_of_sample_step_days=2,
        )

        self.assertIsNotNone(backtest_input.initial_weights)
        self.assertAlmostEqual(backtest_input.initial_weights["ASSET_A"], 0.40, places=4)
        self.assertAlmostEqual(backtest_input.initial_weights["ASSET_B"], 0.60, places=4)
        self.assertAlmostEqual(sum(backtest_input.initial_weights.values()), 1.0, places=6)
        self.assertNotEqual(backtest_input.initial_weights["ASSET_A"], 0.50)

    def test_same_market_validation_and_mixed_market_rejection(self):
        """Verify mixed market portfolios are rejected."""
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("5.0"),
            average_price=Decimal("150.0"),
        )
        mock_fetcher = self._make_mock_fetcher()
        builder = PortfolioBacktestInputBuilder(historical_data_fetcher=mock_fetcher)

        with self.assertRaises(ValueError) as ctx:
            builder.build_backtest_input(
                portfolio=self.portfolio,
                in_sample_window_days=3,
                out_of_sample_step_days=1,
            )
        self.assertIn("mixed markets", str(ctx.exception))

    def test_insufficient_history_rejection(self):
        """Verify explicit error when common date history is less than in_sample + OOS step."""
        mock_fetcher = self._make_mock_fetcher()
        builder = PortfolioBacktestInputBuilder(historical_data_fetcher=mock_fetcher)

        # 10 dates available, requesting in_sample=8 + OOS=5 -> required=13
        with self.assertRaises(ValueError) as ctx:
            builder.build_backtest_input(
                portfolio=self.portfolio,
                in_sample_window_days=8,
                out_of_sample_step_days=5,
            )
        self.assertIn("Insufficient historical observations", str(ctx.exception))

    def test_benchmark_data_construction_and_ticker_preservation(self):
        """Verify benchmark prices construction and benchmark ticker preservation."""
        mock_fetcher = self._make_mock_fetcher()
        builder = PortfolioBacktestInputBuilder(historical_data_fetcher=mock_fetcher)

        backtest_input = builder.build_backtest_input(
            portfolio=self.portfolio,
            benchmark_ticker="NIFTY 50",
            in_sample_window_days=5,
            out_of_sample_step_days=2,
        )

        self.assertEqual(backtest_input.benchmark_ticker, "NIFTY 50")
        self.assertIsNotNone(backtest_input.benchmark_prices)
        self.assertEqual(len(backtest_input.benchmark_prices), len(self.dates))

    def test_benchmark_insufficient_overlapping_dates_rejection(self):
        """Verify rejection when benchmark prices have fewer than 3 overlapping dates."""
        def sparse_bmark_fetcher(ticker, to_date, from_date=None, market="IN"):
            if "NSE_INDEX" in ticker.upper() or ticker in ("BENCH_SPARSE",):
                # Only 1 date matches portfolio dates
                return {"candles": [{"timestamp": self.dates[0], "close": 200.0}]}
            return self._make_mock_fetcher()(ticker, to_date, from_date, market)

        builder = PortfolioBacktestInputBuilder(historical_data_fetcher=sparse_bmark_fetcher)

        with self.assertRaises(ValueError) as ctx:
            builder.build_backtest_input(
                portfolio=self.portfolio,
                benchmark_ticker="BENCH_SPARSE",
                in_sample_window_days=5,
                out_of_sample_step_days=2,
            )
        self.assertIn("insufficient overlapping observations", str(ctx.exception))

    def test_preservation_of_backtest_configuration(self):
        """Verify all backtest parameters are passed through correctly."""
        mock_fetcher = self._make_mock_fetcher()
        builder = PortfolioBacktestInputBuilder(historical_data_fetcher=mock_fetcher)

        backtest_input = builder.build_backtest_input(
            portfolio=self.portfolio,
            in_sample_window_days=4,
            out_of_sample_step_days=2,
            transaction_cost_bps=15.0,
            risk_free_rate=0.05,
            min_weight=0.05,
            max_weight=0.60,
            rebalance_frequency="monthly",
        )

        self.assertEqual(backtest_input.in_sample_window_days, 4)
        self.assertEqual(backtest_input.out_of_sample_step_days, 2)
        self.assertEqual(backtest_input.transaction_cost_bps, 15.0)
        self.assertEqual(backtest_input.risk_free_rate, 0.05)
        self.assertEqual(backtest_input.min_weight, 0.05)
        self.assertEqual(backtest_input.max_weight, 0.60)
        self.assertEqual(backtest_input.rebalance_frequency, "monthly")


from unittest.mock import patch
from django.urls import reverse


class PortfolioBacktestAPITestCase(TestCase):
    """Test suite for POST /api/v1/portfolio/<portfolio_id>/backtest/ API endpoint."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="api_user1",
            email="api_user1@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="api_user2",
            email="api_user2@example.com",
            password="securepassword456",
        )

        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="API Test Portfolio",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_A",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("100.0"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_B",
            market="IN",
            quantity=Decimal("30.0"),
            average_price=Decimal("50.0"),
        )

        self.dates = [f"2025-01-{i:02d}" for i in range(1, 11)]
        self.client = APIClient()

    def _mock_get_historical_data(self, ticker, to_date, from_date=None, market="IN"):
        norm_ticker = ticker.upper()
        if norm_ticker == "ASSET_A":
            candles = [{"timestamp": d, "close": 100.0 + i} for i, d in enumerate(self.dates)]
            return {"candles": candles}
        elif norm_ticker == "ASSET_B":
            candles = [{"timestamp": d, "close": 50.0 + i * 0.5} for i, d in enumerate(self.dates)]
            return {"candles": candles}
        elif "NSE_INDEX" in norm_ticker or norm_ticker in ("NIFTY 50", "BENCHMARK"):
            candles = [{"timestamp": d, "close": 200.0 + i * 2} for i, d in enumerate(self.dates)]
            return {"candles": candles}
        return {"candles": []}

    def test_unauthenticated_user_rejected(self):
        """Verify unauthenticated requests are rejected with 401 Unauthorized."""
        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_another_user_portfolio_returns_404(self):
        """Verify accessing another user's portfolio returns 404 Not Found."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_authenticated_owner_backtest_success(self, mock_fetch):
        """Verify authenticated owner gets complete structured backtest and risk evaluation."""
        mock_fetch.side_effect = self._mock_get_historical_data
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        payload = {
            "benchmark_ticker": "NIFTY 50",
            "initial_capital": 50000.0,
            "in_sample_window_days": 5,
            "out_of_sample_step_days": 2,
            "transaction_cost_bps": 10.0,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["portfolio_id"], str(self.portfolio.id))
        self.assertEqual(data["benchmark_ticker"], "NIFTY 50")
        self.assertEqual(data["initial_capital"], 50000.0)
        self.assertIsNotNone(data["strategy_metrics"])
        self.assertIsNotNone(data["buy_and_hold_metrics"])
        self.assertIsNotNone(data["benchmark_metrics"])
        self.assertIsNotNone(data["relative_metrics"])
        self.assertIsNotNone(data["final_portfolio_value"])
        self.assertIsNotNone(data["total_transaction_costs"])
        self.assertIsInstance(data["rebalance_events"], list)
        self.assertIsInstance(data["equity_curve"], list)

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_optional_benchmark_omitted(self, mock_fetch):
        """Verify backtest succeeds when benchmark is omitted, returning None for benchmark metrics."""
        mock_fetch.side_effect = self._mock_get_historical_data
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        payload = {
            "in_sample_window_days": 5,
            "out_of_sample_step_days": 2,
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIsNone(data["benchmark_ticker"])
        self.assertIsNone(data["benchmark_metrics"])
        self.assertIsNone(data["relative_metrics"])
        self.assertIsNotNone(data["strategy_metrics"])
        self.assertIsNotNone(data["buy_and_hold_metrics"])

    def test_request_validation_failure(self):
        """Verify serializer rejects invalid parameters such as min_weight > max_weight."""
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        payload = {
            "min_weight": 0.8,
            "max_weight": 0.2,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("min_weight", response.json())

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_domain_backtest_error_handling(self, mock_fetch):
        """Verify domain errors (e.g. mixed market holdings) return 400 Bad Request with error detail."""
        mock_fetch.side_effect = self._mock_get_historical_data
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("5.0"),
            average_price=Decimal("150.0"),
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        payload = {
            "in_sample_window_days": 5,
            "out_of_sample_step_days": 2,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())
        self.assertIn("mixed markets", response.json()["error"])


class PortfolioRiskViewTestCase(TestCase):
    """Test suite for GET /api/v1/portfolio/<portfolio_id>/risk/ endpoint."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="riskinvestor1",
            email="riskinvestor1@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="riskinvestor2",
            email="riskinvestor2@example.com",
            password="securepassword456",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Risk Test Portfolio",
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_A",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("100.0"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_B",
            market="IN",
            quantity=Decimal("30.0"),
            average_price=Decimal("50.0"),
        )
        self.dates = [f"2025-01-{i:02d}" for i in range(1, 15)]
        self.client = APIClient()

    def _mock_get_historical_data(self, ticker, to_date, from_date=None, market="IN"):
        norm_ticker = ticker.upper()
        if norm_ticker == "ASSET_A":
            # Include fluctuations so max_drawdown > 0 and calmar_ratio is calculated
            candles = [{"timestamp": d, "close": 100.0 + (5.0 if i % 2 == 0 else -3.0) + i * 1.0} for i, d in enumerate(self.dates)]
            return {"candles": candles}
        elif norm_ticker == "ASSET_B":
            candles = [{"timestamp": d, "close": 50.0 + (2.0 if i % 2 == 0 else -1.0) + i * 0.5} for i, d in enumerate(self.dates)]
            return {"candles": candles}
        return {"candles": []}

    def test_unauthenticated_request_rejected(self):
        """1. Unauthenticated request rejected with 401 Unauthorized."""
        url = reverse("portfolio-risk", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_another_user_portfolio_rejected(self):
        """2. Accessing another user's portfolio rejected with 404 Not Found."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse("portfolio-risk", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_authenticated_owner_can_retrieve_all_12_risk_fields(self, mock_fetch):
        """3. Authenticated owner can retrieve risk with all 12 authoritative fields."""
        mock_fetch.side_effect = self._mock_get_historical_data
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-risk", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["portfolio_id"], str(self.portfolio.id))
        self.assertEqual(data["portfolio_name"], "Risk Test Portfolio")
        self.assertIn("risk_metrics", data)

        required_metrics = [
            "total_period_return",
            "annualized_return",
            "cagr",
            "volatility",
            "downside_volatility",
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "max_drawdown",
            "max_drawdown_duration_days",
            "var_95_historical",
            "cvar_95_historical",
        ]

        for metric in required_metrics:
            self.assertIn(metric, data, f"Missing top-level metric: {metric}")
            self.assertIn(metric, data["risk_metrics"], f"Missing risk_metrics field: {metric}")
            self.assertIsNotNone(data[metric], f"Metric {metric} should not be None")

    def test_empty_portfolio_returns_400(self):
        """4. Portfolio with no holdings returns 400 Bad Request."""
        empty_portfolio = Portfolio.objects.create(
            user=self.user,
            name="Empty Portfolio",
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-risk", kwargs={"portfolio_id": empty_portfolio.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())
        self.assertIn("no holdings", response.json()["error"].lower())

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_mixed_market_portfolio_returns_400(self, mock_fetch):
        """5. Mixed-market portfolio returns 400 Bad Request."""
        mock_fetch.side_effect = self._mock_get_historical_data
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("5.0"),
            average_price=Decimal("150.0"),
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-risk", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())
        self.assertIn("mixed markets", response.json()["error"])

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_insufficient_historical_data_returns_400(self, mock_fetch):
        """6. Insufficient historical price data returns 400 Bad Request."""
        # Return only 1 candle (insufficient for covariance/variance estimation)
        mock_fetch.return_value = {"candles": [{"timestamp": "2025-01-01", "close": 100.0}]}
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-risk", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())


class PortfolioOptimizationViewTestCase(TestCase):
    """Test suite for POST /api/v1/portfolio/<portfolio_id>/optimize/ endpoint."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="optinvestor1",
            email="optinvestor1@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="optinvestor2",
            email="optinvestor2@example.com",
            password="securepassword456",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Optimization Test Portfolio",
        )
        self.holding_a = Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_A",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("100.0"),
        )
        self.holding_b = Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_B",
            market="IN",
            quantity=Decimal("30.0"),
            average_price=Decimal("50.0"),
        )
        self.dates = [f"2025-01-{i:02d}" for i in range(1, 20)]
        self.client = APIClient()

    def _mock_get_historical_data(self, ticker, to_date, from_date=None, market="IN"):
        norm_ticker = ticker.upper()
        if norm_ticker == "ASSET_A":
            candles = [
                {"timestamp": d, "close": 100.0 + (5.0 if i % 2 == 0 else -3.0) + i * 1.5}
                for i, d in enumerate(self.dates)
            ]
            return {"candles": candles}
        elif norm_ticker == "ASSET_B":
            candles = [
                {"timestamp": d, "close": 50.0 + (2.0 if i % 2 == 0 else -1.0) + i * 0.8}
                for i, d in enumerate(self.dates)
            ]
            return {"candles": candles}
        return {"candles": []}

    def test_unauthenticated_request_rejected(self):
        """1. Unauthenticated request rejected with 401 Unauthorized."""
        url = reverse("portfolio-optimize", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_another_user_portfolio_rejected(self):
        """2. Accessing another user's portfolio rejected with 404 Not Found."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse("portfolio-optimize", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_valid_owner_optimization_success(self, mock_fetch):
        """3. Valid owner receives 200 OK with authoritative weights, metrics, and comparisons."""
        mock_fetch.side_effect = self._mock_get_historical_data
        self.client.force_authenticate(user=self.user)

        payload = {
            "objective": "max_sharpe",
            "risk_free_rate": 0.05,
            "min_weight": 0.10,
            "max_weight": 0.90,
        }

        url = reverse("portfolio-optimize", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Contract assertions
        self.assertEqual(data["portfolio_id"], str(self.portfolio.id))
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["objective"], "max_sharpe")

        # Weights assertions
        opt_weights = data["optimized_weights"]
        self.assertIn("ASSET_A", opt_weights)
        self.assertIn("ASSET_B", opt_weights)
        self.assertAlmostEqual(sum(opt_weights.values()), 1.0, places=3)
        self.assertGreaterEqual(opt_weights["ASSET_A"], 0.10 - 1e-4)
        self.assertLessEqual(opt_weights["ASSET_A"], 0.90 + 1e-4)
        self.assertGreaterEqual(opt_weights["ASSET_B"], 0.10 - 1e-4)
        self.assertLessEqual(opt_weights["ASSET_B"], 0.90 + 1e-4)

        # Current weights assertions
        curr_weights = data["current_weights"]
        self.assertIn("ASSET_A", curr_weights)
        self.assertIn("ASSET_B", curr_weights)
        self.assertAlmostEqual(sum(curr_weights.values()), 1.0, places=3)

        # Metrics assertions
        curr_m = data["current_metrics"]
        opt_m = data["optimized_metrics"]
        for key in ["expected_return", "volatility", "sharpe_ratio"]:
            self.assertIn(key, curr_m)
            self.assertIn(key, opt_m)
            self.assertIsInstance(curr_m[key], (int, float))
            self.assertIsInstance(opt_m[key], (int, float))

        # Comparisons assertions
        comparisons = data["weight_comparisons"]
        self.assertEqual(len(comparisons), 2)
        for comp in comparisons:
            self.assertIn("ticker", comp)
            self.assertIn("current_weight", comp)
            self.assertIn("target_weight", comp)
            self.assertIn("weight_difference", comp)
            self.assertIn("direction", comp)

        # Holding mutation assertion - ensure no holdings were modified
        self.holding_a.refresh_from_db()
        self.holding_b.refresh_from_db()
        self.assertEqual(self.holding_a.quantity, Decimal("10.0"))
        self.assertEqual(self.holding_a.average_price, Decimal("100.0"))
        self.assertEqual(self.holding_b.quantity, Decimal("30.0"))
        self.assertEqual(self.holding_b.average_price, Decimal("50.0"))

    def test_empty_portfolio_returns_400(self):
        """4. Portfolio with no holdings returns 400 Bad Request."""
        empty_portfolio = Portfolio.objects.create(
            user=self.user,
            name="Empty Optimization Portfolio",
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-optimize", kwargs={"portfolio_id": empty_portfolio.id})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_single_asset_portfolio_returns_400(self):
        """5. Portfolio with only one asset returns 400 Bad Request."""
        single_portfolio = Portfolio.objects.create(
            user=self.user,
            name="Single Asset Portfolio",
        )
        Holding.objects.create(
            portfolio=single_portfolio,
            ticker="ONLY_ONE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("100.0"),
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-optimize", kwargs={"portfolio_id": single_portfolio.id})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())
        self.assertIn("at least two", response.json()["error"].lower())

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_mixed_market_portfolio_returns_400(self, mock_fetch):
        """6. Mixed-market portfolio returns 400 Bad Request."""
        mock_fetch.side_effect = self._mock_get_historical_data
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("5.0"),
            average_price=Decimal("150.0"),
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-optimize", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())
        self.assertIn("mixed markets", response.json()["error"].lower())

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_infeasible_bounds_returns_400(self, mock_fetch):
        """7. Infeasible bounds (min_weight * N > 1.0) returns 400 Bad Request."""
        mock_fetch.side_effect = self._mock_get_historical_data
        self.client.force_authenticate(user=self.user)

        # 2 assets with min_weight=0.6 requires sum >= 1.2, which violates sum=1.0
        payload = {
            "min_weight": 0.60,
            "max_weight": 0.90,
        }
        url = reverse("portfolio-optimize", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_invalid_parameters_returns_400(self):
        """8. Invalid parameters (min_weight > max_weight, invalid objective) return 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-optimize", kwargs={"portfolio_id": self.portfolio.id})

        # min_weight > max_weight
        res1 = self.client.post(url, {"min_weight": 0.8, "max_weight": 0.2}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)

        # Unsupported objective
        res2 = self.client.post(url, {"objective": "min_variance"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_insufficient_historical_data_returns_400(self, mock_fetch):
        """9. Insufficient historical price data returns 400 Bad Request."""
        mock_fetch.return_value = {"candles": [{"timestamp": "2025-01-01", "close": 100.0}]}
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-optimize", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())


class PortfolioBacktestAPITestCase(TestCase):
    """Test suite for POST /api/v1/portfolio/<portfolio_id>/backtest/ endpoint."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="backtest_user1",
            email="backtest_user1@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="backtest_user2",
            email="backtest_user2@example.com",
            password="securepassword456",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Backtest Test Portfolio",
        )
        self.holding_a = Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_A",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("100.0"),
        )
        self.holding_b = Holding.objects.create(
            portfolio=self.portfolio,
            ticker="ASSET_B",
            market="IN",
            quantity=Decimal("30.0"),
            average_price=Decimal("50.0"),
        )
        self.dates = [f"2025-01-{i:02d}" for i in range(1, 20)]
        self.client = APIClient()

    def _mock_get_historical_data(self, ticker, to_date, from_date=None, market="IN"):
        norm_ticker = ticker.upper()
        if norm_ticker == "ASSET_A":
            candles = [
                {"timestamp": d, "close": 100.0 + (5.0 if i % 2 == 0 else -3.0) + i * 1.5}
                for i, d in enumerate(self.dates)
            ]
            return {"candles": candles}
        elif norm_ticker == "ASSET_B":
            candles = [
                {"timestamp": d, "close": 50.0 + (2.0 if i % 2 == 0 else -1.0) + i * 0.8}
                for i, d in enumerate(self.dates)
            ]
            return {"candles": candles}
        elif norm_ticker in ["^NSEI", "NSE_INDEX|NIFTY 50", "NIFTY 50", "BENCHMARK"]:
            candles = [
                {"timestamp": d, "close": 1000.0 + i * 10.0 + (2.0 if i % 2 == 0 else -2.0)}
                for i, d in enumerate(self.dates)
            ]
            return {"candles": candles}
        return {"candles": []}

    def test_unauthenticated_request_rejected(self):
        """1. Unauthenticated request rejected with 401 Unauthorized."""
        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unowned_portfolio_rejected(self):
        """2. Accessing another user's portfolio rejected with 404 Not Found."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_portfolio_returns_400(self):
        """3. Portfolio with no holdings returns 400 Bad Request."""
        empty_portfolio = Portfolio.objects.create(
            user=self.user,
            name="Empty Backtest Portfolio",
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": empty_portfolio.id})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_single_asset_portfolio_returns_400(self):
        """4. Portfolio with only one asset returns 400 Bad Request."""
        single_portfolio = Portfolio.objects.create(
            user=self.user,
            name="Single Asset Backtest Portfolio",
        )
        Holding.objects.create(
            portfolio=single_portfolio,
            ticker="ONLY_ONE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("100.0"),
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": single_portfolio.id})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())
        self.assertIn("at least two", response.json()["error"].lower())

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_mixed_market_portfolio_returns_400(self, mock_fetch):
        """5. Mixed-market portfolio returns 400 Bad Request."""
        mock_fetch.side_effect = self._mock_get_historical_data
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="AAPL",
            market="US",
            quantity=Decimal("5.0"),
            average_price=Decimal("150.0"),
        )
        self.client.force_authenticate(user=self.user)

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())
        self.assertIn("mixed markets", response.json()["error"].lower())

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_canonical_request_fields_accepted(self, mock_fetch):
        """6. Canonical request fields produce authoritative response with multi-series curves and unchanged holdings."""
        mock_fetch.side_effect = self._mock_get_historical_data
        self.client.force_authenticate(user=self.user)

        payload = {
            "from_date": "2025-01-01",
            "to_date": "2025-01-19",
            "benchmark_ticker": "^NSEI",
            "initial_capital": 100000.0,
            "rebalance_frequency": "periodic",
            "in_sample_window_days": 5,
            "out_of_sample_step_days": 2,
            "transaction_cost_bps": 10.0,
            "risk_free_rate": 0.05,
            "min_weight": 0.0,
            "max_weight": 1.0,
        }

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check response structure
        self.assertEqual(data["portfolio_id"], str(self.portfolio.id))
        self.assertEqual(data["benchmark_ticker"], "^NSEI")
        self.assertEqual(data["initial_capital"], 100000.0)

        # Strategy metrics check
        self.assertIsNotNone(data["strategy_metrics"])
        self.assertIn("total_period_return", data["strategy_metrics"])
        self.assertIn("cagr", data["strategy_metrics"])
        self.assertIn("sharpe_ratio", data["strategy_metrics"])
        self.assertIn("max_drawdown", data["strategy_metrics"])

        # Buy-and-hold metrics check
        self.assertIsNotNone(data["buy_and_hold_metrics"])
        self.assertIn("total_period_return", data["buy_and_hold_metrics"])

        # Benchmark metrics check
        self.assertIsNotNone(data["benchmark_metrics"])
        self.assertIn("total_period_return", data["benchmark_metrics"])

        # Relative metrics check
        self.assertIsNotNone(data["relative_metrics"])
        self.assertIn("excess_cagr", data["relative_metrics"])
        self.assertIn("total_return_difference", data["relative_metrics"])
        self.assertIn("tracking_error", data["relative_metrics"])
        self.assertIn("information_ratio", data["relative_metrics"])

        # Equity curve check
        equity_curve = data["equity_curve"]
        self.assertIsInstance(equity_curve, list)
        self.assertGreater(len(equity_curve), 0)
        first_eq = equity_curve[0]
        self.assertIn("date", first_eq)
        self.assertIn("strategy_value", first_eq)
        self.assertIn("buy_and_hold_value", first_eq)
        self.assertIn("benchmark_value", first_eq)

        # Drawdown curve check
        drawdown_curve = data["drawdown_curve"]
        self.assertIsInstance(drawdown_curve, list)
        self.assertGreater(len(drawdown_curve), 0)
        first_dd = drawdown_curve[0]
        self.assertIn("date", first_dd)
        self.assertIn("strategy_drawdown", first_dd)
        self.assertIn("benchmark_drawdown", first_dd)

        # Non-mutation assertion: Portfolio holdings must remain intact
        self.holding_a.refresh_from_db()
        self.holding_b.refresh_from_db()
        self.assertEqual(self.holding_a.quantity, Decimal("10.0"))
        self.assertEqual(self.holding_a.average_price, Decimal("100.0"))
        self.assertEqual(self.holding_b.quantity, Decimal("30.0"))
        self.assertEqual(self.holding_b.average_price, Decimal("50.0"))

    @patch("apps.ai.services.research_tools.get_historical_data")
    def test_frontend_equivalent_aliases_forwarded_correctly(self, mock_fetch):
        """7. Frontend alias fields (benchmark, in_sample_window, out_of_sample_step, transaction_cost) are resolved."""
        mock_fetch.side_effect = self._mock_get_historical_data
        self.client.force_authenticate(user=self.user)

        payload = {
            "benchmark": "^NSEI",
            "initial_capital": 50000.0,
            "in_sample_window": 5,
            "out_of_sample_step": 2,
            "transaction_cost": 0.0010,  # 10 bps as fraction
        }

        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["benchmark_ticker"], "^NSEI")
        self.assertEqual(data["initial_capital"], 50000.0)
        self.assertIsNotNone(data["equity_curve"])
        self.assertIsNotNone(data["drawdown_curve"])
        self.assertIsNotNone(data["strategy_metrics"])
        self.assertIsNotNone(data["benchmark_metrics"])

    def test_invalid_parameters_rejected(self):
        """8. Invalid min_weight > max_weight rejected with 400 Bad Request."""
        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-backtest", kwargs={"portfolio_id": self.portfolio.id})

        response = self.client.post(url, {"min_weight": 0.8, "max_weight": 0.2}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AlertModelTestCase(TestCase):
    """Test suite for Alert model, ownership invariants, choices, indexes, and serializer."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="alert_user",
            email="alert_user@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="other_alert_user",
            email="other_alert_user@example.com",
            password="securepassword456",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Main Portfolio",
        )
        self.other_portfolio = Portfolio.objects.create(
            user=self.other_user,
            name="Other User Portfolio",
        )

    def test_alert_creation_for_owned_portfolio(self):
        """1. Alert can be created for an owned portfolio."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            severity=AlertSeverity.WARNING,
            title="High Concentration Warning",
            message="Holding RELIANCE exceeds 35% weight.",
            metric_value=Decimal("38.5000"),
            threshold_value=Decimal("35.0000"),
        )
        self.assertIsNotNone(alert.pk)
        self.assertEqual(alert.portfolio, self.portfolio)
        self.assertEqual(alert.user, self.user)

    def test_alert_uuid_primary_key_generated(self):
        """2. UUID primary key is generated correctly."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.DRAWDOWN_BREACH,
            title="Max Drawdown Breach",
            metric_value=Decimal("18.2500"),
            threshold_value=Decimal("15.0000"),
        )
        self.assertIsInstance(alert.id, uuid.UUID)

    def test_default_status_is_active(self):
        """3. Default status is ACTIVE."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.LOSS_THRESHOLD,
            title="Severe Loss Alert",
            metric_value=Decimal("-12.5000"),
            threshold_value=Decimal("-10.0000"),
        )
        self.assertEqual(alert.status, AlertStatus.ACTIVE)
        self.assertEqual(alert.severity, AlertSeverity.WARNING)

    def test_created_at_is_populated(self):
        """4. created_at is automatically populated on save."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.DRAWDOWN_BREACH,
            title="Drawdown Alert",
            metric_value=Decimal("16.0000"),
            threshold_value=Decimal("15.0000"),
        )
        self.assertIsNotNone(alert.created_at)

    def test_acknowledged_at_defaults_to_none(self):
        """5. acknowledged_at defaults to None for active alerts."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Concentration Alert",
            metric_value=Decimal("40.0000"),
            threshold_value=Decimal("30.0000"),
        )
        self.assertIsNone(alert.acknowledged_at)

    def test_valid_alert_types_accepted(self):
        """6. All valid alert types are accepted."""
        for alert_type in [
            AlertType.CONCENTRATION_BREACH,
            AlertType.DRAWDOWN_BREACH,
            AlertType.LOSS_THRESHOLD,
        ]:
            alert = Alert.objects.create(
                portfolio=self.portfolio,
                alert_type=alert_type,
                title=f"Alert for {alert_type}",
                metric_value=Decimal("10.0000"),
                threshold_value=Decimal("5.0000"),
            )
            self.assertEqual(alert.alert_type, alert_type)

    def test_valid_severities_accepted(self):
        """7. All valid severities (info, warning, critical) are accepted."""
        for sev in [AlertSeverity.INFO, AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
            alert = Alert.objects.create(
                portfolio=self.portfolio,
                alert_type=AlertType.CONCENTRATION_BREACH,
                severity=sev,
                title=f"Severity {sev}",
                metric_value=Decimal("10.0000"),
                threshold_value=Decimal("5.0000"),
            )
            self.assertEqual(alert.severity, sev)

    def test_valid_statuses_accepted(self):
        """8. All valid statuses (ACTIVE, ACKNOWLEDGED, RESOLVED) are accepted."""
        for st in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED]:
            alert = Alert.objects.create(
                portfolio=self.portfolio,
                alert_type=AlertType.CONCENTRATION_BREACH,
                status=st,
                title=f"Status {st}",
                metric_value=Decimal("10.0000"),
                threshold_value=Decimal("5.0000"),
            )
            self.assertEqual(alert.status, st)

    def test_alert_linked_to_portfolio_user_automatically(self):
        """9. Alert automatically inherits portfolio.user when user is omitted."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Auto-user test",
            metric_value=Decimal("30.0000"),
            threshold_value=Decimal("25.0000"),
        )
        self.assertEqual(alert.user, self.portfolio.user)

    def test_application_level_validation_rejects_mismatched_user(self):
        """10. Validation rejects mismatched user and portfolio owner."""
        alert = Alert(
            portfolio=self.portfolio,  # owned by self.user
            user=self.other_user,       # mismatched user!
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Mismatched User Alert",
            metric_value=Decimal("30.0000"),
            threshold_value=Decimal("25.0000"),
        )
        with self.assertRaises(ValidationError) as ctx:
            alert.full_clean()
        self.assertIn("user", ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            alert.save()

    def test_portfolio_deletion_cascades_to_alerts(self):
        """11. Portfolio deletion removes associated alerts according to CASCADE."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.DRAWDOWN_BREACH,
            title="To be deleted",
            metric_value=Decimal("20.0000"),
            threshold_value=Decimal("15.0000"),
        )
        alert_id = alert.id
        self.portfolio.delete()
        self.assertFalse(Alert.objects.filter(id=alert_id).exists())

    def test_user_deletion_cascades_to_alerts(self):
        """12. User deletion cascades to alerts without leaving orphaned records."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.LOSS_THRESHOLD,
            title="User to be deleted",
            metric_value=Decimal("-15.0000"),
            threshold_value=Decimal("-10.0000"),
        )
        alert_id = alert.id
        self.user.delete()
        self.assertFalse(Alert.objects.filter(id=alert_id).exists())

    def test_alert_query_filtering_by_portfolio_alert_type_and_created_at(self):
        """13. Alert queryset can efficiently filter by portfolio + alert_type + created_at."""
        alert1 = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Alert 1",
            metric_value=Decimal("32.0000"),
            threshold_value=Decimal("30.0000"),
        )
        alert2 = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.DRAWDOWN_BREACH,
            title="Alert 2",
            metric_value=Decimal("16.0000"),
            threshold_value=Decimal("15.0000"),
        )

        qs = Alert.objects.filter(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            created_at__lte=alert1.created_at,
        )
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, alert1.id)

        status_qs = Alert.objects.filter(
            portfolio=self.portfolio,
            status=AlertStatus.ACTIVE,
        )
        self.assertEqual(status_qs.count(), 2)

    def test_serializer_returns_alert_information_correctly(self):
        """14. Serializer correctly formats alert fields for presentation."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            severity=AlertSeverity.CRITICAL,
            title="Critical Concentration",
            message="TCS exceeds 45% of portfolio.",
            metric_value=Decimal("46.2500"),
            threshold_value=Decimal("35.0000"),
            status=AlertStatus.ACTIVE,
        )
        serializer = AlertSerializer(alert)
        data = serializer.data

        self.assertEqual(data["id"], str(alert.id))
        self.assertEqual(data["portfolio"], self.portfolio.id)
        self.assertEqual(data["user"], self.user.id)
        self.assertEqual(data["alert_type"], "concentration_breach")
        self.assertEqual(data["severity"], "critical")
        self.assertEqual(data["title"], "Critical Concentration")
        self.assertEqual(data["message"], "TCS exceeds 45% of portfolio.")
        self.assertEqual(Decimal(str(data["metric_value"])), Decimal("46.2500"))
        self.assertEqual(Decimal(str(data["threshold_value"])), Decimal("35.0000"))
        self.assertEqual(data["status"], "ACTIVE")
        self.assertIsNone(data["acknowledged_at"])
        self.assertIsNotNone(data["created_at"])

    def test_serializer_does_not_permit_writing_arbitrary_user_ownership(self):
        """15. User cannot write arbitrary user ownership through serializer."""
        self.assertIn("user", AlertSerializer.Meta.read_only_fields)
        self.assertIn("portfolio", AlertSerializer.Meta.read_only_fields)

    def test_serializer_portfolio_ownership_cannot_be_reassigned(self):
        """16. Portfolio ownership cannot be reassigned through serializer."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Initial Alert",
            metric_value=Decimal("30.0000"),
            threshold_value=Decimal("25.0000"),
        )
        serializer = AlertSerializer(
            instance=alert,
            data={"portfolio": str(self.other_portfolio.id), "title": "Updated Title"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        updated_alert = serializer.save()
        self.assertEqual(updated_alert.portfolio, self.portfolio)

    def test_server_controlled_fields_are_read_only(self):
        """17. Server-controlled fields are marked read-only in serializer."""
        for field in ["id", "portfolio", "user", "created_at", "acknowledged_at"]:
            self.assertIn(
                field,
                AlertSerializer.Meta.read_only_fields,
                f"Field '{field}' must be marked read_only.",
            )


class PortfolioMonitorServiceTestCase(TestCase):
    """Phase 2 test suite for deterministic PortfolioMonitorService."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="monitor_owner",
            email="owner@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="monitor_intruder",
            email="intruder@example.com",
            password="securepassword456",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Monitoring Test Portfolio",
        )
        self.service = PortfolioMonitorService()

    def test_concentration_breach_detected_above_35_percent(self):
        """1. Concentration breach is detected above 35%."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("40.0"), average_price=Decimal("1000.0"))
        Holding.objects.create(portfolio=self.portfolio, ticker="TCS", market="IN", quantity=Decimal("30.0"), average_price=Decimal("1000.0"))
        Holding.objects.create(portfolio=self.portfolio, ticker="INFY", market="IN", quantity=Decimal("30.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 1000.0, "TCS": 1000.0, "INFY": 1000.0}
        historical_prices = {
            "RELIANCE": [1000.0, 1000.0, 1000.0, 1000.0],
            "TCS": [1000.0, 1000.0, 1000.0, 1000.0],
            "INFY": [1000.0, 1000.0, 1000.0, 1000.0],
        }

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        conc_events = [e for e in result.events if e.alert_type == AlertType.CONCENTRATION_BREACH]
        self.assertEqual(len(conc_events), 1)
        self.assertEqual(conc_events[0].metadata["ticker"], "RELIANCE")
        self.assertEqual(conc_events[0].metric_value, Decimal("40.0000"))
        self.assertEqual(conc_events[0].threshold_value, Decimal("35.0"))

    def test_concentration_exactly_at_35_percent_does_not_breach(self):
        """2. Concentration exactly at 35% does NOT breach (strictly > 35%)."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("35.0"), average_price=Decimal("1000.0"))
        Holding.objects.create(portfolio=self.portfolio, ticker="TCS", market="IN", quantity=Decimal("35.0"), average_price=Decimal("1000.0"))
        Holding.objects.create(portfolio=self.portfolio, ticker="INFY", market="IN", quantity=Decimal("30.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 1000.0, "TCS": 1000.0, "INFY": 1000.0}
        historical_prices = {
            "RELIANCE": [1000.0, 1000.0, 1000.0, 1000.0],
            "TCS": [1000.0, 1000.0, 1000.0, 1000.0],
            "INFY": [1000.0, 1000.0, 1000.0, 1000.0],
        }

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        conc_events = [e for e in result.events if e.alert_type == AlertType.CONCENTRATION_BREACH]
        self.assertEqual(len(conc_events), 0)

    def test_multiple_concentration_breaches_returned(self):
        """3. Multiple concentration breaches are returned."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("50.0"), average_price=Decimal("1000.0"))
        Holding.objects.create(portfolio=self.portfolio, ticker="TCS", market="IN", quantity=Decimal("50.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 1000.0, "TCS": 1000.0}
        historical_prices = {
            "RELIANCE": [1000.0, 1000.0, 1000.0, 1000.0],
            "TCS": [1000.0, 1000.0, 1000.0, 1000.0],
        }

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        conc_events = [e for e in result.events if e.alert_type == AlertType.CONCENTRATION_BREACH]
        self.assertEqual(len(conc_events), 2)
        tickers = {e.metadata["ticker"] for e in conc_events}
        self.assertEqual(tickers, {"RELIANCE", "TCS"})

    def test_no_concentration_breach_returns_no_concentration_event(self):
        """4. No concentration breach returns no concentration event."""
        for ticker in ["A", "B", "C", "D"]:
            Holding.objects.create(portfolio=self.portfolio, ticker=ticker, market="IN", quantity=Decimal("25.0"), average_price=Decimal("100.0"))

        last_prices = {t: 100.0 for t in ["A", "B", "C", "D"]}
        historical_prices = {t: [100.0, 100.0, 100.0, 100.0] for t in ["A", "B", "C", "D"]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        conc_events = [e for e in result.events if e.alert_type == AlertType.CONCENTRATION_BREACH]
        self.assertEqual(len(conc_events), 0)

    def test_drawdown_breach_above_15_percent_detected(self):
        """5. Drawdown breach above 15% is detected."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("100.0"))

        last_prices = {"RELIANCE": 82.0}
        historical_prices = {"RELIANCE": [100.0, 100.0, 80.0, 82.0]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        dd_events = [e for e in result.events if e.alert_type == AlertType.DRAWDOWN_BREACH]
        self.assertEqual(len(dd_events), 1)
        self.assertEqual(dd_events[0].metric_value, Decimal("20.0000"))
        self.assertEqual(dd_events[0].threshold_value, Decimal("15.0"))
        self.assertIn("15.00%", dd_events[0].message)

    def test_drawdown_exactly_at_15_percent_does_not_breach(self):
        """6. Drawdown exactly at 15% does NOT breach (strictly > 15%)."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("100.0"))

        last_prices = {"RELIANCE": 86.0}
        historical_prices = {"RELIANCE": [100.0, 100.0, 85.0, 86.0]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        dd_events = [e for e in result.events if e.alert_type == AlertType.DRAWDOWN_BREACH]
        self.assertEqual(len(dd_events), 0)

    def test_severe_loss_below_minus_10_percent_detected(self):
        """7. Severe loss below -10% is detected."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 850.0}
        historical_prices = {"RELIANCE": [850.0, 850.0, 850.0, 850.0]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        loss_events = [e for e in result.events if e.alert_type == AlertType.LOSS_THRESHOLD]
        self.assertEqual(len(loss_events), 1)
        self.assertEqual(loss_events[0].metric_value, Decimal("-15.0000"))
        self.assertEqual(loss_events[0].threshold_value, Decimal("-10.0"))

    def test_loss_exactly_minus_10_percent_does_not_breach(self):
        """8. Loss exactly -10% does NOT breach (strictly < -10%)."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 900.0}
        historical_prices = {"RELIANCE": [900.0, 900.0, 900.0, 900.0]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        loss_events = [e for e in result.events if e.alert_type == AlertType.LOSS_THRESHOLD]
        self.assertEqual(len(loss_events), 0)

    def test_no_loss_breach_when_above_threshold(self):
        """9. No loss breach when above threshold (e.g. +5% profit)."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 1050.0}
        historical_prices = {"RELIANCE": [1000.0, 1020.0, 1040.0, 1050.0]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        loss_events = [e for e in result.events if e.alert_type == AlertType.LOSS_THRESHOLD]
        self.assertEqual(len(loss_events), 0)

    def test_multiple_condition_types_returned_together(self):
        """10. Multiple condition types can be returned together (concentration + drawdown + loss)."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 750.0}
        historical_prices = {"RELIANCE": [1000.0, 1000.0, 750.0, 750.0]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        types = {e.alert_type for e in result.events}
        self.assertIn(AlertType.CONCENTRATION_BREACH, types)
        self.assertIn(AlertType.DRAWDOWN_BREACH, types)
        self.assertIn(AlertType.LOSS_THRESHOLD, types)
        self.assertEqual(len(result.events), 3)

    def test_empty_or_no_holdings_behaves_safely(self):
        """11. Empty/no holdings behaves safely, returning 0 events."""
        result = self.service.evaluate(portfolio=self.portfolio)
        self.assertEqual(result.portfolio_id, str(self.portfolio.id))
        self.assertEqual(len(result.events), 0)

    def test_historical_data_absence_behaves_according_to_existing_risk_service(self):
        """12. Historical-data absence behaves according to existing risk-service behavior."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("1000.0"))
        last_prices = {"RELIANCE": 1000.0}

        mock_builder = PortfolioWorkflowInputBuilder(
            historical_data_fetcher=lambda **kwargs: {"ticker": "RELIANCE", "candles": []}
        )
        service = PortfolioMonitorService(workflow_input_builder=mock_builder)

        with self.assertRaises(ValueError) as ctx:
            service.evaluate(
                portfolio=self.portfolio,
                last_prices=last_prices,
                historical_prices=None,
            )
        self.assertIn("contains no candles", str(ctx.exception))

    def test_returned_metric_and_threshold_values_are_correct_decimals(self):
        """13. Returned metric/threshold values are correct Decimal values."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("1000.0"))

        last_prices = {"RELIANCE": 800.0}
        historical_prices = {"RELIANCE": [1000.0, 1000.0, 800.0, 800.0]}

        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )

        for event in result.events:
            self.assertIsInstance(event.metric_value, Decimal)
            self.assertIsInstance(event.threshold_value, Decimal)

    def test_ownership_cross_tenant_access_is_rejected(self):
        """14. Ownership/cross-tenant access is rejected with PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            self.service.evaluate(
                portfolio=self.portfolio,
                user=self.other_user,
            )

    def test_monitor_does_not_create_alert_database_rows(self):
        """15. Monitor does not create Alert database rows."""
        Holding.objects.create(portfolio=self.portfolio, ticker="RELIANCE", market="IN", quantity=Decimal("10.0"), average_price=Decimal("1000.0"))
        last_prices = {"RELIANCE": 700.0}
        historical_prices = {"RELIANCE": [1000.0, 1000.0, 700.0, 700.0]}

        initial_count = Alert.objects.count()
        result = self.service.evaluate(
            portfolio=self.portfolio,
            last_prices=last_prices,
            historical_prices=historical_prices,
        )
        self.assertGreater(len(result.events), 0)
        self.assertEqual(Alert.objects.count(), initial_count)


class PortfolioAlertsAPITestCase(TestCase):
    """Phase 3 test suite for Portfolio Alerts REST API and On-Demand Evaluation."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="alert_owner",
            email="owner@example.com",
            password="securepassword123",
        )
        self.other_user = User.objects.create_user(
            username="alert_intruder",
            email="intruder@example.com",
            password="securepassword456",
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Main Monitored Portfolio",
        )
        self.portfolio_2 = Portfolio.objects.create(
            user=self.user,
            name="Second Monitored Portfolio",
        )
        self.other_portfolio = Portfolio.objects.create(
            user=self.other_user,
            name="Foreign Monitored Portfolio",
        )

    def _mock_market_data_breach(self, ticker, market="IN"):
        prices = {
            "RELIANCE": {"last_price": 700.0},
            "TCS": {"last_price": 1000.0},
            "INFY": {"last_price": 1000.0},
        }
        return prices.get(ticker.upper(), {"last_price": 1000.0})

    def _mock_historical_data_breach(self, ticker, to_date=None, from_date=None, market="IN"):
        histories = {
            "RELIANCE": {"candles": [{"close": 1000.0}, {"close": 1000.0}, {"close": 700.0}, {"close": 700.0}]},
            "TCS": {"candles": [{"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}]},
            "INFY": {"candles": [{"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}]},
        }
        return histories.get(ticker.upper(), {"candles": [{"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}]})

    def test_authenticated_owner_can_list_alerts(self):
        """1. Authenticated owner can list alerts."""
        a1 = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Breach 1",
            metric_value=Decimal("40.0"),
            threshold_value=Decimal("35.0"),
        )
        a2 = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.DRAWDOWN_BREACH,
            title="Breach 2",
            metric_value=Decimal("20.0"),
            threshold_value=Decimal("15.0"),
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-alert-list", kwargs={"portfolio_id": self.portfolio.id})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]["id"], str(a2.id))
        self.assertEqual(res.data[1]["id"], str(a1.id))

    def test_unauthenticated_alert_listing_is_rejected(self):
        """2. Unauthenticated alert listing is rejected with 401 Unauthorized."""
        url = reverse("portfolio-alert-list", kwargs={"portfolio_id": self.portfolio.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_foreign_user_cannot_list_another_portfolio_alerts(self):
        """3. Foreign user cannot list another portfolio's alerts (returns 404 Not Found)."""
        Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Secret Breach",
            metric_value=Decimal("40.0"),
            threshold_value=Decimal("35.0"),
        )
        self.client.force_authenticate(user=self.other_user)
        url = reverse("portfolio-alert-list", kwargs={"portfolio_id": self.portfolio.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.ai.services.research_tools.get_historical_data")
    @patch("apps.ai.services.research_tools.get_market_data")
    def test_owner_can_trigger_on_demand_monitoring(self, mock_market, mock_hist):
        """4. Owner can trigger on-demand monitoring."""
        mock_market.side_effect = self._mock_market_data_breach
        mock_hist.side_effect = self._mock_historical_data_breach

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("1000.0"),
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    @patch("apps.ai.services.research_tools.get_historical_data")
    @patch("apps.ai.services.research_tools.get_market_data")
    def test_monitoring_creates_alert_records_for_detected_breaches(self, mock_market, mock_hist):
        """5. Monitoring creates Alert records for detected breaches."""
        mock_market.side_effect = self._mock_market_data_breach
        mock_hist.side_effect = self._mock_historical_data_breach

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("1000.0"),
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})
        self.assertEqual(Alert.objects.filter(portfolio=self.portfolio).count(), 0)

        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        alerts = Alert.objects.filter(portfolio=self.portfolio)
        self.assertGreater(alerts.count(), 0)
        for alert in alerts:
            self.assertEqual(alert.user, self.user)
            self.assertEqual(alert.status, AlertStatus.ACTIVE)

    @patch("apps.ai.services.research_tools.get_historical_data")
    @patch("apps.ai.services.research_tools.get_market_data")
    def test_monitoring_returns_detected_events_and_created_alerts(self, mock_market, mock_hist):
        """6. Monitoring returns detected events and created alerts in structured payload."""
        mock_market.side_effect = self._mock_market_data_breach
        mock_hist.side_effect = self._mock_historical_data_breach

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("1000.0"),
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["portfolio_id"], str(self.portfolio.id))
        self.assertIn("evaluated_at", res.data)
        self.assertIn("events", res.data)
        self.assertIn("alerts_created", res.data)
        self.assertIn("alerts_suppressed", res.data)
        self.assertGreater(len(res.data["alerts_created"]), 0)

    @patch("apps.ai.services.research_tools.get_historical_data")
    @patch("apps.ai.services.research_tools.get_market_data")
    def test_repeated_monitoring_within_24_hours_does_not_duplicate_same_alert_type(self, mock_market, mock_hist):
        """7. Repeated monitoring within 24 hours does not duplicate the same alert type."""
        mock_market.side_effect = self._mock_market_data_breach
        mock_hist.side_effect = self._mock_historical_data_breach

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("1000.0"),
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})

        res1 = self.client.post(url, {}, format="json")
        initial_count = Alert.objects.filter(portfolio=self.portfolio).count()
        self.assertGreater(initial_count, 0)
        self.assertEqual(len(res1.data["alerts_created"]), initial_count)

        res2 = self.client.post(url, {}, format="json")
        self.assertEqual(len(res2.data["alerts_created"]), 0)
        self.assertEqual(len(res2.data["alerts_suppressed"]), initial_count)
        self.assertEqual(Alert.objects.filter(portfolio=self.portfolio).count(), initial_count)

    @patch("apps.ai.services.research_tools.get_historical_data")
    @patch("apps.ai.services.research_tools.get_market_data")
    def test_concentration_events_preserve_ticker_context_under_cooldown(self, mock_market, mock_hist):
        """8. Concentration events preserve ticker context where applicable."""
        mock_market.return_value = {"last_price": 1000.0}
        mock_hist.return_value = {"candles": [{"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}, {"close": 1000.0}]}

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("40.0"),
            average_price=Decimal("1000.0"),
        )
        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="INFY",
            market="IN",
            quantity=Decimal("60.0"),
            average_price=Decimal("1000.0"),
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})
        res1 = self.client.post(url, {}, format="json")

        conc_created_1 = [a for a in res1.data["alerts_created"] if a["alert_type"] == AlertType.CONCENTRATION_BREACH]
        self.assertEqual(len(conc_created_1), 2)

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="TCS",
            market="IN",
            quantity=Decimal("100.0"),
            average_price=Decimal("1000.0"),
        )

        res2 = self.client.post(url, {}, format="json")
        created_tickers = [a["title"] for a in res2.data["alerts_created"] if a["alert_type"] == AlertType.CONCENTRATION_BREACH]
        self.assertEqual(len(created_tickers), 1)
        self.assertIn("TCS", created_tickers[0])

    @patch("apps.ai.services.research_tools.get_historical_data")
    @patch("apps.ai.services.research_tools.get_market_data")
    def test_different_portfolios_users_remain_isolated_under_cooldown(self, mock_market, mock_hist):
        """9. Different portfolios/users remain isolated under cooldown."""
        mock_market.side_effect = self._mock_market_data_breach
        mock_hist.side_effect = self._mock_historical_data_breach

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("1000.0"),
        )
        Holding.objects.create(
            portfolio=self.portfolio_2,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("1000.0"),
        )

        self.client.force_authenticate(user=self.user)
        url1 = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})
        url2 = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio_2.id})

        res1 = self.client.post(url1, {}, format="json")
        self.assertGreater(len(res1.data["alerts_created"]), 0)

        res2 = self.client.post(url2, {}, format="json")
        self.assertGreater(len(res2.data["alerts_created"]), 0)

    def test_owner_can_acknowledge_active_alert(self):
        """10. Owner can acknowledge an ACTIVE alert."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Breach",
            metric_value=Decimal("40.0"),
            threshold_value=Decimal("35.0"),
            status=AlertStatus.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-alert-acknowledge", kwargs={"portfolio_id": self.portfolio.id, "alert_id": alert.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_acknowledgement_sets_status_acknowledged(self):
        """11. Acknowledgement sets status=ACKNOWLEDGED."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.DRAWDOWN_BREACH,
            title="Breach",
            metric_value=Decimal("20.0"),
            threshold_value=Decimal("15.0"),
            status=AlertStatus.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-alert-acknowledge", kwargs={"portfolio_id": self.portfolio.id, "alert_id": alert.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "ACKNOWLEDGED")
        alert.refresh_from_db()
        self.assertEqual(alert.status, AlertStatus.ACKNOWLEDGED)

    def test_acknowledgement_sets_acknowledged_at(self):
        """12. Acknowledgement sets acknowledged_at timestamp."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.LOSS_THRESHOLD,
            title="Loss Breach",
            metric_value=Decimal("-15.0"),
            threshold_value=Decimal("-10.0"),
            status=AlertStatus.ACTIVE,
        )
        self.assertIsNone(alert.acknowledged_at)

        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-alert-acknowledge", kwargs={"portfolio_id": self.portfolio.id, "alert_id": alert.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(res.data["acknowledged_at"])
        alert.refresh_from_db()
        self.assertIsNotNone(alert.acknowledged_at)

    def test_repeated_acknowledgement_is_deterministic_and_idempotent(self):
        """13. Repeated acknowledgement is deterministic/idempotent."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Breach",
            metric_value=Decimal("40.0"),
            threshold_value=Decimal("35.0"),
            status=AlertStatus.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-alert-acknowledge", kwargs={"portfolio_id": self.portfolio.id, "alert_id": alert.id})

        res1 = self.client.post(url)
        alert.refresh_from_db()
        ack_time1 = alert.acknowledged_at

        res2 = self.client.post(url)
        alert.refresh_from_db()

        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(alert.acknowledged_at, ack_time1)

    def test_foreign_user_cannot_acknowledge_another_user_alert(self):
        """14. Foreign user cannot acknowledge another user's alert (returns 404)."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.DRAWDOWN_BREACH,
            title="Breach",
            metric_value=Decimal("20.0"),
            threshold_value=Decimal("15.0"),
            status=AlertStatus.ACTIVE,
        )
        self.client.force_authenticate(user=self.other_user)
        url = reverse("portfolio-alert-acknowledge", kwargs={"portfolio_id": self.portfolio.id, "alert_id": alert.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        alert.refresh_from_db()
        self.assertEqual(alert.status, AlertStatus.ACTIVE)

    def test_alert_belonging_to_different_portfolio_cannot_be_acknowledged_through_another_portfolio_url(self):
        """15. Alert belonging to a different portfolio cannot be acknowledged through another portfolio URL."""
        alert_in_other = Alert.objects.create(
            portfolio=self.other_portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Other Breach",
            metric_value=Decimal("40.0"),
            threshold_value=Decimal("35.0"),
            status=AlertStatus.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-alert-acknowledge", kwargs={"portfolio_id": self.portfolio.id, "alert_id": alert_in_other.id})
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        alert_in_other.refresh_from_db()
        self.assertEqual(alert_in_other.status, AlertStatus.ACTIVE)

    def test_monitor_endpoint_cannot_create_alerts_for_foreign_portfolio(self):
        """16. Monitor endpoint cannot create alerts for a foreign portfolio."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})
        res = self.client.post(url, {}, format="json")

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Alert.objects.filter(portfolio=self.portfolio).count(), 0)

    def test_alert_serializer_output_remains_read_only_and_server_controlled(self):
        """17. Alert serializer output remains read-only/server-controlled."""
        alert = Alert.objects.create(
            portfolio=self.portfolio,
            alert_type=AlertType.CONCENTRATION_BREACH,
            title="Server Title",
            metric_value=Decimal("40.0"),
            threshold_value=Decimal("35.0"),
        )
        serializer = AlertSerializer(
            instance=alert,
            data={
                "status": AlertStatus.RESOLVED,
                "user": self.other_user.id,
                "metric_value": Decimal("99.9999"),
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid())
        saved_alert = serializer.save()

        self.assertEqual(saved_alert.status, AlertStatus.ACTIVE)
        self.assertEqual(saved_alert.user, self.user)
        self.assertEqual(saved_alert.metric_value, Decimal("40.0000"))

    @patch("apps.ai.services.research_tools.get_historical_data")
    @patch("apps.ai.services.research_tools.get_market_data")
    def test_monitor_endpoint_does_not_accept_caller_controlled_user_ownership(self, mock_market, mock_hist):
        """18. Monitor endpoint does not accept caller-controlled user ownership."""
        mock_market.side_effect = self._mock_market_data_breach
        mock_hist.side_effect = self._mock_historical_data_breach

        Holding.objects.create(
            portfolio=self.portfolio,
            ticker="RELIANCE",
            market="IN",
            quantity=Decimal("10.0"),
            average_price=Decimal("1000.0"),
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("portfolio-monitor", kwargs={"portfolio_id": self.portfolio.id})
        res = self.client.post(
            url,
            {"user": self.other_user.id, "user_id": self.other_user.id, "portfolio": str(self.other_portfolio.id)},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for alert in Alert.objects.filter(portfolio=self.portfolio):
            self.assertEqual(alert.user, self.user)

    def test_transaction_behavior_is_safe_when_multiple_alerts_are_created(self):
        """19. Transaction behavior is safe when multiple alerts are created (atomic rollback on error)."""
        service = AlertService()
        result = MonitoringResult(
            portfolio_id=str(self.portfolio.id),
            evaluated_at=timezone.now(),
            events=[
                MonitoringEvent(
                    alert_type=AlertType.CONCENTRATION_BREACH,
                    severity=AlertSeverity.WARNING,
                    title="Breach 1",
                    message="msg 1",
                    metric_value=Decimal("40.0"),
                    threshold_value=Decimal("35.0"),
                ),
                MonitoringEvent(
                    alert_type=AlertType.DRAWDOWN_BREACH,
                    severity=AlertSeverity.WARNING,
                    title="Breach 2",
                    message="msg 2",
                    metric_value=Decimal("20.0"),
                    threshold_value=Decimal("15.0"),
                ),
            ],
        )

        initial_count = Alert.objects.filter(portfolio=self.portfolio).count()
        original_create = Alert.objects.create
        call_count = [0]

        def fail_on_second(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise IntegrityError("Simulated DB failure")
            return original_create(*args, **kwargs)

        with patch.object(Alert.objects, "create", side_effect=fail_on_second):
            with self.assertRaises(IntegrityError):
                service.process_monitoring_result(self.portfolio, result)

        self.assertEqual(Alert.objects.filter(portfolio=self.portfolio).count(), initial_count)

    def test_critical_section_serializes_with_select_for_update_and_prevents_duplicate_creation(self):
        """20. Critical section serializes portfolio evaluation with select_for_update and prevents duplicate creation."""
        service = AlertService()
        result = MonitoringResult(
            portfolio_id=str(self.portfolio.id),
            evaluated_at=timezone.now(),
            events=[
                MonitoringEvent(
                    alert_type=AlertType.DRAWDOWN_BREACH,
                    severity=AlertSeverity.CRITICAL,
                    title="Critical Drawdown",
                    message="Portfolio drawdown exceeds threshold.",
                    metric_value=Decimal("22.5"),
                    threshold_value=Decimal("15.0"),
                ),
            ],
        )

        with patch.object(Portfolio.objects, "select_for_update", wraps=Portfolio.objects.select_for_update) as mock_sfu:
            res1 = service.process_monitoring_result(self.portfolio, result)
            self.assertTrue(mock_sfu.called)

        self.assertEqual(len(res1["alerts_created"]), 1)
        self.assertEqual(Alert.objects.filter(portfolio=self.portfolio, alert_type=AlertType.DRAWDOWN_BREACH).count(), 1)

        # Immediate second evaluation on the same portfolio:
        # Serialized critical section executes cooldown inside atomic block and suppresses duplicate
        with patch.object(Portfolio.objects, "select_for_update", wraps=Portfolio.objects.select_for_update) as mock_sfu2:
            res2 = service.process_monitoring_result(self.portfolio, result)
            self.assertTrue(mock_sfu2.called)

        self.assertEqual(len(res2["alerts_created"]), 0)
        self.assertEqual(len(res2["alerts_suppressed"]), 1)
        self.assertEqual(Alert.objects.filter(portfolio=self.portfolio, alert_type=AlertType.DRAWDOWN_BREACH).count(), 1)

