from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.ai.exceptions import LLMError
from apps.ai.services.llm_service import LLMService
from apps.ai.services.token_budget import (
    LLMUsage,
    TokenBudgetExceededError,
    TokenBudgetManager,
    get_default_token_budget_manager,
)


class LLMServiceTestCase(SimpleTestCase):

    @patch("apps.ai.services.llm_service.GroqProvider")
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
            messages=[
                {
                    "role": "user",
                    "content": "Tell me about Reliance.",
                }
            ],
            max_completion_tokens=1000,
        )

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_generate_passes_output_budget_and_records_usage(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        mock_provider.generate.return_value = "Response"
        mock_provider.last_usage = LLMUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            model="qwen/qwen3.6-27b",
        )

        budget_manager = TokenBudgetManager()
        service = LLMService(token_budget_manager=budget_manager)

        res = service.generate([{"role": "user", "content": "Hello"}])

        self.assertEqual(res, "Response")
        mock_provider.generate.assert_called_once_with(
            messages=[{"role": "user", "content": "Hello"}],
            max_completion_tokens=1000,
        )
        self.assertEqual(budget_manager.last_usage, mock_provider.last_usage)

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_generate_with_tools_reaches_provider_and_records_usage(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 25
        mock_response.usage.total_tokens = 40
        mock_provider.generate_with_tools.return_value = mock_response
        mock_provider.last_usage = LLMUsage(
            prompt_tokens=15,
            completion_tokens=25,
            total_tokens=40,
            model="qwen/qwen3.6-27b",
        )

        budget_manager = TokenBudgetManager()
        service = LLMService(token_budget_manager=budget_manager)
        messages = [{"role": "user", "content": "Fetch profile."}]
        tools = [{"type": "function", "function": {"name": "get_profile"}}]

        result = service.generate_with_tools(messages=messages, tools=tools)

        self.assertEqual(result, mock_response)
        mock_provider.generate_with_tools.assert_called_once_with(
            messages=messages, tools=tools, max_completion_tokens=1000
        )
        self.assertEqual(
            budget_manager.last_usage,
            LLMUsage(
                prompt_tokens=15,
                completion_tokens=25,
                total_tokens=40,
                model="qwen/qwen3.6-27b",
            ),
        )

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_missing_provider_usage_does_not_fail_request(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        mock_provider.generate.return_value = "Response without usage"
        mock_provider.last_usage = None

        budget_manager = TokenBudgetManager()
        service = LLMService(token_budget_manager=budget_manager)

        res = service.generate([{"role": "user", "content": "Hi"}])
        self.assertEqual(res, "Response without usage")
        self.assertIsNone(budget_manager.last_usage)

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_oversized_generate_request_blocked_before_provider_call(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        small_budget = TokenBudgetManager(
            max_request_tokens=2000, safety_reserve_tokens=500
        )
        service = LLMService(token_budget_manager=small_budget)

        large_messages = [{"role": "user", "content": "X" * 3000}]

        with self.assertRaises(TokenBudgetExceededError):
            service.generate(large_messages)

        mock_provider.generate.assert_not_called()

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_oversized_tool_request_blocked_before_provider_call(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        small_budget = TokenBudgetManager(
            max_request_tokens=2000, safety_reserve_tokens=500
        )
        service = LLMService(token_budget_manager=small_budget)

        large_messages = [{"role": "user", "content": "X" * 3000}]
        tools = [{"type": "function", "function": {"name": "test_tool"}}]

        with self.assertRaises(TokenBudgetExceededError):
            service.generate_with_tools(messages=large_messages, tools=tools)

        mock_provider.generate_with_tools.assert_not_called()

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_requested_output_tokens_contribute_to_budget(
        self, mock_groq_provider
    ):
        tight_budget = TokenBudgetManager(
            max_request_tokens=4500, safety_reserve_tokens=0
        )
        service = LLMService(token_budget_manager=tight_budget)

        service.generate([{"role": "user", "content": "Hi"}])
        mock_groq_provider.return_value.generate.assert_called_once()

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_tool_calls_have_bounded_output_budget(
        self, mock_groq_provider
    ):
        tight_budget = TokenBudgetManager(
            max_request_tokens=800, safety_reserve_tokens=0
        )
        service = LLMService(token_budget_manager=tight_budget)

        with self.assertRaises(TokenBudgetExceededError):
            service.generate_with_tools(
                messages=[{"role": "user", "content": "hi"}], tools=[]
            )

        mock_groq_provider.return_value.generate_with_tools.assert_not_called()

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_provider_errors_retain_existing_llm_error_behavior(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        mock_provider.generate.side_effect = LLMError(
            "Groq provider request failed: 500 Internal Server Error"
        )

        service = LLMService()

        with self.assertRaises(LLMError) as ctx:
            service.generate([{"role": "user", "content": "Test"}])

        self.assertIn("Groq provider request failed", str(ctx.exception))

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
        s1 = LLMService()
        s2 = LLMService(model="reasoning")
        s3 = LLMService(model="fast")
        s4 = LLMService(model="evaluation")
        s5 = LLMService(model="synthesis")
        s6 = LLMService(model="qwen/custom-model")

        self.assertEqual(s1.model, "reasoning-model")
        self.assertEqual(s2.model, "reasoning-model")
        self.assertEqual(s3.model, "fast-model")
        self.assertEqual(s4.model, "evaluation-model")
        self.assertEqual(s5.model, "synthesis-model")
        self.assertEqual(s6.model, "qwen/custom-model")

        self.assertEqual(
            mock_groq_provider.call_args_list[0].kwargs["model"],
            "reasoning-model",
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
        self.assertEqual(
            LLMService(model="qwen/custom-model").model, "qwen/custom-model"
        )

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_frozen_per_agent_model_resolution(self, mock_groq_provider):
        from apps.ai.agents.financial import FinancialAnalysisAgent
        from apps.ai.agents.market import MarketAnalysisAgent
        from apps.ai.agents.news import NewsIntelligenceAgent
        from apps.ai.agents.portfolio_optimization import (
            PortfolioOptimizationAgent,
        )
        from apps.ai.agents.risk import RiskAnalysisAgent
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

        syn_model = syn.llm_service.__self__.model
        self.assertEqual(syn_model, "qwen/qwen3.8-27b")

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_exact_six_agent_logical_model_mapping(self, mock_groq_provider):
        from apps.ai.agents.financial import FinancialAnalysisAgent
        from apps.ai.agents.market import MarketAnalysisAgent
        from apps.ai.agents.news import NewsIntelligenceAgent
        from apps.ai.agents.portfolio_optimization import (
            PortfolioOptimizationAgent,
        )
        from apps.ai.agents.risk import RiskAnalysisAgent
        from apps.ai.agents.synthesis import FinalSynthesisAgent

        fin = FinancialAnalysisAgent()
        mkt = MarketAnalysisAgent()
        news = NewsIntelligenceAgent()
        risk = RiskAnalysisAgent()
        port = PortfolioOptimizationAgent()
        syn = FinalSynthesisAgent()

        # Architectural design requirement: six-agent logical model mapping
        self.assertEqual(fin.llm_service.model, "qwen/qwen3.6-27b")
        self.assertEqual(mkt.llm_service.model, "qwen/qwen3.6-27b")
        self.assertEqual(news.llm_service.model, "qwen/qwen3.8-27b")
        self.assertEqual((risk.llm_service or LLMService(model="risk")).model, "qwen/qwen3.8-27b")
        self.assertEqual((port.llm_service or LLMService(model="portfolio")).model, "qwen/qwen3.8-27b")
        self.assertEqual(syn.llm_service.__self__.model, "qwen/qwen3.8-27b")

    def test_provider_effective_model_resolution(self):
        from apps.ai.agents.financial import FinancialAnalysisAgent
        from apps.ai.agents.market import MarketAnalysisAgent
        from apps.ai.agents.news import NewsIntelligenceAgent
        from apps.ai.agents.portfolio_optimization import (
            PortfolioOptimizationAgent,
        )
        from apps.ai.agents.risk import RiskAnalysisAgent
        from apps.ai.agents.synthesis import FinalSynthesisAgent

        fin = FinancialAnalysisAgent()
        mkt = MarketAnalysisAgent()
        news = NewsIntelligenceAgent()
        risk = RiskAnalysisAgent()
        port = PortfolioOptimizationAgent()
        syn = FinalSynthesisAgent()

        # Provider effective models sent to Groq
        self.assertEqual(fin.llm_service.provider.get_effective_model(), "qwen/qwen3.8-27b")
        self.assertEqual(mkt.llm_service.provider.get_effective_model(), "qwen/qwen3.8-27b")
        self.assertEqual(news.llm_service.provider.get_effective_model(), "qwen/qwen3.8-27b")
        self.assertEqual((risk.llm_service or LLMService(model="risk")).provider.get_effective_model(), "qwen/qwen3.8-27b")
        self.assertEqual((port.llm_service or LLMService(model="portfolio")).provider.get_effective_model(), "qwen/qwen3.8-27b")
        self.assertEqual(syn.llm_service.__self__.provider.get_effective_model(), "qwen/qwen3.8-27b")

    def test_default_llm_services_share_same_token_budget_manager(self):
        s1 = LLMService()
        s2 = LLMService(model="fast")
        self.assertIs(s1.token_budget_manager, s2.token_budget_manager)
        self.assertIs(s1.token_budget_manager, get_default_token_budget_manager())

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_all_default_agents_share_same_token_budget_manager(
        self, mock_groq_provider
    ):
        from apps.ai.agents.financial import FinancialAnalysisAgent
        from apps.ai.agents.market import MarketAnalysisAgent
        from apps.ai.agents.news import NewsIntelligenceAgent
        from apps.ai.agents.portfolio_optimization import (
            PortfolioOptimizationAgent,
        )
        from apps.ai.agents.risk import RiskAnalysisAgent
        from apps.ai.agents.synthesis import FinalSynthesisAgent

        default_manager = get_default_token_budget_manager()

        fin = FinancialAnalysisAgent()
        mkt = MarketAnalysisAgent()
        news = NewsIntelligenceAgent()
        risk = RiskAnalysisAgent()
        port = PortfolioOptimizationAgent()
        syn = FinalSynthesisAgent()

        self.assertIs(fin.llm_service.token_budget_manager, default_manager)
        self.assertIs(mkt.llm_service.token_budget_manager, default_manager)
        self.assertIs(news.llm_service.token_budget_manager, default_manager)

        risk_service = risk.llm_service or LLMService(model="risk")
        self.assertIs(risk_service.token_budget_manager, default_manager)

        port_service = port.llm_service or LLMService(model="portfolio")
        self.assertIs(port_service.token_budget_manager, default_manager)

        syn_service = syn.llm_service.__self__
        self.assertIs(syn_service.token_budget_manager, default_manager)

    def test_explicit_injected_token_budget_manager_remains_isolated(self):
        custom_manager = TokenBudgetManager()
        service = LLMService(token_budget_manager=custom_manager)
        default_manager = get_default_token_budget_manager()

        self.assertIs(service.token_budget_manager, custom_manager)
        self.assertIsNot(service.token_budget_manager, default_manager)

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_token_usage_recorded_in_one_service_visible_in_another_default_service(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        mock_provider.generate.return_value = "Result"
        mock_provider.last_usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model="qwen/qwen3.6-27b",
        )

        s1 = LLMService()
        s2 = LLMService(model="fast")

        s1.generate([{"role": "user", "content": "Test"}])

        self.assertEqual(
            s2.token_budget_manager.last_usage, mock_provider.last_usage
        )

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_generate_accepts_and_forwards_max_completion_tokens(
        self, mock_groq_provider
    ):
        mock_provider = mock_groq_provider.return_value
        mock_provider.generate.return_value = "Response"
        mock_provider.last_usage = None

        mock_manager = MagicMock()
        service = LLMService(token_budget_manager=mock_manager)

        messages = [{"role": "user", "content": "Hello"}]
        result = service.generate(messages, max_completion_tokens=512)

        self.assertEqual(result, "Response")
        mock_manager.validate_request_budget.assert_called_once_with(
            messages=messages,
            max_output_tokens=512,
            tools=None,
        )
        mock_provider.generate.assert_called_once_with(
            messages=messages,
            max_completion_tokens=512,
        )

    @patch("apps.ai.services.llm_service.GroqProvider")
    def test_output_token_ceiling_enforced(self, mock_groq_provider):
        mock_provider = mock_groq_provider.return_value
        mock_provider.generate.return_value = "Response"
        mock_provider.last_usage = None

        mock_manager = MagicMock()
        service = LLMService(token_budget_manager=mock_manager)
        messages = [{"role": "user", "content": "Hello"}]

        # 1. Default generation (no explicit argument) is capped at 1000
        service.generate(messages)
        mock_manager.validate_request_budget.assert_called_with(
            messages=messages,
            max_output_tokens=1000,
            tools=None,
        )
        mock_provider.generate.assert_called_with(
            messages=messages,
            max_completion_tokens=1000,
        )

        mock_manager.reset_mock()
        mock_provider.reset_mock()

        # 2. Explicit 4096 is capped to 1000
        service.generate(messages, max_completion_tokens=4096)
        mock_manager.validate_request_budget.assert_called_with(
            messages=messages,
            max_output_tokens=1000,
            tools=None,
        )
        mock_provider.generate.assert_called_with(
            messages=messages,
            max_completion_tokens=1000,
        )

        mock_manager.reset_mock()
        mock_provider.reset_mock()

        # 3. Explicit 512 remains 512
        service.generate(messages, max_completion_tokens=512)
        mock_manager.validate_request_budget.assert_called_with(
            messages=messages,
            max_output_tokens=512,
            tools=None,
        )
        mock_provider.generate.assert_called_with(
            messages=messages,
            max_completion_tokens=512,
        )