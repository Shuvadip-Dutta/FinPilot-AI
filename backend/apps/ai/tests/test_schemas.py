import json

from django.test import SimpleTestCase
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from apps.ai.services.schemas import AgentResult


class AgentResultSchemaTestCase(SimpleTestCase):

    def test_existing_construction_remains_compatible(self):
        result = AgentResult(response="x", tools_used=[])

        self.assertIsNone(result.data)

    def test_structured_data_is_optional_and_json_serializable(self):
        result = AgentResult(
            response="x",
            tools_used=["get_market_data"],
            data={"ticker": "RELIANCE", "quotes": [{"price": 1309.0}]},
        )

        serialized = result.model_dump(mode="json")
        restored = AgentResult.model_validate(serialized)

        self.assertEqual(restored.data, result.data)
        self.assertEqual(json.loads(json.dumps(serialized))["data"], result.data)

    def test_checkpoint_serializer_round_trip_preserves_agent_result_data(self):
        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=[("apps.ai.services.schemas", "AgentResult")]
        )
        result = AgentResult(
            response="x",
            tools_used=[],
            data={"aggregated_sentiment": {"positive": 2}},
        )

        type_tag, payload = serializer.dumps_typed(result)
        restored = serializer.loads_typed((type_tag, payload))

        self.assertEqual(restored, result)

    def test_checkpoint_serializer_round_trip_portfolio_risk_metrics(self):
        import warnings
        from apps.ai.portfolio.schemas import PortfolioRiskMetrics

        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=[
                ("apps.ai.portfolio.schemas", "PortfolioRiskMetrics"),
            ]
        )
        metrics = PortfolioRiskMetrics(
            volatility=0.18,
            downside_volatility=0.12,
            sharpe_ratio=1.2,
            sortino_ratio=1.5,
            calmar_ratio=1.1,
            max_drawdown=0.10,
            max_drawdown_duration_days=35,
            var_95_historical=0.02,
            cvar_95_historical=0.03,
            annualized_return=0.15,
            cagr=0.14,
            total_period_return=0.30,
        )

        with warnings.catch_warnings(record=True) as recorded_warnings:
            warnings.simplefilter("always")
            type_tag, payload = serializer.dumps_typed(metrics)
            restored = serializer.loads_typed((type_tag, payload))

        self.assertEqual(restored, metrics)
        serializer_warnings = [
            w
            for w in recorded_warnings
            if "whitelist" in str(w.message).lower() or "untrusted" in str(w.message).lower()
        ]
        self.assertEqual(serializer_warnings, [])
