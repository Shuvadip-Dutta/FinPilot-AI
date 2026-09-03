from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.ai.services.llm_service import LLMService


class LLMServiceTestCase(SimpleTestCase):

    @patch(
        "apps.ai.services.llm_service.GroqProvider"
    )
    def test_generate(self, mock_groq_provider):

        mock_provider = mock_groq_provider.return_value

        mock_provider.generate.return_value = (
            "Reliance Industries is a major Indian company."
        )

        service = LLMService()

        result = service.generate(
            [
                {
                    "role": "user",
                    "content": "Tell me about Reliance.",
                }
            ]
        )

        self.assertEqual(
            result,
            "Reliance Industries is a major Indian company.",
        )

        mock_provider.generate.assert_called_once_with(
            [
                {
                    "role": "user",
                    "content": "Tell me about Reliance.",
                }
            ]
        )

    @override_settings(
        GROQ_API_KEY="test-key",
        GROQ_MODEL="legacy-model",
        REASONING_MODEL="reasoning-model",
        FAST_MODEL="fast-model",
        EVALUATION_MODEL="evaluation-model",
        SYNTHESIS_MODEL="synthesis-model",
    )
    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_model_tier_selection(self, mock_groq_provider):
        LLMService()
        LLMService(model="reasoning")
        LLMService(model="fast")
        LLMService(model="evaluation")
        LLMService(model="synthesis")
        LLMService(model="qwen/custom-model")

        self.assertEqual(
            mock_groq_provider.call_args_list[0].kwargs["model"],
            "reasoning-model",
        )
        self.assertEqual(
            mock_groq_provider.call_args_list[1].kwargs["model"],
            "reasoning-model",
        )
        self.assertEqual(
            mock_groq_provider.call_args_list[2].kwargs["model"],
            "fast-model",
        )
        self.assertEqual(
            mock_groq_provider.call_args_list[3].kwargs["model"],
            "evaluation-model",
        )
        self.assertEqual(
            mock_groq_provider.call_args_list[4].kwargs["model"],
            "synthesis-model",
        )
        self.assertEqual(
            mock_groq_provider.call_args_list[5].kwargs["model"],
            "qwen/custom-model",
        )

    @override_settings(
        GROQ_MODEL="legacy-model",
        REASONING_MODEL="reasoning-model",
        FAST_MODEL="fast-model",
        EVALUATION_MODEL="evaluation-model",
        SYNTHESIS_MODEL="synthesis-model",
    )
    def test_settings_model_configuration(self):
        self.assertEqual(settings.GROQ_MODEL, "legacy-model")
        self.assertEqual(settings.REASONING_MODEL, "reasoning-model")
        self.assertEqual(settings.FAST_MODEL, "fast-model")
        self.assertEqual(settings.EVALUATION_MODEL, "evaluation-model")
        self.assertEqual(settings.SYNTHESIS_MODEL, "synthesis-model")

    @override_settings(
        GROQ_API_KEY="test-key",
        GROQ_MODEL="legacy-model",
        REASONING_MODEL=None,
        FAST_MODEL=None,
        EVALUATION_MODEL=None,
        SYNTHESIS_MODEL=None,
    )
    def test_default_and_backward_compatible_model_resolution(self):
        self.assertEqual(LLMService().model, "legacy-model")
        self.assertEqual(LLMService(model="fast").model, "legacy-model")
        self.assertEqual(LLMService(model="default").model, "legacy-model")
        self.assertEqual(LLMService(model="qwen/custom-model").model, "qwen/custom-model")

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_frozen_per_agent_model_resolution(self, mock_groq_provider):
        from apps.ai.agents.financial import FinancialAnalysisAgent
        from apps.ai.agents.market import MarketAnalysisAgent
        from apps.ai.agents.news import NewsIntelligenceAgent
        from apps.ai.agents.risk import RiskAnalysisAgent
        from apps.ai.agents.portfolio_optimization import PortfolioOptimizationAgent
        from apps.ai.agents.synthesis import FinalSynthesisAgent

        fin = FinancialAnalysisAgent()
        mkt = MarketAnalysisAgent()
        news = NewsIntelligenceAgent()
        risk = RiskAnalysisAgent()
        port = PortfolioOptimizationAgent()
        syn = FinalSynthesisAgent()

        self.assertEqual(fin.llm_service.model, "qwen/qwen3.6-27b")
        self.assertEqual(mkt.llm_service.model, "qwen/qwen3.6-27b")
        self.assertEqual(news.llm_service.model, "qwen/qwen3.8-27b")

        risk_service = risk.llm_service or LLMService(model="risk")
        self.assertEqual(risk_service.model, "qwen/qwen3.8-27b")

        port_service = port.llm_service or LLMService(model="portfolio")
        self.assertEqual(port_service.model, "qwen/qwen3.8-27b")

        # synthesis llm_service is bound generate method
        syn_model = syn.llm_service.__self__.model
        self.assertEqual(syn_model, "qwen/qwen3.8-27b")