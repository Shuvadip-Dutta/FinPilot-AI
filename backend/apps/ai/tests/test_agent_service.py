from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.graph.state import AgentState
from apps.ai.services.agent_service import AgentService
from apps.ai.services.schemas import AgentResult


class AgentServiceFacadeTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="facade_user",
            email="facade@example.com",
            password="password123",
        )

    def test_default_initialization_uses_canonical_workflow(self):
        service = AgentService()
        self.assertIsNotNone(service.workflow)
        self.assertIsInstance(service.workflow, LangGraphResearchWorkflow)

    def test_create_canonical_returns_agent_service_instance(self):
        service = AgentService.create_canonical()
        self.assertIsInstance(service, AgentService)
        self.assertIsInstance(service.workflow, LangGraphResearchWorkflow)

    def test_run_delegates_to_injected_workflow(self):
        mock_workflow = MagicMock()
        prov = {
            "financial": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }
        rc = ResearchContext(ticker="RELIANCE", market="IN", provenance=prov)
        mock_workflow.run.return_value = AgentState(
            user_message="Analyze Reliance",
            ticker="RELIANCE",
            market="IN",
            route="financial",
            research_context=rc,
            results={
                "financial": AgentResult(
                    response="Reliance financial analysis.",
                    tools_used=["get_financials"],
                )
            },
        )

        service = AgentService(workflow=mock_workflow)
        result = service.run(
            message="Analyze Reliance",
            user=self.user,
            ticker="RELIANCE",
            market="IN",
            thread_id="thread_001",
        )

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.response, "Reliance financial analysis.")
        self.assertEqual(result.tools_used, ["get_financials"])
        self.assertEqual(result.data["route"], "financial")
        self.assertEqual(result.data["ticker"], "RELIANCE")
        self.assertEqual(result.data["market"], "IN")
        self.assertEqual(result.data["provenance"]["financial"]["source"], "upstox")

        mock_workflow.run.assert_called_once_with(
            user_message="Analyze Reliance",
            user=self.user,
            ticker="RELIANCE",
            market="IN",
            thread_id="thread_001",
        )

    def test_run_workflow_extracts_synthesis_or_route_result(self):
        mock_workflow = MagicMock()
        mock_workflow.run.return_value = AgentState(
            user_message="Overview request",
            route="general",
            results={
                "synthesis": AgentResult(
                    response="Final synthesized report",
                    tools_used=["get_news", "get_market_data"],
                )
            },
        )

        service = AgentService(workflow=mock_workflow)
        result = service.run("Overview request")

        self.assertEqual(result.response, "Final synthesized report")
        self.assertEqual(result.tools_used, ["get_news", "get_market_data"])

    def test_agent_result_schema(self):
        result = AgentResult(
            response="Test response",
            tools_used=["get_news"],
            data={"route": "news"},
        )
        self.assertEqual(result.response, "Test response")
        self.assertEqual(result.tools_used, ["get_news"])
        self.assertEqual(result.data["route"], "news")
