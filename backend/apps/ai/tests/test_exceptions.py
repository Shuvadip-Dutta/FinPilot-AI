from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from groq import APIConnectionError

from apps.ai.agents.financial import FinancialAnalysisAgent
from apps.ai.evaluation.evaluator import FinanceModelEvaluator
from apps.ai.evaluation.schemas import EvaluationCase
from apps.ai.exceptions import (
    AIError,
    LLMError,
    RAGError,
    ToolExecutionError,
    WorkflowError,
)
from apps.ai.graph.workflow import ResearchWorkflow
from apps.ai.rag.retriever import Retriever
from apps.ai.services.agent_service import AgentService
from apps.ai.services.providers.groq import GroqProvider
from apps.ai.services.schemas import AgentResult


class ReliabilityExceptionTestCase(SimpleTestCase):

    def test_exception_hierarchy(self):
        self.assertTrue(issubclass(LLMError, AIError))
        self.assertTrue(issubclass(ToolExecutionError, AIError))
        self.assertTrue(issubclass(WorkflowError, AIError))
        self.assertTrue(issubclass(RAGError, AIError))

    @patch("apps.ai.services.providers.groq.Groq")
    def test_groq_operational_failure_becomes_llm_error(self, mock_groq):
        mock_client = mock_groq.return_value
        mock_client.chat.completions.create.side_effect = APIConnectionError(
            request=MagicMock(),
        )

        provider = GroqProvider()

        with self.assertRaises(LLMError):
            provider.generate([{"role": "user", "content": "Hello"}])

    @patch("apps.ai.services.agent_service.LLMService")
    def test_malformed_tool_arguments_become_tool_execution_error(self, mock_llm):
        tool_call = SimpleNamespace(
            id="call_invalid",
            function=SimpleNamespace(
                name="get_market_data",
                arguments="{not valid json}",
            ),
        )
        response = MagicMock()
        response.choices[0].message.tool_calls = [tool_call]
        response.choices[0].message.content = None
        mock_llm.return_value.generate_with_tools.return_value = response

        service = AgentService()

        with self.assertRaises(ToolExecutionError) as context:
            service.run("What is the price of RELIANCE?")

        self.assertIn("Malformed arguments", str(context.exception))

    def test_financial_agent_does_not_swallow_programming_error(self):
        def programming_error(**kwargs):
            raise RuntimeError("Unexpected defect")

        agent = FinancialAnalysisAgent(
            financials_tool=programming_error,
            key_metrics_tool=lambda **kwargs: {"metrics": []},
            ticker="RELIANCE",
        )

        with self.assertRaises(RuntimeError):
            agent.run("Analyze RELIANCE financials.")

    def test_financial_agent_handles_expected_provider_failure(self):
        def provider_error(**kwargs):
            raise ValueError("Financial provider unavailable")

        agent = FinancialAnalysisAgent(
            financials_tool=provider_error,
            key_metrics_tool=lambda **kwargs: {"metrics": []},
            ticker="RELIANCE",
        )

        result = agent.run("Analyze RELIANCE financials.")

        self.assertIn("Financial provider unavailable", result.response)

    def test_workflow_records_expected_operational_failure(self):
        router = MagicMock()
        router.route.return_value = "financial"
        financial = MagicMock()
        financial.run.side_effect = ToolExecutionError("Tool unavailable")
        workflow = ResearchWorkflow(
            router=router,
            financial_agent=financial,
            market_agent=MagicMock(),
            news_agent=MagicMock(),
        )

        state = workflow.run("Show RELIANCE revenue.")

        self.assertEqual(state.errors, ["financial: Tool unavailable"])

    def test_workflow_does_not_swallow_programming_error(self):
        router = MagicMock()
        router.route.return_value = "financial"
        financial = MagicMock()
        financial.run.side_effect = RuntimeError("Unexpected defect")
        workflow = ResearchWorkflow(
            router=router,
            financial_agent=financial,
            market_agent=MagicMock(),
            news_agent=MagicMock(),
        )

        with self.assertRaises(RuntimeError):
            workflow.run("Show RELIANCE revenue.")

    def test_rag_operational_failure_becomes_rag_error(self):
        provider = MagicMock()
        provider.embed.side_effect = ValueError("Embedding unavailable")
        store = MagicMock()
        retriever = Retriever(provider, store)

        with self.assertRaises(RAGError) as context:
            retriever.retrieve("revenue")

        self.assertIn("Embedding unavailable", str(context.exception))

    def test_evaluation_handles_controlled_model_failure(self):
        case = EvaluationCase(
            case_id="finance-case",
            category="finance",
            question="What should financial analysis cover?",
            reference_answer="Revenue and profit.",
            required_concepts=["revenue", "profit"],
        )

        result = FinanceModelEvaluator(
            model=lambda messages: (_ for _ in ()).throw(LLMError("Unavailable"))
        ).evaluate_case(case)

        self.assertFalse(result.passed)
        self.assertEqual(result.score, 0.0)
        self.assertIn("Unavailable", result.response)

    def test_evaluation_does_not_swallow_programming_error(self):
        case = EvaluationCase(
            case_id="finance-case",
            category="finance",
            question="What should financial analysis cover?",
            reference_answer="Revenue and profit.",
            required_concepts=["revenue", "profit"],
        )

        def programming_error(messages):
            raise RuntimeError("Unexpected defect")

        with self.assertRaises(RuntimeError):
            FinanceModelEvaluator(programming_error).evaluate_case(case)
            
    @patch("apps.ai.services.providers.groq.Groq")
    def test_groq_tool_call_failure_becomes_llm_error(self, mock_groq):
        mock_client = mock_groq.return_value

        mock_client.chat.completions.create.side_effect = APIConnectionError(
            request=MagicMock(),
        )

        provider = GroqProvider()

        with self.assertRaises(LLMError):
            provider.generate_with_tools(
                messages=[
                    {
                        "role": "user",
                        "content": "Analyze RELIANCE.",
                    }
                ],
                tools=[],
            )
