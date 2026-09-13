"""Deterministic portfolio monitoring engine.

Evaluates portfolios against quantitative risk and health thresholds:
1. Concentration breach (holding weight > concentration_threshold)
2. Maximum drawdown breach (max drawdown > drawdown_threshold)
3. Severe portfolio loss (unrealized P/L % < loss_threshold)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from django.core.exceptions import PermissionDenied, ValidationError

from apps.ai.portfolio.adapters import create_portfolio_market_data_adapter
from apps.ai.portfolio.intelligence import (
    PortfolioIntelligenceService,
    PortfolioMarketDataError,
)
from apps.ai.portfolio.risk import (
    PortfolioRiskEngine,
    PortfolioRiskError,
    calculate_current_weights,
)
from apps.portfolio.builder import PortfolioWorkflowInputBuilder
from apps.portfolio.models import AlertSeverity, AlertStatus, AlertType, Portfolio


@dataclass
class MonitoringConfig:
    """Configurable thresholds for portfolio monitoring."""

    concentration_threshold: Decimal = Decimal("35.0")
    drawdown_threshold: Decimal = Decimal("15.0")
    loss_threshold: Decimal = Decimal("-10.0")


@dataclass
class MonitoringEvent:
    """Structured data for a detected monitoring condition breach."""

    alert_type: str
    severity: str
    title: str
    message: str
    metric_value: Decimal
    threshold_value: Decimal
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringResult:
    """Outcome of evaluating a portfolio against monitoring conditions."""

    portfolio_id: str
    evaluated_at: datetime
    events: list[MonitoringEvent] = field(default_factory=list)


class PortfolioMonitorService:
    """Deterministic evaluation engine for portfolio monitoring conditions.

    Does not create database records or perform external network calls when
    pre-fetched market prices are supplied.
    """

    def __init__(
        self,
        config: MonitoringConfig | None = None,
        market_data_adapter: Any | None = None,
        workflow_input_builder: PortfolioWorkflowInputBuilder | None = None,
        risk_engine: PortfolioRiskEngine | None = None,
    ):
        self.config = config or MonitoringConfig()
        self.market_data_adapter = market_data_adapter or create_portfolio_market_data_adapter()
        self.workflow_input_builder = workflow_input_builder or PortfolioWorkflowInputBuilder()
        self.risk_engine = risk_engine or PortfolioRiskEngine()

    def evaluate(
        self,
        portfolio: Portfolio | str | uuid.UUID,
        user: Any | None = None,
        last_prices: dict[str, float] | None = None,
        historical_prices: dict[str, list[float]] | None = None,
        to_date: str | None = None,
        from_date: str | None = None,
    ) -> MonitoringResult:
        """Evaluate a portfolio against all active monitoring conditions deterministically."""
        portfolio_obj = self._resolve_portfolio(portfolio, user=user)
        canonical_portfolio = portfolio_obj.to_pydantic()

        evaluated_at = datetime.now(timezone.utc)
        portfolio_id_str = str(portfolio_obj.id)

        # Empty / no holdings edge case
        if not canonical_portfolio.holdings:
            return MonitoringResult(
                portfolio_id=portfolio_id_str,
                evaluated_at=evaluated_at,
                events=[],
            )

        events: list[MonitoringEvent] = []

        # 1. Resolve live/last prices
        resolved_last_prices = self._resolve_last_prices(canonical_portfolio, last_prices)

        # 2. Evaluate Condition A: Concentration breach
        concentration_events = self._evaluate_concentration(
            canonical_portfolio=canonical_portfolio,
            last_prices=resolved_last_prices,
        )
        events.extend(concentration_events)

        # 3. Evaluate Condition B: Maximum drawdown breach
        drawdown_event = self._evaluate_drawdown(
            canonical_portfolio=canonical_portfolio,
            last_prices=resolved_last_prices,
            historical_prices=historical_prices,
            to_date=to_date,
            from_date=from_date,
        )
        if drawdown_event:
            events.append(drawdown_event)

        # 4. Evaluate Condition C: Severe portfolio loss
        loss_event = self._evaluate_loss(
            canonical_portfolio=canonical_portfolio,
            last_prices=resolved_last_prices,
        )
        if loss_event:
            events.append(loss_event)

        return MonitoringResult(
            portfolio_id=portfolio_id_str,
            evaluated_at=evaluated_at,
            events=events,
        )

    def _resolve_portfolio(
        self,
        portfolio: Portfolio | str | uuid.UUID,
        user: Any | None = None,
    ) -> Portfolio:
        """Resolve Portfolio instance from DB and verify user ownership if user is supplied."""
        if isinstance(portfolio, Portfolio):
            portfolio_obj = portfolio
        else:
            try:
                portfolio_obj = (
                    Portfolio.objects.select_related("user")
                    .prefetch_related("holdings")
                    .get(pk=portfolio)
                )
            except (Portfolio.DoesNotExist, ValidationError, ValueError) as exc:
                raise ValueError(f"Portfolio '{portfolio}' not found.") from exc

        if user is not None:
            user_id = getattr(user, "id", user)
            if portfolio_obj.user_id != user_id:
                raise PermissionDenied("Portfolio does not belong to the specified user.")

        return portfolio_obj

    def _resolve_last_prices(
        self,
        canonical_portfolio: Any,
        last_prices: dict[str, float] | None,
    ) -> dict[str, float]:
        """Normalize or fetch last traded prices for all holdings."""
        if last_prices is not None:
            return {k.strip().upper(): float(v) for k, v in last_prices.items()}

        intel_service = PortfolioIntelligenceService(market_data_tool=self.market_data_adapter)
        return intel_service.get_last_prices(canonical_portfolio)

    def _evaluate_concentration(
        self,
        canonical_portfolio: Any,
        last_prices: dict[str, float],
    ) -> list[MonitoringEvent]:
        """Evaluate holding weights against concentration_threshold."""
        events: list[MonitoringEvent] = []
        weights = calculate_current_weights(canonical_portfolio, last_prices)

        # Iterate deterministically across holdings sorted by ticker
        sorted_tickers = sorted(weights.keys())
        for ticker in sorted_tickers:
            weight = weights[ticker]
            # Convert weight to percentage (e.g. 0.385 -> 38.5000)
            weight_pct = Decimal(str(round(weight * 100, 4)))
            if weight_pct > self.config.concentration_threshold:
                severity = (
                    AlertSeverity.CRITICAL
                    if weight_pct >= Decimal("50.0")
                    else AlertSeverity.WARNING
                )
                events.append(
                    MonitoringEvent(
                        alert_type=AlertType.CONCENTRATION_BREACH,
                        severity=severity,
                        title=f"Concentration breach: {ticker}",
                        message=(
                            f"Holding {ticker} concentration of {weight_pct:.2f}% "
                            f"exceeds the {self.config.concentration_threshold:.2f}% threshold."
                        ),
                        metric_value=weight_pct,
                        threshold_value=self.config.concentration_threshold,
                        metadata={"ticker": ticker, "weight_pct": float(weight_pct)},
                    )
                )
        return events

    def _evaluate_drawdown(
        self,
        canonical_portfolio: Any,
        last_prices: dict[str, float],
        historical_prices: dict[str, list[float]] | None,
        to_date: str | None,
        from_date: str | None,
    ) -> MonitoringEvent | None:
        """Evaluate portfolio maximum drawdown against drawdown_threshold."""
        weights = calculate_current_weights(canonical_portfolio, last_prices)

        if historical_prices is None:
            historical_prices = self.workflow_input_builder.fetch_portfolio_historical_prices(
                portfolio=canonical_portfolio,
                to_date=to_date,
                from_date=from_date,
            )

        metrics = self.risk_engine.calculate(
            historical_prices=historical_prices,
            weights=weights,
        )

        drawdown_pct = Decimal(str(round(metrics.max_drawdown * 100, 4)))
        if drawdown_pct > self.config.drawdown_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if drawdown_pct >= Decimal("25.0")
                else AlertSeverity.WARNING
            )
            return MonitoringEvent(
                alert_type=AlertType.DRAWDOWN_BREACH,
                severity=severity,
                title="Maximum drawdown breach",
                message=(
                    f"Portfolio maximum drawdown of {drawdown_pct:.2f}% "
                    f"exceeds the {self.config.drawdown_threshold:.2f}% threshold."
                ),
                metric_value=drawdown_pct,
                threshold_value=self.config.drawdown_threshold,
                metadata={
                    "max_drawdown_pct": float(drawdown_pct),
                    "duration_days": metrics.max_drawdown_duration_days,
                },
            )
        return None

    def _evaluate_loss(
        self,
        canonical_portfolio: Any,
        last_prices: dict[str, float],
    ) -> MonitoringEvent | None:
        """Evaluate unrealized portfolio P/L percentage against loss_threshold."""
        # Inject adapter using last_prices for PortfolioIntelligenceService
        def custom_market_tool(ticker: str, market: str = "IN") -> dict[str, float]:
            norm_ticker = ticker.strip().upper()
            if norm_ticker in last_prices:
                return {"last_price": float(last_prices[norm_ticker])}
            return self.market_data_adapter(ticker=ticker, market=market)

        intel_service = PortfolioIntelligenceService(market_data_tool=custom_market_tool)
        intel = intel_service.analyze(canonical_portfolio)

        pnl_pct = Decimal(str(round(intel.profit_loss_percentage, 4)))
        if pnl_pct < self.config.loss_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if pnl_pct <= Decimal("-20.0")
                else AlertSeverity.WARNING
            )
            return MonitoringEvent(
                alert_type=AlertType.LOSS_THRESHOLD,
                severity=severity,
                title="Severe portfolio loss",
                message=(
                    f"Portfolio unrealized loss of {pnl_pct:.2f}% "
                    f"exceeds the {self.config.loss_threshold:.2f}% threshold."
                ),
                metric_value=pnl_pct,
                threshold_value=self.config.loss_threshold,
                metadata={
                    "pnl_pct": float(pnl_pct),
                    "profit_loss": intel.profit_loss,
                    "invested_value": intel.invested_value,
                    "current_value": intel.current_value,
                },
            )
        return None
