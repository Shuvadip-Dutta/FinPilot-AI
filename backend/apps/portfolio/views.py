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
