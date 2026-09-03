import json
import sys
from unittest.mock import MagicMock

from django.test import TestCase
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
from apps.ai.graph.router import WorkflowRouter
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult
from apps.research.models import ResearchEvidence, ResearchSession
from apps.research.services.session_service import ResearchSessionService


def _verification_checkpointer():
    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            (
                "apps.ai.services.schemas",
                "AgentResult",
            ),
        ],
    )
    return MemorySaver(serde=serializer)


class Phase9PersistenceVerificationTestCase(TestCase):

    def test_verify_phase9_persistence_e2e(self):
        report_lines = []
        report_lines.append("\nPHASE 9.5 VERIFICATION")
        report_lines.append("======================")
        report_lines.append("SUCCESS PATH")

        all_passed = True

        def record_result(label, passed, detail=""):
            nonlocal all_passed
            if passed:
                report_lines.append(f"[PASS] {label}")
            else:
                all_passed = False
                report_lines.append(f"[FAIL] {label}: {detail}")

        # Mock agent responses
        financial_agent = MagicMock()
        financial_agent.run.return_value = AgentResult(
            response="RELIANCE financial ratio metrics strong. Debt-to-equity is low.",
            tools_used=["get_financial_metrics"],
            data={"revenue": 500000000, "debt_equity": 0.35},
        )

        market_agent = MagicMock()
        market_agent.run.return_value = AgentResult(
            response="RELIANCE share price trading at 2950.50 INR.",
            tools_used=["get_quote_data"],
            data={"close": 2950.50},
        )

        news_agent = MagicMock()
        news_agent.run.return_value = AgentResult(
            response="Positive news coverage on RELIANCE green energy expansion.",
            tools_used=["get_news"],
            data={"sentiment": "POSITIVE"},
        )

        risk_agent = MagicMock()
        risk_agent.run.return_value = AgentResult(
            response="Risk rating: LOW. Stable operating cash flows.",
            tools_used=["assess_risk"],
            data={"risk_score": 0.20},
        )

        synthesis_agent = MagicMock()
        synthesis_agent.run.return_value = AgentResult(
            response="RELIANCE demonstrates strong financial stability with favorable market momentum and low risk.",
            tools_used=["llm_synthesis"],
            data={"recommendation": "BUY"},
        )

        router = WorkflowRouter()

        workflow = LangGraphResearchWorkflow(
            router=router,
            financial_agent=financial_agent,
            market_agent=market_agent,
            news_agent=news_agent,
            risk_agent=risk_agent,
            synthesis_agent=synthesis_agent,
            checkpointer=_verification_checkpointer(),
        )

        user_message = "Evaluate RELIANCE financial stability and recent news."
        ticker = "RELIANCE"
        market = "INDIA"
        thread_id = "phase9-e2e-verification-thread"

        state = workflow.run(
            user_message=user_message,
            ticker=ticker,
            market=market,
            thread_id=thread_id,
        )

        self.assertIsInstance(state, AgentState)

        # 1. Query ResearchSession
        try:
            session = ResearchSession.objects.get(thread_id=thread_id)
            record_result("session exists", True)
        except ResearchSession.DoesNotExist:
            session = None
            record_result("session exists", False, "ResearchSession row not found in database")

        if session:
            record_result("thread_id", session.thread_id == thread_id, f"Expected {thread_id}, got {session.thread_id}")
            record_result("ticker", session.ticker == ticker, f"Expected {ticker}, got {session.ticker}")
            record_result("market", session.market == market, f"Expected {market}, got {session.market}")
            record_result("route", session.route == state.route, f"Expected {state.route}, got {session.route}")
            record_result("status", session.status == "COMPLETED", f"Expected COMPLETED, got {session.status}")
            record_result("latency", session.latency_ms is not None and session.latency_ms > 0, f"latency_ms: {session.latency_ms}")
            
            expected_synthesis = "RELIANCE demonstrates strong financial stability with favorable market momentum and low risk."
            record_result("final synthesis", session.final_synthesis == expected_synthesis, f"Got: {session.final_synthesis}")

            evidence_items = ResearchEvidence.objects.filter(session=session)
            executed_agent_count = len(state.results)
            record_result("evidence count", evidence_items.count() == executed_agent_count, f"Expected {executed_agent_count}, got {evidence_items.count()}")

            has_tools_and_data = True
            for ev in evidence_items:
                if ev.agent_name in state.results:
                    orig_res = state.results[ev.agent_name]
                    if isinstance(orig_res, dict):
                        orig_tools = orig_res.get("tools_used", [])
                        orig_data = orig_res.get("data")
                    else:
                        orig_tools = getattr(orig_res, "tools_used", [])
                        orig_data = getattr(orig_res, "data", None)

                    if orig_tools != ev.tools_used:
                        has_tools_and_data = False
                    if orig_data and orig_data != ev.structured_data:
                        has_tools_and_data = False
            record_result("evidence payloads", has_tools_and_data, "Mismatch in tools_used or structured_data payloads")

            # Chatbot context verification
            context = ResearchSessionService.build_chatbot_context(session.id)
            context_valid = (
                isinstance(context, dict)
                and context.get("session_id") == str(session.id)
                and context.get("thread_id") == thread_id
                and context.get("ticker") == ticker
                and context.get("status") == "COMPLETED"
                and context.get("final_synthesis") == expected_synthesis
                and len(context.get("evidence", {})) == executed_agent_count
            )
            record_result("chatbot context", context_valid, f"Invalid context returned: {context}")

            # Print compact sample of chatbot context to stdout
            compact_sample = {
                "session_id": context.get("session_id"),
                "thread_id": context.get("thread_id"),
                "ticker": context.get("ticker"),
                "status": context.get("status"),
                "final_synthesis": context.get("final_synthesis"),
                "evidence_agents": list(context.get("evidence", {}).keys()),
            }
            sys.stderr.write("\nCHATBOT CONTEXT SAMPLE:\n")
            sys.stderr.write(json.dumps(compact_sample, indent=2) + "\n\n")
        else:
            for key in ["thread_id", "ticker", "market", "route", "status", "latency", "final synthesis", "evidence count", "evidence payloads", "chatbot context"]:
                record_result(key, False, "Session object was not created")

        # FAILURE PATH VERIFICATION
        report_lines.append("\nFAILURE PATH")
        fail_thread_id = "phase9-e2e-failure-thread"
        failing_news_agent = MagicMock()
        failing_news_agent.run.side_effect = RuntimeError("Simulated API failure in Market agent")

        failing_workflow = LangGraphResearchWorkflow(
            router=WorkflowRouter(),
            financial_agent=financial_agent,
            market_agent=market_agent,
            news_agent=failing_news_agent,
            risk_agent=risk_agent,
            synthesis_agent=synthesis_agent,
            checkpointer=_verification_checkpointer(),
        )

        exception_propagated = False
        try:
            failing_workflow.run(
                user_message="Evaluate RELIANCE financial stability and recent news.",
                ticker="RELIANCE",
                market="INDIA",
                thread_id=fail_thread_id,
            )
        except RuntimeError as err:
            if str(err) == "Simulated API failure in Market agent":
                exception_propagated = True

        record_result("exception propagated", exception_propagated, "RuntimeError was not propagated correctly")

        try:
            failed_session = ResearchSession.objects.get(thread_id=fail_thread_id)
            record_result("session created", True)
            record_result("status FAILED", failed_session.status == "FAILED", f"Expected FAILED, got {failed_session.status}")
        except ResearchSession.DoesNotExist:
            record_result("session created", False, "Failed session row was not created in database")
            record_result("status FAILED", False, "Failed session row missing")

        report_lines.append("")
        if all_passed:
            report_lines.append("FINAL RESULT: PASS")
        else:
            report_lines.append("FINAL RESULT: FAIL")

        report_text = "\n".join(report_lines)
        sys.stderr.write(report_text + "\n")

        # Assert all checks passed so Django test framework counts it as PASS
        self.assertTrue(all_passed, "Phase 9.5 E2E Verification failed. See report above for details.")
