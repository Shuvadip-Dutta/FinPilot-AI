from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from apps.ai.services.schemas import AgentResult


class AIChatAPITestCase(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()

    @patch(
        "apps.ai.views.AgentService"
    )
    def test_chat_success(
        self,
        mock_agent_service,
    ):

        mock_agent_service.return_value.run.return_value = (
            AgentResult(
                response=(
                    "Reliance is a major Indian company."
                ),
                tools_used=[
                    "get_company_profile",
                ],
            )
        )

        response = self.client.post(
            "/api/v1/ai/chat/",
            {
                "message": "Tell me about Reliance.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.data["response"],
            "Reliance is a major Indian company.",
        )

        self.assertEqual(
            response.data["tools_used"],
            [
                "get_company_profile",
            ],
        )

        mock_agent_service.return_value.run.assert_called_once_with(
            "Tell me about Reliance."
        )

    def test_missing_message(self):

        response = self.client.post(
            "/api/v1/ai/chat/",
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "message",
            response.data,
        )

    def test_empty_message(self):

        response = self.client.post(
            "/api/v1/ai/chat/",
            {
                "message": "   ",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertIn(
            "message",
            response.data,
        )

    @patch(
        "apps.ai.views.AgentService"
    )
    def test_agent_value_error(
        self,
        mock_agent_service,
    ):

        mock_agent_service.return_value.run.side_effect = (
            ValueError(
                "Maximum tool-call limit exceeded."
            )
        )

        response = self.client.post(
            "/api/v1/ai/chat/",
            {
                "message": "Analyze Reliance.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.data["error"],
            "Maximum tool-call limit exceeded.",
        )