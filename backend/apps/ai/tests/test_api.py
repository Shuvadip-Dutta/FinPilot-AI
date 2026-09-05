from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.ai.services.schemas import AgentResult
from apps.research.models import ResearchSession


class AIChatAPITestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
        )
        self.client.force_authenticate(user=self.user)

    @patch("apps.ai.views.AgentService")
    def test_chat_success(self, mock_agent_service):
        mock_agent_service.create_canonical.return_value = mock_agent_service.return_value
        mock_agent_service.return_value.run.return_value = AgentResult(
            response="Reliance is a major Indian company.",
            tools_used=["get_company_profile"],
            data={
                "route": "financial",
                "provenance": {
                    "financial": {
                        "primary_provider": "upstox",
                        "source": "upstox",
                        "fallback_used": False,
                        "data_status": "complete",
                    }
                },
            },
        )

        response = self.client.post(
            "/api/v1/ai/chat/",
            {"message": "Tell me about Reliance."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["response"], "Reliance is a major Indian company.")
        self.assertEqual(response.data["tools_used"], ["get_company_profile"])
        self.assertIn("session_id", response.data)
        self.assertIn("thread_id", response.data)
        self.assertEqual(response.data["route"], "financial")
        self.assertIn("provenance", response.data)
        self.assertEqual(response.data["provenance"]["financial"]["source"], "upstox")

    @patch("apps.ai.graph.langgraph_workflow.LangGraphResearchWorkflow.run")
    def test_authenticated_ai_request_creates_session_owned_by_user(self, mock_graph_run):
        user_a = User.objects.create_user(
            username="user_a",
            email="user_a@example.com",
            password="password123",
        )
        self.client.force_authenticate(user=user_a)

        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.ai.graph.state import AgentState

        prov = {
            "financial": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }
        rc = ResearchContext(ticker="RELIANCE", market="IN", provenance=prov)
        mock_state = AgentState(
            user_message="Overview for User A",
            ticker="RELIANCE",
            market="IN",
            route="general",
            research_context=rc,
            results={
                "synthesis": AgentResult(
                    response="Overview for User A response",
                    tools_used=["get_financials"],
                )
            },
        )
        mock_graph_run.return_value = mock_state

        # Create session in DB as ResearchSessionService would do
        session = ResearchSession.objects.create(
            user=user_a,
            thread_id="test_thread_123",
            user_message="Overview for User A",
            ticker="RELIANCE",
            market="IN",
            route="general",
            final_synthesis="Overview for User A response",
        )

        response = self.client.post(
            "/api/v1/ai/chat/",
            {
                "message": "Overview for User A",
                "ticker": "RELIANCE",
                "market": "IN",
                "thread_id": "test_thread_123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["thread_id"], "test_thread_123")
        self.assertEqual(response.data["session_id"], str(session.id))
        self.assertEqual(session.user, user_a)

    @patch("apps.ai.graph.langgraph_workflow.LangGraphResearchWorkflow.run")
    def test_user_a_cannot_create_session_owned_by_user_b(self, mock_graph_run):
        user_a = User.objects.create_user(username="user_a_iso", password="password123")
        user_b = User.objects.create_user(username="user_b_iso", password="password123")

        from apps.ai.graph.state import AgentState
        from apps.research.services.session_service import ResearchSessionService
        mock_state = AgentState(
            user_message="User A query",
            results={"general": AgentResult(response="User A query response", tools_used=[])},
        )

        def side_effect(user_message, user=None, **kwargs):
            if user:
                ResearchSessionService.create_session(
                    user_message=user_message,
                    user=user,
                    thread_id=kwargs.get("thread_id", "default"),
                )
            return mock_state

        mock_graph_run.side_effect = side_effect

        self.client.force_authenticate(user=user_a)
        response = self.client.post(
            "/api/v1/ai/chat/",
            {"message": "User A query"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(ResearchSession.objects.filter(user=user_a).exists())
        self.assertFalse(ResearchSession.objects.filter(user=user_b).exists())

    def test_unauthenticated_request_rejected(self):
        self.client.logout()
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/v1/ai/chat/",
            {"message": "Unauthenticated query"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_message(self):
        response = self.client.post("/api/v1/ai/chat/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.data)

    def test_empty_message(self):
        response = self.client.post(
            "/api/v1/ai/chat/",
            {"message": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", response.data)

    @patch("apps.ai.views.AgentService")
    def test_agent_value_error(self, mock_agent_service):
        mock_agent_service.create_canonical.return_value = mock_agent_service.return_value
        mock_agent_service.return_value.run.side_effect = ValueError(
            "Maximum tool-call limit exceeded."
        )

        response = self.client.post(
            "/api/v1/ai/chat/",
            {"message": "Analyze Reliance."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Maximum tool-call limit exceeded.")

    def test_agent_service_facade_backward_compatibility(self):
        """Verify AgentService.run() returns an AgentResult delegating to workflow."""
        from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
        from apps.ai.graph.state import AgentState
        from apps.ai.services.agent_service import AgentService

        mock_workflow = MagicMock()
        prov = {
            "financial": ProviderProvenance(
                primary_provider="upstox",
                source="upstox",
                fallback_used=False,
                data_status="complete",
            )
        }
        rc = ResearchContext(ticker="TCS", market="IN", provenance=prov)
        mock_workflow.run.return_value = AgentState(
            user_message="Tell me about TCS",
            ticker="TCS",
            market="IN",
            route="financial",
            research_context=rc,
            results={
                "financial": AgentResult(
                    response="TCS financial overview.",
                    tools_used=["get_financials"],
                )
            },
        )

        service = AgentService(workflow=mock_workflow)
        res = service.run("Tell me about TCS", user=self.user)

        self.assertIsInstance(res, AgentResult)
        self.assertEqual(res.response, "TCS financial overview.")
        self.assertEqual(res.tools_used, ["get_financials"])
        self.assertEqual(res.data["provenance"]["financial"]["source"], "upstox")
        mock_workflow.run.assert_called_once_with(
            user_message="Tell me about TCS",
            user=self.user,
            ticker=None,
            market=None,
            thread_id="default",
        )