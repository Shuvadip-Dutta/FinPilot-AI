import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.portfolio.optimization import OptimizationInput
from apps.ai.portfolio.schemas import (
    Holding as HoldingSchema,
    Portfolio as PortfolioSchema,
)
from apps.portfolio.builder import PortfolioWorkflowInputBuilder
from apps.portfolio.models import (
    Holding,
    Portfolio,
    holding_to_schema,
    portfolio_to_schema,
)

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






