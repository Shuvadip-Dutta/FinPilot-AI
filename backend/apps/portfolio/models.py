import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.ai.portfolio.schemas import (
    Holding as HoldingSchema,
    Portfolio as PortfolioSchema,
)


def validate_positive(value: Decimal | float) -> None:
    """Validate that a monetary or quantity value is strictly positive (> 0)."""
    if value is not None and value <= 0:
        raise ValidationError("Value must be strictly positive (> 0).")


class Portfolio(models.Model):
    """User portfolio container."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolios",
    )
    name = models.CharField(
        max_length=100,
        default="Primary Portfolio",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.user})"

    def to_pydantic(self) -> PortfolioSchema:
        """Project this Django Portfolio into the canonical Pydantic contract."""
        return portfolio_to_schema(self)


class Holding(models.Model):
    """An individual equity position in a portfolio."""

    MARKET_CHOICES = [
        ("IN", "India"),
        ("US", "United States"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    ticker = models.CharField(max_length=20)
    market = models.CharField(
        max_length=10,
        choices=MARKET_CHOICES,
        default="IN",
    )
    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[validate_positive],
    )
    average_price = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        validators=[validate_positive],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ticker"]
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "ticker", "market"],
                name="unique_portfolio_ticker_market",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="holding_quantity_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(average_price__gt=0),
                name="holding_average_price_gt_zero",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ticker} ({self.quantity} @ {self.average_price})"

    def clean(self) -> None:
        super().clean()
        if self.ticker:
            self.ticker = self.ticker.strip().upper()
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError(
                {"quantity": "Quantity must be strictly positive (> 0)."}
            )
        if self.average_price is not None and self.average_price <= 0:
            raise ValidationError(
                {"average_price": "Average price must be strictly positive (> 0)."}
            )

    def save(self, *args, **kwargs) -> None:
        if self.ticker:
            self.ticker = self.ticker.strip().upper()
        super().save(*args, **kwargs)

    def to_pydantic(self) -> HoldingSchema:
        """Project this Django Holding into the canonical Pydantic contract."""
        return holding_to_schema(self)


def holding_to_schema(holding: Holding) -> HoldingSchema:
    """Map a Django Holding ORM model to the canonical Pydantic Holding contract."""
    return HoldingSchema(
        ticker=holding.ticker,
        market=holding.market,
        quantity=float(holding.quantity),
        average_price=float(holding.average_price),
    )


def portfolio_to_schema(portfolio: Portfolio) -> PortfolioSchema:
    """Map a Django Portfolio ORM model to the canonical Pydantic Portfolio contract."""
    return PortfolioSchema(
        holdings=[holding_to_schema(h) for h in portfolio.holdings.all()]
    )


class AlertType(models.TextChoices):
    CONCENTRATION_BREACH = "concentration_breach", "Concentration Breach"
    DRAWDOWN_BREACH = "drawdown_breach", "Drawdown Breach"
    LOSS_THRESHOLD = "loss_threshold", "Loss Threshold"


class AlertSeverity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class AlertStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    RESOLVED = "RESOLVED", "Resolved"


class Alert(models.Model):
    """A deterministic portfolio-monitoring event or threshold breach."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_alerts",
    )
    alert_type = models.CharField(
        max_length=50,
        choices=AlertType.choices,
    )
    severity = models.CharField(
        max_length=20,
        choices=AlertSeverity.choices,
        default=AlertSeverity.WARNING,
    )
    title = models.CharField(
        max_length=200,
    )
    message = models.TextField(
        blank=True,
        default="",
    )
    metric_value = models.DecimalField(
        max_digits=18,
        decimal_places=4,
    )
    threshold_value = models.DecimalField(
        max_digits=18,
        decimal_places=4,
    )
    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.ACTIVE,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["portfolio", "alert_type", "created_at"],
                name="idx_alert_port_type_created",
            ),
            models.Index(
                fields=["portfolio", "status"],
                name="idx_alert_port_status",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.alert_type} on {self.portfolio.name} ({self.status})"

    def clean(self) -> None:
        super().clean()
        if self.portfolio_id and self.user_id:
            if self.portfolio.user_id != self.user_id:
                raise ValidationError(
                    {"user": "Alert user must match the portfolio owner."}
                )

    def save(self, *args, **kwargs) -> None:
        if self.portfolio_id and not self.user_id:
            self.user = self.portfolio.user
        self.clean()
        super().save(*args, **kwargs)
