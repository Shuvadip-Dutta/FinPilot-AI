from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.ai.mcp.access import (
    AgentToolAccess,
    AgentToolPolicy,
)


class AgentToolPolicyTestCase(SimpleTestCase):

    def test_default_policy(self):
        policy = AgentToolPolicy()

        self.assertEqual(
            policy.allowed_tools,
            set(),
        )

        self.assertEqual(
            policy.max_tool_calls,
            5,
        )

        self.assertEqual(
            policy.max_rounds,
            3,
        )

    def test_custom_policy(self):
        policy = AgentToolPolicy(
            allowed_tools={
                "get_financials",
                "get_key_metrics",
            },
            max_tool_calls=4,
            max_rounds=2,
        )

        self.assertEqual(
            policy.allowed_tools,
            {
                "get_financials",
                "get_key_metrics",
            },
        )

        self.assertEqual(
            policy.max_tool_calls,
            4,
        )

        self.assertEqual(
            policy.max_rounds,
            2,
        )

    def test_invalid_tool_call_limit(self):
        with self.assertRaises(ValidationError):
            AgentToolPolicy(
                max_tool_calls=0,
            )

    def test_invalid_round_limit(self):
        with self.assertRaises(ValidationError):
            AgentToolPolicy(
                max_rounds=0,
            )


class AgentToolAccessTestCase(SimpleTestCase):

    def setUp(self):
        self.access = AgentToolAccess(
            available_tools={
                "get_financials",
                "get_key_metrics",
                "get_market_data",
                "get_news",
            }
        )

    def test_get_allowed_tools(self):
        policy = AgentToolPolicy(
            allowed_tools={
                "get_financials",
                "get_key_metrics",
            }
        )

        result = self.access.get_allowed_tools(
            policy
        )

        self.assertEqual(
            result,
            {
                "get_financials",
                "get_key_metrics",
            },
        )

    def test_unknown_policy_tool_is_rejected(self):
        policy = AgentToolPolicy(
            allowed_tools={
                "get_financials",
                "unknown_tool",
            }
        )

        with self.assertRaises(ValueError) as context:
            self.access.get_allowed_tools(
                policy
            )

        self.assertIn(
            "Unknown MCP tools requested",
            str(context.exception),
        )

    def test_allowed_tool_passes(self):
        policy = AgentToolPolicy(
            allowed_tools={
                "get_financials",
            }
        )

        self.access.validate_tool(
            "get_financials",
            policy,
        )

    def test_disallowed_tool_is_rejected(self):
        policy = AgentToolPolicy(
            allowed_tools={
                "get_financials",
            }
        )

        with self.assertRaises(ValueError) as context:
            self.access.validate_tool(
                "get_news",
                policy,
            )

        self.assertEqual(
            str(context.exception),
            "MCP tool not allowed for this agent: get_news",
        )

    def test_unknown_tool_is_rejected(self):
        policy = AgentToolPolicy(
            allowed_tools={
                "get_financials",
            }
        )

        with self.assertRaises(ValueError) as context:
            self.access.validate_tool(
                "unknown_tool",
                policy,
            )

        self.assertEqual(
            str(context.exception),
            "Unknown MCP tool: unknown_tool",
        )

    def test_tool_call_limit(self):
        policy = AgentToolPolicy(
            max_tool_calls=3,
        )

        with self.assertRaises(ValueError) as context:
            self.access.validate_limits(
                tool_calls=4,
                rounds=1,
                policy=policy,
            )

        self.assertEqual(
            str(context.exception),
            "Maximum MCP tool-call limit exceeded.",
        )

    def test_round_limit(self):
        policy = AgentToolPolicy(
            max_rounds=2,
        )

        with self.assertRaises(ValueError) as context:
            self.access.validate_limits(
                tool_calls=1,
                rounds=3,
                policy=policy,
            )

        self.assertEqual(
            str(context.exception),
            "Maximum MCP round limit exceeded.",
        )

    def test_limits_at_boundary_are_allowed(self):
        policy = AgentToolPolicy(
            max_tool_calls=3,
            max_rounds=2,
        )

        self.access.validate_limits(
            tool_calls=3,
            rounds=2,
            policy=policy,
        )