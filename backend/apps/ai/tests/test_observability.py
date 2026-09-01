from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.observability import AIObserver


class AIObserverTestCase(SimpleTestCase):

    @patch("apps.ai.observability.logger")
    def test_graph_started_logs_expected_safe_metadata(self, mock_logger):
        observer = AIObserver()

        observer.graph_started(thread_id="thread-1", route="general")

        payload = mock_logger.info.call_args.args[0]
        self.assertEqual(payload["event"], "graph_started")
        self.assertEqual(payload["thread_id"], "thread-1")
        self.assertEqual(payload["route"], "general")
        self.assertEqual(payload["status"], "started")
        self.assertNotIn("api_key", payload)
        self.assertNotIn("password", payload)

    @patch("apps.ai.observability.logger")
    def test_graph_completed_logs_duration_and_status(self, mock_logger):
        observer = AIObserver()

        with patch("apps.ai.observability.time.perf_counter", side_effect=[10.0, 10.25]):
            observer.graph_started(thread_id="thread-1")
            observer.graph_completed(thread_id="thread-1")

        payload = mock_logger.info.call_args_list[-1].args[0]
        self.assertEqual(payload["event"], "graph_completed")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["duration_ms"], 250.0)

    @patch("apps.ai.observability.logger")
    def test_node_started_logs_node_name(self, mock_logger):
        observer = AIObserver()

        observer.node_started(thread_id="thread-1", node="financial", route="financial")

        payload = mock_logger.info.call_args.args[0]
        self.assertEqual(payload["event"], "node_started")
        self.assertEqual(payload["node"], "financial")
        self.assertEqual(payload["route"], "financial")

    @patch("apps.ai.observability.logger")
    def test_node_completed_logs_duration_and_status(self, mock_logger):
        observer = AIObserver()

        with patch("apps.ai.observability.time.perf_counter", side_effect=[20.0, 20.1]):
            observer.node_started(thread_id="thread-1", node="market")
            observer.node_completed(thread_id="thread-1", node="market")

        payload = mock_logger.info.call_args_list[-1].args[0]
        self.assertEqual(payload["event"], "node_completed")
        self.assertEqual(payload["node"], "market")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["duration_ms"], 100.0)

    @patch("apps.ai.observability.logger")
    def test_node_failed_logs_error_type_and_message(self, mock_logger):
        observer = AIObserver()

        with patch("apps.ai.observability.time.perf_counter", side_effect=[30.0, 30.2]):
            observer.node_started(thread_id="thread-1", node="news")
            observer.node_failed(
                thread_id="thread-1",
                node="news",
                route="news",
                error_type="ValueError",
                error_message="News unavailable",
            )

        payload = mock_logger.error.call_args.args[0]
        self.assertEqual(payload["event"], "node_failed")
        self.assertEqual(payload["error_type"], "ValueError")
        self.assertEqual(payload["error_message"], "News unavailable")

    @patch("apps.ai.observability.logger")
    def test_no_sensitive_fields_are_logged(self, mock_logger):
        observer = AIObserver()

        observer.graph_started(
            thread_id="thread-1",
            route="general",
            password="super-secret",
            api_key="abc",
            authorization="Bearer token",
            raw_prompt="full prompt",
            tool_args={"ticker": "RELIANCE"},
        )

        payload = mock_logger.info.call_args.args[0]
        self.assertNotIn("password", payload)
        self.assertNotIn("api_key", payload)
        self.assertNotIn("authorization", payload)
        self.assertNotIn("raw_prompt", payload)
        self.assertNotIn("tool_args", payload)

    @patch("apps.ai.observability.logger")
    def test_observer_does_not_swallow_exceptions(self, mock_logger):
        observer = AIObserver()

        def run_and_observe():
            try:
                raise RuntimeError("boom")
            except RuntimeError as exc:
                observer.graph_failed(
                    thread_id="thread-1",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                raise

        with self.assertRaises(RuntimeError):
            run_and_observe()

        exception_payload = mock_logger.exception.call_args.args[0]
        self.assertEqual(exception_payload["event"], "graph_failed")
        self.assertEqual(exception_payload["error_type"], "RuntimeError")
        self.assertEqual(exception_payload["error_message"], "boom")
        self.assertFalse(mock_logger.error.called)

    @patch("apps.ai.observability.logger")
    def test_repeated_lifecycle_events_are_deterministic(self, mock_logger):
        first = AIObserver()
        second = AIObserver()

        with patch("apps.ai.observability.time.perf_counter", side_effect=[1.0, 1.2, 2.0, 2.1]):
            first.graph_started(thread_id="same", route="general")
            first.graph_completed(thread_id="same")
            second.graph_started(thread_id="same", route="general")
            second.graph_completed(thread_id="same")

        first_payload = mock_logger.info.call_args_list[0].args[0]
        second_payload = mock_logger.info.call_args_list[2].args[0]
        self.assertEqual(first_payload, second_payload)
        self.assertEqual(first_payload["event"], "graph_started")

    @patch("apps.ai.observability.logger")
    def test_real_workflow_emits_graph_and_node_lifecycle(self, mock_logger):
        router = MagicMock()
        router.route.return_value = "market"

        financial = MagicMock()
        financial.run.return_value = MagicMock(model_dump=lambda: {"response": "Financial result"})

        market = MagicMock()
        market.run.return_value = MagicMock(model_dump=lambda: {"response": "Market result"})

        news = MagicMock()
        news.run.return_value = MagicMock(model_dump=lambda: {"response": "News result"})

        workflow = LangGraphResearchWorkflow(
            router=router,
            financial_agent=financial,
            market_agent=market,
            news_agent=news,
            checkpointer=None,
        )

        workflow.run("What is the RELIANCE price?", thread_id="thread-42")

        events = [call.args[0]["event"] for call in mock_logger.info.call_args_list]
        self.assertIn("graph_started", events)
        self.assertIn("graph_completed", events)
        self.assertIn("node_started", events)
        self.assertIn("node_completed", events)

        started_payload = next(call.args[0] for call in mock_logger.info.call_args_list if call.args[0].get("event") == "graph_started")
        completed_payload = next(call.args[0] for call in mock_logger.info.call_args_list if call.args[0].get("event") == "graph_completed")
        self.assertEqual(started_payload["thread_id"], "thread-42")
        self.assertEqual(completed_payload["thread_id"], "thread-42")

    @patch("apps.ai.observability.logger")
    def test_error_message_redacts_sensitive_fields(self, mock_logger):
        observer = AIObserver()
        observer.graph_failed(
            thread_id="thread-99",
            route="market",
            error_type="RuntimeError",
            error_message="Authorization: Bearer abc123 | api_key=top-secret | password=letmein",
        )

        payload = mock_logger.error.call_args.args[0]
        self.assertIn("[REDACTED]", payload["error_message"])
        self.assertNotIn("abc123", payload["error_message"])
        self.assertNotIn("top-secret", payload["error_message"])
        self.assertNotIn("letmein", payload["error_message"])


class LangGraphObservabilityIntegrationTestCase(SimpleTestCase):

    @staticmethod
    def _make_agent(response="result"):
        agent = MagicMock()
        agent.run.return_value = MagicMock(model_dump=lambda: {"response": response})
        return agent

    def test_graph_lifecycle_events_are_emitted(self):
        router = MagicMock()
        router.route.return_value = "market"
        workflow = __import__("apps.ai.graph.langgraph_workflow", fromlist=["LangGraphResearchWorkflow"]).LangGraphResearchWorkflow(
            router=router,
            financial_agent=self._make_agent(),
            market_agent=self._make_agent("market result"),
            news_agent=self._make_agent(),
            checkpointer=None,
        )

        workflow.observer = MagicMock()
        workflow.run("What is the RELIANCE price?", thread_id="thread-42")

        workflow.observer.graph_started.assert_called_once_with(thread_id="thread-42", route="market")
        workflow.observer.graph_completed.assert_called_once()
        self.assertEqual(workflow.observer.graph_completed.call_args.kwargs["thread_id"], "thread-42")

    def test_node_failure_records_observability_information(self):
        router = MagicMock()
        router.route.return_value = "financial"
        financial = MagicMock()
        financial.run.side_effect = ValueError("Financial unavailable")
        workflow = __import__("apps.ai.graph.langgraph_workflow", fromlist=["LangGraphResearchWorkflow"]).LangGraphResearchWorkflow(
            router=router,
            financial_agent=financial,
            market_agent=self._make_agent(),
            news_agent=self._make_agent(),
            checkpointer=None,
        )

        workflow.observer = MagicMock()
        state = workflow.run("Show revenue for RELIANCE.", thread_id="thread-99")

        self.assertIn("financial: Financial unavailable", state.errors)
        workflow.observer.node_failed.assert_called()
        self.assertEqual(workflow.observer.node_failed.call_args.kwargs["thread_id"], "thread-99")

    def test_runtime_error_still_propagates(self):
        router = MagicMock()
        router.route.return_value = "market"
        market = MagicMock()
        market.run.side_effect = RuntimeError("unexpected bug")
        workflow = __import__("apps.ai.graph.langgraph_workflow", fromlist=["LangGraphResearchWorkflow"]).LangGraphResearchWorkflow(
            router=router,
            financial_agent=self._make_agent(),
            market_agent=market,
            news_agent=self._make_agent(),
            checkpointer=None,
        )

        workflow.observer = MagicMock()
        with self.assertRaises(RuntimeError):
            workflow.run("What is the RELIANCE price?", thread_id="thread-err")

        workflow.observer.graph_failed.assert_called_once()
        self.assertEqual(workflow.observer.graph_failed.call_args.kwargs["thread_id"], "thread-err")
