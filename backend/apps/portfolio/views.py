from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.portfolio.backtest import PortfolioBacktestEngine
from apps.ai.portfolio.backtest_evaluator import PortfolioBacktestEvaluator
from apps.portfolio.backtest_builder import PortfolioBacktestInputBuilder
from apps.portfolio.models import Holding, Portfolio
from apps.portfolio.serializers import (
    HoldingSerializer,
    PortfolioBacktestRequestSerializer,
    PortfolioOptimizationRequestSerializer,
    PortfolioSerializer,
)


class PortfolioListCreateView(APIView):
    """List and create portfolios for authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolios = Portfolio.objects.filter(user=request.user)
        serializer = PortfolioSerializer(portfolios, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PortfolioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        portfolio = serializer.save(user=request.user)
        return Response(
            PortfolioSerializer(portfolio).data,
            status=status.HTTP_201_CREATED,
        )


class PortfolioDetailView(APIView):
    """Retrieve, update, and delete an individual user portfolio."""

    permission_classes = [IsAuthenticated]

    def _get_portfolio(self, pk, user):
        return get_object_or_404(Portfolio, pk=pk, user=user)

    def get(self, request, pk):
        portfolio = self._get_portfolio(pk, request.user)
        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        return self.patch(request, pk)

    def patch(self, request, pk):
        portfolio = self._get_portfolio(pk, request.user)
        serializer = PortfolioSerializer(portfolio, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        portfolio = self._get_portfolio(pk, request.user)
        portfolio.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HoldingListCreateView(APIView):
    """List and create holdings for a specific user portfolio."""

    permission_classes = [IsAuthenticated]

    def _get_portfolio(self, portfolio_pk, user):
        return get_object_or_404(Portfolio, pk=portfolio_pk, user=user)

    def get(self, request, portfolio_pk):
        portfolio = self._get_portfolio(portfolio_pk, request.user)
        holdings = portfolio.holdings.all()
        serializer = HoldingSerializer(holdings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, portfolio_pk):
        portfolio = self._get_portfolio(portfolio_pk, request.user)
        serializer = HoldingSerializer(
            data=request.data,
            context={"portfolio": portfolio},
        )
        serializer.is_valid(raise_exception=True)
        holding = serializer.save(portfolio=portfolio)
        return Response(
            HoldingSerializer(holding).data,
            status=status.HTTP_201_CREATED,
        )


class HoldingDetailView(APIView):
    """Retrieve, update, and delete an individual holding."""

    permission_classes = [IsAuthenticated]

    def _get_holding(self, pk, user, portfolio_pk=None):
        if portfolio_pk:
            portfolio = get_object_or_404(Portfolio, pk=portfolio_pk, user=user)
            return get_object_or_404(Holding, pk=pk, portfolio=portfolio)
        return get_object_or_404(Holding, pk=pk, portfolio__user=user)

    def get(self, request, pk, portfolio_pk=None):
        holding = self._get_holding(pk, request.user, portfolio_pk)
        serializer = HoldingSerializer(holding)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk, portfolio_pk=None):
        return self.patch(request, pk, portfolio_pk)

    def patch(self, request, pk, portfolio_pk=None):
        holding = self._get_holding(pk, request.user, portfolio_pk)
        serializer = HoldingSerializer(
            holding,
            data=request.data,
            partial=True,
            context={"portfolio": holding.portfolio},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk, portfolio_pk=None):
        holding = self._get_holding(pk, request.user, portfolio_pk)
        holding.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortfolioBacktestView(APIView):
    """Execute walk-forward backtest and risk evaluation for a user's portfolio."""

    permission_classes = [IsAuthenticated]

    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)

        serializer = PortfolioBacktestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        builder = PortfolioBacktestInputBuilder()
        try:
            backtest_input = builder.build_backtest_input(
                portfolio=portfolio,
                to_date=validated_data.get("to_date"),
                from_date=validated_data.get("from_date"),
                benchmark_ticker=validated_data.get("benchmark_ticker"),
                initial_capital=validated_data.get("initial_capital", 100000.0),
                rebalance_frequency=validated_data.get("rebalance_frequency", "periodic"),
                in_sample_window_days=validated_data.get("in_sample_window_days", 252),
                out_of_sample_step_days=validated_data.get("out_of_sample_step_days", 21),
                transaction_cost_bps=validated_data.get("transaction_cost_bps", 10.0),
                risk_free_rate=validated_data.get("risk_free_rate", 0.0),
                min_weight=validated_data.get("min_weight", 0.0),
                max_weight=validated_data.get("max_weight", 1.0),
            )
        except (ValueError, TypeError) as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        engine = PortfolioBacktestEngine()
        engine_result = engine.run(backtest_input)

        if not engine_result.success:
            return Response(
                {"error": engine_result.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        evaluator = PortfolioBacktestEvaluator()
        final_result = evaluator.evaluate(backtest_input, engine_result)

        response_data = {
            "portfolio_id": str(portfolio.id),
            "benchmark_ticker": backtest_input.benchmark_ticker,
            "initial_capital": backtest_input.initial_capital,
            "from_date": validated_data.get("from_date"),
            "to_date": validated_data.get("to_date"),
            "strategy_metrics": final_result.strategy_metrics.model_dump() if final_result.strategy_metrics else None,
            "buy_and_hold_metrics": final_result.buy_and_hold_metrics.model_dump() if final_result.buy_and_hold_metrics else None,
            "benchmark_metrics": final_result.benchmark_metrics.model_dump() if final_result.benchmark_metrics else None,
            "relative_metrics": final_result.relative_metrics.model_dump() if final_result.relative_metrics else None,
            "final_portfolio_value": final_result.final_portfolio_value,
            "total_transaction_costs": final_result.total_transaction_costs,
            "rebalance_events": [e.model_dump() for e in final_result.rebalance_events] if final_result.rebalance_events else [],
            "equity_curve": final_result.equity_curve,
            "return_series": final_result.return_series,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PortfolioRiskView(APIView):
    """Calculate and return deterministic quantitative risk metrics for an authenticated user's portfolio."""

    permission_classes = [IsAuthenticated]

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)

        if not portfolio.holdings.exists():
            return Response(
                {"error": "Portfolio has no holdings. Add holdings to calculate risk metrics."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.ai.portfolio.adapters import create_portfolio_market_data_adapter
        from apps.ai.portfolio.intelligence import PortfolioIntelligenceService
        from apps.ai.portfolio.risk import PortfolioRiskEngine, calculate_current_weights
        from apps.portfolio.builder import PortfolioWorkflowInputBuilder

        # Parse optional query parameters
        risk_free_rate_param = request.query_params.get("risk_free_rate", 0.0)
        try:
            risk_free_rate = float(risk_free_rate_param)
        except (ValueError, TypeError):
            risk_free_rate = 0.0

        to_date = request.query_params.get("to_date")
        from_date = request.query_params.get("from_date")

        builder = PortfolioWorkflowInputBuilder()
        try:
            canonical_portfolio = portfolio.to_pydantic()
            historical_prices = builder.fetch_portfolio_historical_prices(
                portfolio=canonical_portfolio,
                to_date=to_date,
                from_date=from_date,
            )
        except (ValueError, TypeError) as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate current weights using latest market prices
        intel_service = PortfolioIntelligenceService(
            market_data_tool=create_portfolio_market_data_adapter()
        )
        try:
            last_prices = intel_service.get_last_prices(canonical_portfolio)
        except Exception:
            last_prices = {}

        for holding in canonical_portfolio.holdings:
            t = holding.ticker.strip().upper()
            if t not in last_prices or last_prices[t] <= 0:
                if t in historical_prices and historical_prices[t]:
                    last_prices[t] = float(historical_prices[t][-1])
                else:
                    last_prices[t] = float(holding.average_price)

        try:
            weights = calculate_current_weights(canonical_portfolio, last_prices)
        except (ValueError, TypeError) as exc:
            return Response(
                {"error": f"Failed to calculate holding weights: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate deterministic quantitative risk
        risk_engine = PortfolioRiskEngine()
        try:
            metrics = risk_engine.calculate(
                historical_prices=historical_prices,
                weights=weights,
                risk_free_rate=risk_free_rate,
            )
        except (ValueError, TypeError) as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metrics_dict = metrics.model_dump()
        response_data = {
            "portfolio_id": str(portfolio.id),
            "portfolio_name": portfolio.name,
            "risk_metrics": metrics_dict,
            **metrics_dict,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PortfolioOptimizationView(APIView):
    """Execute deterministic mean-variance portfolio optimization for an authenticated user's portfolio."""

    permission_classes = [IsAuthenticated]

    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, pk=portfolio_id, user=request.user)

        serializer = PortfolioOptimizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if not portfolio.holdings.exists():
            return Response(
                {"error": "Optimization requires at least two unique assets, portfolio has none."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.ai.portfolio.adapters import create_portfolio_market_data_adapter
        from apps.ai.portfolio.intelligence import PortfolioIntelligenceService
        from apps.ai.portfolio.optimization import PortfolioOptimizationEngine
        from apps.ai.portfolio.risk import calculate_current_weights
        from apps.portfolio.builder import PortfolioWorkflowInputBuilder

        builder = PortfolioWorkflowInputBuilder()
        try:
            optimization_input = builder.build_optimization_input(
                portfolio=portfolio,
                risk_free_rate=validated_data.get("risk_free_rate", 0.0),
                min_weight=validated_data.get("min_weight", 0.0),
                max_weight=validated_data.get("max_weight", 1.0),
                from_date=validated_data.get("from_date"),
                to_date=validated_data.get("to_date"),
            )
        except (ValueError, TypeError) as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute deterministic optimization
        engine = PortfolioOptimizationEngine()
        opt_result = engine.optimize(optimization_input)

        if not opt_result.success:
            return Response(
                {"error": opt_result.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate current portfolio weights using live/latest market prices
        canonical_portfolio = portfolio.to_pydantic()
        intel_service = PortfolioIntelligenceService(
            market_data_tool=create_portfolio_market_data_adapter()
        )
        try:
            last_prices = intel_service.get_last_prices(canonical_portfolio)
        except Exception:
            last_prices = {}

        for holding in canonical_portfolio.holdings:
            t = holding.ticker.strip().upper()
            if t not in last_prices or last_prices[t] <= 0:
                if t in optimization_input.historical_prices and optimization_input.historical_prices[t]:
                    last_prices[t] = float(optimization_input.historical_prices[t][-1])
                else:
                    last_prices[t] = float(holding.average_price)

        try:
            current_weights_map = calculate_current_weights(canonical_portfolio, last_prices)
        except Exception:
            asset_count = len(optimization_input.tickers)
            current_weights_map = {t: 1.0 / asset_count for t in optimization_input.tickers}

        # Compute current portfolio metrics using existing deterministic formulas
        returns = engine.calculate_returns(optimization_input)
        expected_returns = engine.calculate_annualized_expected_returns(returns)
        covariance = engine.calculate_annualized_covariance(returns)

        current_weights_list = [current_weights_map.get(t, 0.0) for t in optimization_input.tickers]
        total_curr = sum(current_weights_list)
        if total_curr > 0:
            current_weights_list = [w / total_curr for w in current_weights_list]

        try:
            cur_ret, cur_vol, cur_sharpe = engine.calculate_portfolio_metrics(
                weights=current_weights_list,
                expected_returns=expected_returns,
                covariance=covariance,
                risk_free_rate=optimization_input.risk_free_rate,
            )
        except Exception:
            cur_ret, cur_vol, cur_sharpe = 0.0, 0.0, 0.0

        current_metrics = {
            "expected_return": cur_ret,
            "volatility": cur_vol,
            "sharpe_ratio": cur_sharpe,
        }

        optimized_metrics = {
            "expected_return": opt_result.expected_return,
            "volatility": opt_result.volatility,
            "sharpe_ratio": opt_result.sharpe_ratio,
        }

        # Build weight comparisons
        weight_comparisons = []
        for ticker in optimization_input.tickers:
            cur_w = current_weights_map.get(ticker, 0.0) * 100.0
            tgt_w = opt_result.optimized_weights.get(ticker, 0.0) * 100.0
            diff = tgt_w - cur_w
            direction = "hold"
            if diff > 0.25:
                direction = "increase"
            elif diff < -0.25:
                direction = "decrease"

            h_obj = portfolio.holdings.filter(ticker__iexact=ticker).first()
            h_name = getattr(h_obj, "name", None) or ticker

            weight_comparisons.append({
                "ticker": ticker,
                "name": h_name,
                "current_weight": round(cur_w, 2),
                "target_weight": round(tgt_w, 2),
                "weight_difference": round(diff, 2),
                "direction": direction,
            })

        response_data = {
            "portfolio_id": str(portfolio.id),
            "portfolio_name": portfolio.name,
            "status": "success",
            "objective": validated_data.get("objective", "max_sharpe"),
            "current_weights": current_weights_map,
            "optimized_weights": opt_result.optimized_weights,
            "current_metrics": current_metrics,
            "optimized_metrics": optimized_metrics,
            "metrics": {
                "current_expected_return": cur_ret,
                "optimized_expected_return": opt_result.expected_return,
                "current_volatility": cur_vol,
                "optimized_volatility": opt_result.volatility,
                "current_sharpe": cur_sharpe,
                "optimized_sharpe": opt_result.sharpe_ratio,
                "expected_return": opt_result.expected_return,
                "volatility": opt_result.volatility,
                "sharpe_ratio": opt_result.sharpe_ratio,
            },
            "weight_comparisons": weight_comparisons,
            "comparisons": weight_comparisons,
        }

        return Response(response_data, status=status.HTTP_200_OK)

