from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.graph.contracts import WorkflowDecision
from apps.ai.graph.state import AgentState


class AgentStateTestCase(SimpleTestCase):

    def test_valid_agent_state(self):
        state = AgentState(
            user_message="Show Reliance financials.",
            ticker="RELIANCE",
            market="IN",
        )

        self.assertEqual(
            state.user_message,
            "Show Reliance financials.",
        )
        self.assertEqual(state.ticker, "RELIANCE")
        self.assertEqual(state.market, "IN")

    def test_results_defaults_to_empty_dictionary(self):
        state = AgentState(user_message="Hello")

        self.assertEqual(state.results, {})

    def test_errors_defaults_to_empty_list(self):
        state = AgentState(user_message="Hello")

        self.assertEqual(state.errors, [])

    def test_route_can_be_assigned(self):
        state = AgentState(
            user_message="What is the price of TCS?",
            route="market",
        )

        self.assertEqual(state.route, "market")

    def test_smoke_workflow_state_uses_canonical_user_message(self):
        state = AgentState(
            user_message=(
                "Analyze RELIANCE for financial health, current market position, "
                "recent news sentiment, and key risks."
            ),
            ticker="RELIANCE",
            market="IN",
            route="risk",
            results={},
            errors=[],
        )

        self.assertEqual(state.ticker, "RELIANCE")
        self.assertEqual(state.route, "risk")
        self.assertEqual(state.results, {})
        self.assertEqual(state.errors, [])


class WorkflowDecisionTestCase(SimpleTestCase):

    def test_valid_workflow_decision(self):
        decision = WorkflowDecision(
            route="financial",
            reason="The message asks about company revenue.",
        )

        self.assertEqual(decision.route, "financial")
        self.assertEqual(
            decision.reason,
            "The message asks about company revenue.",
        )

    def test_invalid_workflow_decision_route_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            WorkflowDecision(
                route="unsupported",
                reason="This route is not permitted.",
            )
