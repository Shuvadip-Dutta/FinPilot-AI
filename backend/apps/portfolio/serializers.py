from decimal import Decimal
from rest_framework import serializers

from apps.portfolio.models import Holding, Portfolio


class HoldingSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(max_length=20)
    market = serializers.ChoiceField(choices=["IN", "US"], default="IN")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    average_price = serializers.DecimalField(max_digits=18, decimal_places=4)

    class Meta:
        model = Holding
        fields = [
            "id",
            "portfolio",
            "ticker",
            "market",
            "quantity",
            "average_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "portfolio", "created_at", "updated_at"]

    def validate_ticker(self, value: str) -> str:
        normalized = value.strip().upper() if value else ""
        if not normalized:
            raise serializers.ValidationError("Ticker must not be empty.")
        return normalized

    def validate_market(self, value: str) -> str:
        normalized = value.strip().upper() if value else "IN"
        if normalized not in ("IN", "US"):
            raise serializers.ValidationError("Market must be IN or US.")
        return normalized

    def validate_quantity(self, value: Decimal) -> Decimal:
        if value is None or value <= 0:
            raise serializers.ValidationError("Quantity must be strictly positive (> 0).")
        return value

    def validate_average_price(self, value: Decimal) -> Decimal:
        if value is None or value <= 0:
            raise serializers.ValidationError("Average price must be strictly positive (> 0).")
        return value

    def validate(self, attrs: dict) -> dict:
        portfolio = self.context.get("portfolio") or (self.instance.portfolio if self.instance else None)
        ticker = attrs.get("ticker", self.instance.ticker if self.instance else None)
        market = attrs.get("market", self.instance.market if self.instance else None)

        if portfolio and ticker and market:
            qs = Holding.objects.filter(
                portfolio=portfolio,
                ticker=ticker.strip().upper(),
                market=market.strip().upper(),
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"non_field_errors": ["A holding for this ticker and market already exists in the portfolio."]}
                )
        return attrs


class PortfolioSerializer(serializers.ModelSerializer):
    holdings = HoldingSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "name",
            "holdings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "holdings", "created_at", "updated_at"]


class PortfolioBacktestRequestSerializer(serializers.Serializer):
    from_date = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    to_date = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    benchmark_ticker = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    initial_capital = serializers.FloatField(required=False, default=100000.0, min_value=0.01)
    rebalance_frequency = serializers.ChoiceField(
        choices=["monthly", "quarterly", "annually", "periodic"],
        required=False,
        default="periodic",
    )
    in_sample_window_days = serializers.IntegerField(required=False, default=252, min_value=3)
    out_of_sample_step_days = serializers.IntegerField(required=False, default=21, min_value=1)
    transaction_cost_bps = serializers.FloatField(required=False, default=10.0, min_value=0.0)
    risk_free_rate = serializers.FloatField(required=False, default=0.0)
    min_weight = serializers.FloatField(required=False, default=0.0, min_value=0.0, max_value=1.0)
    max_weight = serializers.FloatField(required=False, default=1.0, min_value=0.0, max_value=1.0)

    def validate(self, attrs: dict) -> dict:
        min_w = attrs.get("min_weight", 0.0)
        max_w = attrs.get("max_weight", 1.0)
        if min_w > max_w:
            raise serializers.ValidationError({"min_weight": "min_weight cannot exceed max_weight."})
        return attrs


class PortfolioOptimizationRequestSerializer(serializers.Serializer):
    objective = serializers.ChoiceField(
        choices=["max_sharpe"],
        required=False,
        default="max_sharpe",
    )
    risk_free_rate = serializers.FloatField(required=False, default=0.0)
    min_weight = serializers.FloatField(required=False, default=0.0, min_value=0.0, max_value=1.0)
    max_weight = serializers.FloatField(required=False, default=1.0, min_value=0.0, max_value=1.0)
    from_date = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    to_date = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)

    def validate(self, attrs: dict) -> dict:
        min_w = attrs.get("min_weight", 0.0)
        max_w = attrs.get("max_weight", 1.0)
        if min_w > max_w:
            raise serializers.ValidationError({"min_weight": "min_weight cannot exceed max_weight."})
        return attrs


