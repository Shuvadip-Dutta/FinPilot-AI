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
