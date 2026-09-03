import uuid

from django.test import TestCase

from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult
from apps.research.models import ResearchEvidence, ResearchSession
from apps.research.services.session_service import ResearchSessionService


class ResearchSessionServiceTestCase(TestCase):

    def test_create_session(self):
        session = ResearchSessionService.create_session(
            user_message="Analyze RELIANCE financial performance",
            ticker="RELIANCE",
            market="INDIA",
            route="financial",
            thread_id="thread-123",
        )

        self.assertIsNotNone(session.id)
        self.assertEqual(session.user_message, "Analyze RELIANCE financial performance")
        self.assertEqual(session.ticker, "RELIANCE")
        self.assertEqual(session.market, "INDIA")
        self.assertEqual(session.route, "financial")
        self.assertEqual(session.thread_id, "thread-123")
        self.assertEqual(session.status, "COMPLETED")

    def test_save_workflow_result_multiple_agents(self):
        session = ResearchSessionService.create_session(
            user_message="Full analysis for TCS",
            ticker="TCS",
            market="INDIA",
            route="financial",
            thread_id="thread-456",
        )

        state = AgentState(
            user_message="Full analysis for TCS",
            ticker="TCS",
            market="INDIA",
            route="financial",
            results={
                "financial": AgentResult(
                    response="TCS reported strong quarterly revenue growth.",
                    tools_used=["get_financial_metrics"],
                    data={"revenue": 50000, "currency": "INR"},
                ),
                "market": AgentResult(
                    response="TCS share price is trading near 52-week high.",
                    tools_used=["get_quote_data"],
                    data={"last_price": 4120.50},
                ),
                "synthesis": AgentResult(
                    response="Overall investment recommendation: Buy TCS.",
                    tools_used=[],
                    data=None,
                ),
            },
        )

        updated_session = ResearchSessionService.save_workflow_result(
            session_id=session.id,
            agent_state=state,
            latency_ms=1250.5,
        )

        self.assertEqual(updated_session.final_synthesis, "Overall investment recommendation: Buy TCS.")
        self.assertEqual(updated_session.latency_ms, 1250.5)

        # Check preserved fields
        self.assertEqual(updated_session.user_message, "Full analysis for TCS")
        self.assertEqual(updated_session.ticker, "TCS")
        self.assertEqual(updated_session.market, "INDIA")
        self.assertEqual(updated_session.route, "financial")
        self.assertEqual(updated_session.thread_id, "thread-456")

        evidence = ResearchEvidence.objects.filter(session=session).order_by("agent_name")
        self.assertEqual(evidence.count(), 3)

    def test_final_synthesis_persistence(self):
        session = ResearchSessionService.create_session(
            user_message="Synthesize risk profile",
            ticker="INFY",
        )

        state = AgentState(
            user_message="Synthesize risk profile",
            ticker="INFY",
            results={
                "synthesis": AgentResult(
                    response="INFY shows moderate technology sector risk.",
                    tools_used=[],
                )
            },
        )

        saved = ResearchSessionService.save_workflow_result(session.id, state)
        self.assertEqual(saved.final_synthesis, "INFY shows moderate technology sector risk.")

    def test_structured_data_and_tools_used_preservation(self):
        session = ResearchSessionService.create_session(
            user_message="Check market data",
            ticker="AAPL",
        )

        state = AgentState(
            user_message="Check market data",
            ticker="AAPL",
            results={
                "market": AgentResult(
                    response="Apple market quote retrieved.",
                    tools_used=["get_us_market_quote", "calculate_ma"],
                    data={"close": 220.5, "pe_ratio": 33.2},
                )
            },
        )

        ResearchSessionService.save_workflow_result(session.id, state)

        evidence = ResearchSessionService.get_evidence(session.id)
        self.assertEqual(len(evidence), 1)

        market_item = evidence[0]
        self.assertEqual(market_item.agent_name, "market")
        self.assertEqual(market_item.response, "Apple market quote retrieved.")
        self.assertEqual(market_item.tools_used, ["get_us_market_quote", "calculate_ma"])
        self.assertEqual(market_item.structured_data, {"close": 220.5, "pe_ratio": 33.2})

    def test_get_evidence(self):
        session = ResearchSessionService.create_session(user_message="Multi agent test")

        ResearchEvidence.objects.create(
            session=session,
            agent_name="financial",
            response="Financial evidence",
            tools_used=["tool_a"],
        )
        ResearchEvidence.objects.create(
            session=session,
            agent_name="news",
            response="News evidence",
            tools_used=["tool_b"],
        )

        evidence = ResearchSessionService.get_evidence(session.id)
        self.assertEqual(len(evidence), 2)
        agent_names = [e.agent_name for e in evidence]
        self.assertIn("financial", agent_names)
        self.assertIn("news", agent_names)

    def test_get_recent_sessions_for_ticker(self):
        ResearchSessionService.create_session(user_message="Query 1", ticker="RELIANCE")
        ResearchSessionService.create_session(user_message="Query 2", ticker="RELIANCE")
        ResearchSessionService.create_session(user_message="Query 3", ticker="TCS")

        reliance_sessions = ResearchSessionService.get_recent_sessions_for_ticker("RELIANCE")
        self.assertEqual(len(reliance_sessions), 2)
        for s in reliance_sessions:
            self.assertEqual(s.ticker, "RELIANCE")

    def test_build_chatbot_context(self):
        session = ResearchSessionService.create_session(
            user_message="Analyze portfolio risk",
            ticker="TCS",
            market="INDIA",
            route="risk",
            thread_id="t-99",
        )

        state = AgentState(
            user_message="Analyze portfolio risk",
            results={
                "risk": AgentResult(
                    response="Portfolio risk score is 0.42.",
                    tools_used=["assess_risk"],
                    data={"score": 0.42, "level": "LOW"},
                ),
                "synthesis": AgentResult(
                    response="Low risk portfolio confirmed.",
                    tools_used=[],
                ),
            },
        )

        ResearchSessionService.save_workflow_result(session.id, state, latency_ms=450.0)

        context = ResearchSessionService.build_chatbot_context(session.id)

        self.assertEqual(context["session_id"], str(session.id))
        self.assertEqual(context["thread_id"], "t-99")
        self.assertEqual(context["ticker"], "TCS")
        self.assertEqual(context["market"], "INDIA")
        self.assertEqual(context["route"], "risk")
        self.assertEqual(context["final_synthesis"], "Low risk portfolio confirmed.")
        self.assertEqual(context["latency_ms"], 450.0)
        self.assertIn("risk", context["evidence"])
        self.assertEqual(
            context["evidence"]["risk"]["structured_data"],
            {"score": 0.42, "level": "LOW"},
        )

    def test_invalid_session_handling(self):
        non_existent_uuid = uuid.uuid4()
        with self.assertRaises(ResearchSession.DoesNotExist):
            ResearchSessionService.get_session(non_existent_uuid)

        with self.assertRaises(ResearchSession.DoesNotExist):
            ResearchSessionService.get_session("invalid-uuid-string")

        with self.assertRaises(ResearchSession.DoesNotExist):
            ResearchSessionService.save_workflow_result(
                non_existent_uuid,
                AgentState(user_message="test"),
            )

        with self.assertRaises(ResearchSession.DoesNotExist):
            ResearchSessionService.get_evidence(non_existent_uuid)

        with self.assertRaises(ResearchSession.DoesNotExist):
            ResearchSessionService.build_chatbot_context(non_existent_uuid)

    def test_idempotency_duplicate_save(self):
        session = ResearchSessionService.create_session(
            user_message="Idempotency test",
            ticker="TCS",
        )

        state_v1 = AgentState(
            user_message="Idempotency test",
            results={
                "financial": AgentResult(
                    response="Version 1 financial response",
                    tools_used=["tool_v1"],
                    data={"metric": 100},
                )
            },
        )

        ResearchSessionService.save_workflow_result(session.id, state_v1)
        self.assertEqual(ResearchEvidence.objects.filter(session=session).count(), 1)
        ev_v1 = ResearchEvidence.objects.get(session=session, agent_name="financial")
        self.assertEqual(ev_v1.response, "Version 1 financial response")

        # Save again with updated response for the same session
        state_v2 = AgentState(
            user_message="Idempotency test",
            results={
                "financial": AgentResult(
                    response="Version 2 updated financial response",
                    tools_used=["tool_v2"],
                    data={"metric": 200},
                )
            },
        )

        ResearchSessionService.save_workflow_result(session.id, state_v2)
        self.assertEqual(ResearchEvidence.objects.filter(session=session).count(), 1)
        ev_v2 = ResearchEvidence.objects.get(session=session, agent_name="financial")
        self.assertEqual(ev_v2.response, "Version 2 updated financial response")
        self.assertEqual(ev_v2.tools_used, ["tool_v2"])
        self.assertEqual(ev_v2.structured_data, {"metric": 200})

    def test_get_recent_sessions_for_ticker_status_filtering(self):
        s1 = ResearchSessionService.create_session(user_message="Msg 1", ticker="RELIANCE")
        s1.status = "COMPLETED"
        s1.save()

        s2 = ResearchSessionService.create_session(user_message="Msg 2", ticker="RELIANCE")
        s2.status = "FAILED"
        s2.save()

        s3 = ResearchSessionService.create_session(user_message="Msg 3", ticker="RELIANCE")
        s3.status = "RUNNING"
        s3.save()

        completed = ResearchSessionService.get_recent_sessions_for_ticker("RELIANCE", only_completed=True)
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].id, s1.id)

        all_sessions = ResearchSessionService.get_recent_sessions_for_ticker("RELIANCE", only_completed=False)
        self.assertEqual(len(all_sessions), 3)

    def test_get_latest_session_for_ticker(self):
        s1 = ResearchSessionService.create_session(user_message="Old", ticker="INFY")
        s1.status = "COMPLETED"
        s1.save()

        s2 = ResearchSessionService.create_session(user_message="Failed newest", ticker="INFY")
        s2.status = "FAILED"
        s2.save()

        latest_completed = ResearchSessionService.get_latest_session_for_ticker("INFY", only_completed=True)
        self.assertIsNotNone(latest_completed)
        self.assertEqual(latest_completed.id, s1.id)

        latest_overall = ResearchSessionService.get_latest_session_for_ticker("INFY", only_completed=False)
        self.assertIsNotNone(latest_overall)
        self.assertEqual(latest_overall.id, s2.id)

        non_existent = ResearchSessionService.get_latest_session_for_ticker("NONEXISTENT")
        self.assertIsNone(non_existent)

    def test_build_chatbot_context_agent_filtering(self):
        session = ResearchSessionService.create_session(user_message="Filter test", ticker="WIPRO")

        state = AgentState(
            user_message="Filter test",
            ticker="WIPRO",
            results={
                "financial": AgentResult(response="Financial data", tools_used=["f_tool"]),
                "market": AgentResult(response="Market data", tools_used=["m_tool"]),
                "news": AgentResult(response="News data", tools_used=["n_tool"]),
            },
        )
        ResearchSessionService.save_workflow_result(session.id, state)

        # All agents (default)
        all_ctx = ResearchSessionService.build_chatbot_context(session.id)
        self.assertEqual(set(all_ctx["evidence"].keys()), {"financial", "market", "news"})

        # Single agent filter
        fin_ctx = ResearchSessionService.build_chatbot_context(session.id, agent_names=["financial"])
        self.assertEqual(set(fin_ctx["evidence"].keys()), {"financial"})
        self.assertEqual(fin_ctx["evidence"]["financial"]["response"], "Financial data")

        # Multi-agent filter
        multi_ctx = ResearchSessionService.build_chatbot_context(session.id, agent_names=["financial", "news"])
        self.assertEqual(set(multi_ctx["evidence"].keys()), {"financial", "news"})

    def test_build_multi_session_context(self):
        s1 = ResearchSessionService.create_session(user_message="Session 1", ticker="RELIANCE")
        state1 = AgentState(
            user_message="Session 1",
            results={
                "financial": AgentResult(response="Fin 1", tools_used=["t1"]),
                "news": AgentResult(response="News 1", tools_used=["t2"]),
            },
        )
        ResearchSessionService.save_workflow_result(s1.id, state1)

        s2 = ResearchSessionService.create_session(user_message="Session 2", ticker="RELIANCE")
        state2 = AgentState(
            user_message="Session 2",
            results={
                "financial": AgentResult(response="Fin 2", tools_used=["t1"]),
            },
        )
        ResearchSessionService.save_workflow_result(s2.id, state2)

        # Create session for another ticker to verify isolation
        tcs_s = ResearchSessionService.create_session(user_message="TCS Session", ticker="TCS")
        tcs_state = AgentState(
            user_message="TCS Session",
            results={"financial": AgentResult(response="TCS Fin", tools_used=[])},
        )
        ResearchSessionService.save_workflow_result(tcs_s.id, tcs_state)

        # Multi-session context for RELIANCE with limit 2 and financial agent filter
        multi_ctx = ResearchSessionService.build_multi_session_context(
            ticker="RELIANCE",
            limit=2,
            agent_names=["financial"],
            only_completed=True,
        )

        self.assertEqual(multi_ctx["ticker"], "RELIANCE")
        self.assertEqual(multi_ctx["session_count"], 2)
        self.assertEqual(len(multi_ctx["sessions"]), 2)

        # Ordered newest first (s2 created after s1)
        self.assertEqual(multi_ctx["sessions"][0]["session_id"], str(s2.id))
        self.assertEqual(multi_ctx["sessions"][1]["session_id"], str(s1.id))

        # Check evidence filtering inside multi-session context
        self.assertEqual(set(multi_ctx["sessions"][0]["evidence"].keys()), {"financial"})
        self.assertEqual(multi_ctx["sessions"][0]["evidence"]["financial"]["response"], "Fin 2")
        self.assertEqual(multi_ctx["sessions"][1]["evidence"]["financial"]["response"], "Fin 1")

        # Verify TCS is not included anywhere
        session_ids = [s["session_id"] for s in multi_ctx["sessions"]]
        self.assertNotIn(str(tcs_s.id), session_ids)
