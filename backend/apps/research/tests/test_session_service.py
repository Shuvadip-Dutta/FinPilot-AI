from datetime import timedelta
import json
import uuid

from django.contrib.auth.models import User
from django.test import TestCase

from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult
from apps.research.models import ResearchEvidence, ResearchSession
from apps.research.services.session_service import ResearchSessionService


class ResearchSessionServiceTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.user1 = User.objects.create_user(username="user1", email="user1@example.com", password="password1")
        self.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="password2")

    def test_create_session(self):
        session = ResearchSessionService.create_session(
            user_message="Analyze RELIANCE financial performance",
            user=self.user1,
            ticker="RELIANCE",
            market="INDIA",
            route="financial",
            thread_id="thread-123",
        )

        self.assertIsNotNone(session.id)
        self.assertEqual(session.user, self.user1)
        self.assertEqual(session.user_message, "Analyze RELIANCE financial performance")
        self.assertEqual(session.ticker, "RELIANCE")
        self.assertEqual(session.market, "INDIA")
        self.assertEqual(session.route, "financial")
        self.assertEqual(session.thread_id, "thread-123")
        self.assertEqual(session.status, "COMPLETED")

    def test_multiple_users_separate_sessions(self):
        s1 = ResearchSessionService.create_session(user_message="Msg 1", user=self.user1, ticker="RELIANCE")
        s2 = ResearchSessionService.create_session(user_message="Msg 2", user=self.user2, ticker="TCS")

        self.assertEqual(s1.user, self.user1)
        self.assertEqual(s2.user, self.user2)
        self.assertIn(s1, self.user1.research_sessions.all())
        self.assertIn(s2, self.user2.research_sessions.all())
        self.assertNotIn(s2, self.user1.research_sessions.all())

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

        ResearchSession.objects.filter(pk=s2.id).update(
            created_at=s1.created_at + timedelta(seconds=5)
        )
        s2.refresh_from_db()

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

    def test_coerce_agent_result_with_existing_data_dict(self):
        payload = {
            "response": "Financials retrieved",
            "tools_used": ["get_metrics"],
            "data": {"revenue": 50000, "ebitda": 12000},
        }
        resp, tools, structured = ResearchSessionService._coerce_agent_result(payload)
        self.assertEqual(resp, "Financials retrieved")
        self.assertEqual(tools, ["get_metrics"])
        self.assertEqual(structured, {"revenue": 50000, "ebitda": 12000})

    def test_coerce_agent_result_with_direct_structured_dict(self):
        direct_payload = {
            "pe_ratio": 22.5,
            "roe": 0.18,
            "debt_to_equity": 0.5,
        }
        resp, tools, structured = ResearchSessionService._coerce_agent_result(direct_payload)
        self.assertEqual(resp, "")
        self.assertEqual(tools, [])
        self.assertEqual(
            structured,
            {"pe_ratio": 22.5, "roe": 0.18, "debt_to_equity": 0.5},
        )

        # Direct structured payload with response and tools
        payload_with_meta = {
            "response": "Risk computed",
            "tools_used": ["calc_risk"],
            "volatility": 0.15,
            "sharpe_ratio": 1.4,
        }
        resp, tools, structured = ResearchSessionService._coerce_agent_result(payload_with_meta)
        self.assertEqual(resp, "Risk computed")
        self.assertEqual(tools, ["calc_risk"])
        self.assertEqual(structured, {"volatility": 0.15, "sharpe_ratio": 1.4})

    def test_coerce_agent_result_with_normal_response_payload(self):
        normal_payload = {
            "response": "Synthesized analysis completed.",
            "tools_used": ["search_news", "get_quote"],
        }
        resp, tools, structured = ResearchSessionService._coerce_agent_result(normal_payload)
        self.assertEqual(resp, "Synthesized analysis completed.")
        self.assertEqual(tools, ["search_news", "get_quote"])
        self.assertIsNone(structured)

    def _create_sample_risk_metrics(self):
        from apps.ai.portfolio.schemas import PortfolioRiskMetrics
        return PortfolioRiskMetrics(
            volatility=0.18,
            downside_volatility=0.12,
            sharpe_ratio=1.2,
            sortino_ratio=1.5,
            calmar_ratio=1.1,
            max_drawdown=0.10,
            max_drawdown_duration_days=35,
            var_95_historical=0.02,
            cvar_95_historical=0.03,
            annualized_return=0.15,
            cagr=0.14,
            total_period_return=0.30,
        )

    def test_coerce_agent_result_dict_containing_portfolio_risk_metrics(self):
        import json
        from apps.ai.portfolio.schemas import PortfolioRiskMetrics
        metrics = self._create_sample_risk_metrics()
        payload = {
            "current_risk": metrics,
            "optimized_risk": None,
        }
        resp, tools, structured = ResearchSessionService._coerce_agent_result(payload)
        self.assertEqual(resp, "")
        self.assertEqual(tools, [])
        self.assertIsInstance(structured, dict)
        self.assertIsInstance(structured["current_risk"], dict)
        self.assertNotIsInstance(structured["current_risk"], PortfolioRiskMetrics)
        self.assertEqual(structured["current_risk"]["volatility"], 0.18)
        self.assertEqual(structured["current_risk"]["sharpe_ratio"], 1.2)
        self.assertIsNone(structured["optimized_risk"])
        # Verify JSON serializability
        dumped = json.dumps(structured)
        self.assertIn('"volatility": 0.18', dumped)

    def test_coerce_agent_result_nested_pydantic_inside_dict(self):
        import json
        metrics = self._create_sample_risk_metrics()
        payload = {
            "analysis": {
                "nested_section": {
                    "metrics": metrics,
                    "label": "stress_test",
                }
            }
        }
        resp, tools, structured = ResearchSessionService._coerce_agent_result(payload)
        self.assertIsInstance(structured, dict)
        nested_metrics = structured["analysis"]["nested_section"]["metrics"]
        self.assertIsInstance(nested_metrics, dict)
        self.assertEqual(nested_metrics["sortino_ratio"], 1.5)
        self.assertEqual(structured["analysis"]["nested_section"]["label"], "stress_test")
        json.dumps(structured)

    def test_coerce_agent_result_pydantic_model_inside_list(self):
        import json
        metrics = self._create_sample_risk_metrics()
        payload = {
            "metrics_history": [metrics, {"label": "baseline"}],
        }
        resp, tools, structured = ResearchSessionService._coerce_agent_result(payload)
        self.assertIsInstance(structured, dict)
        self.assertIsInstance(structured["metrics_history"], list)
        self.assertIsInstance(structured["metrics_history"][0], dict)
        self.assertEqual(structured["metrics_history"][0]["calmar_ratio"], 1.1)
        self.assertEqual(structured["metrics_history"][1]["label"], "baseline")
        json.dumps(structured)

    def test_save_workflow_result_persists_jsonfield_with_risk_metrics(self):
        import json
        session = ResearchSessionService.create_session(
            user_message="Portfolio risk request",
            ticker=None,
            route="portfolio",
        )
        metrics = self._create_sample_risk_metrics()
        state = AgentState(
            user_message="Portfolio risk request",
            route="portfolio",
            results={
                "portfolio_risk": {
                    "current_risk": metrics,
                    "optimized_risk": None,
                },
                "synthesis": AgentResult(
                    response="Portfolio risk synthesis.",
                    tools_used=["calc_risk"],
                    data=None,
                ),
            },
        )

        ResearchSessionService.save_workflow_result(session.id, state)

        evidence = ResearchEvidence.objects.get(session=session, agent_name="portfolio_risk")
        self.assertIsNotNone(evidence.structured_data)
        self.assertIsInstance(evidence.structured_data, dict)
        self.assertIsInstance(evidence.structured_data["current_risk"], dict)
        self.assertEqual(evidence.structured_data["current_risk"]["volatility"], 0.18)
        self.assertIsNone(evidence.structured_data["optimized_risk"])
        # Crucial: verify psycopg JSONField round-trip is valid JSON
        serialized = json.dumps(evidence.structured_data)
        self.assertIn('"volatility": 0.18', serialized)

    def test_existing_persisted_agent_results_no_regression(self):
        session = ResearchSessionService.create_session(user_message="Test no regression")
        state = AgentState(
            user_message="Test no regression",
            results={
                "financial": AgentResult(
                    response="Financial statement summary.",
                    tools_used=["get_financials"],
                    data={"revenue": 100000, "currency": "INR"},
                ),
                "market": AgentResult(
                    response="Market quote summary.",
                    tools_used=["get_quote"],
                    data=None,
                ),
            },
        )
        ResearchSessionService.save_workflow_result(session.id, state)

        fin_ev = ResearchEvidence.objects.get(session=session, agent_name="financial")
        self.assertEqual(fin_ev.structured_data, {"revenue": 100000, "currency": "INR"})
        self.assertEqual(fin_ev.response, "Financial statement summary.")
        self.assertEqual(fin_ev.tools_used, ["get_financials"])

        mkt_ev = ResearchEvidence.objects.get(session=session, agent_name="market")
        self.assertIsNone(mkt_ev.structured_data)

    def test_sec_evidence_round_trip_persistence_and_reconstruction(self):
        """Phase 5.4: Verify SEC document evidence and provenance round-trip through session persistence."""
        session = ResearchSessionService.create_session(
            user_message="Analyze AAPL Form 10-K filing",
            ticker="AAPL",
            market="US",
            route="financial",
            thread_id="aapl-sec-persist-thread",
        )

        sec_evidence_item = {
            "chunk_id": "sec-chunk-001",
            "document_id": "d1c2b3a4-1234-5678-90ab-cdef12345678",
            "source_type": "SEC_EDGAR",
            "sec_form": "10-K",
            "sec_accession_number": "0000320193-23-000106",
            "sec_filing_date": "2023-11-03",
            "sec_report_date": "2023-09-30",
            "sec_cik": "0000320193",
            "source_url": "https://www.sec.gov/ix?doc=/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
            "score": 0.92,
            "page": 24,
            "text": "Total net sales were $383,285 million in fiscal year 2023 compared to $394,328 million in 2022.",
            "metadata": {
                "section": "Item 7",
                "fiscal_year": 2023,
            },
            "citation": "SEC Form 10-K (0000320193-23-000106), p.24",
        }

        provenance_item = ProviderProvenance(
            primary_provider="sec_edgar",
            source="sec_edgar",
            fallback_used=False,
            data_status="complete",
            fallback_reason=None,
        )

        state = AgentState(
            user_message="Analyze AAPL Form 10-K filing",
            ticker="AAPL",
            market="US",
            route="financial",
            research_context=ResearchContext(
                ticker="AAPL",
                market="US",
                document_evidence=[sec_evidence_item],
                provenance={"financials": provenance_item},
            ),
            results={
                "financial": AgentResult(
                    response="According to Apple's Form 10-K filed on 2023-11-03 [SEC Form 10-K, Accession: 0000320193-23-000106], total net sales were $383,285 million.",
                    tools_used=["search_financial_documents"],
                    data={
                        "ticker": "AAPL",
                        "market": "US",
                        "document_evidence": [sec_evidence_item],
                        "provenance": {"financials": provenance_item},
                    },
                ),
                "synthesis": AgentResult(
                    response="Apple demonstrates robust profitability based on its SEC Form 10-K filing.",
                    tools_used=["llm_synthesis"],
                    data={
                        "document_evidence": [sec_evidence_item],
                        "provenance": {"financials": provenance_item},
                    },
                ),
            },
        )

        saved_session = ResearchSessionService.save_workflow_result(
            session_id=session.id,
            agent_state=state,
            latency_ms=850.0,
            status="COMPLETED",
        )

        self.assertEqual(saved_session.status, "COMPLETED")
        self.assertEqual(saved_session.ticker, "AAPL")
        self.assertEqual(saved_session.market, "US")

        # 1. Verify ResearchEvidence persistence in DB
        fin_ev = ResearchEvidence.objects.get(session=session, agent_name="financial")
        self.assertIsInstance(fin_ev.structured_data, dict)
        self.assertIn("document_evidence", fin_ev.structured_data)
        self.assertIn("provenance", fin_ev.structured_data)

        # Confirm document evidence survives cleanly
        persisted_docs = fin_ev.structured_data["document_evidence"]
        self.assertIsInstance(persisted_docs, list)
        self.assertEqual(len(persisted_docs), 1)
        doc = persisted_docs[0]
        self.assertEqual(doc["sec_form"], "10-K")
        self.assertEqual(doc["sec_accession_number"], "0000320193-23-000106")
        self.assertEqual(doc["sec_cik"], "0000320193")
        self.assertEqual(doc["sec_filing_date"], "2023-11-03")
        self.assertEqual(doc["score"], 0.92)
        self.assertEqual(doc["chunk_id"], "sec-chunk-001")
        self.assertEqual(doc["source_url"], "https://www.sec.gov/ix?doc=/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm")
        self.assertEqual(doc["page"], 24)
        self.assertEqual(doc["citation"], "SEC Form 10-K (0000320193-23-000106), p.24")

        # Confirm provenance survives
        prov = fin_ev.structured_data["provenance"]["financials"]
        self.assertEqual(prov["primary_provider"], "sec_edgar")
        self.assertEqual(prov["source"], "sec_edgar")
        self.assertFalse(prov["fallback_used"])
        self.assertEqual(prov["data_status"], "complete")

        # 2. Verify typed ResearchContext reconstruction
        reconstructed = ResearchSessionService.reconstruct_research_context(session.id)
        self.assertIsNotNone(reconstructed)
        self.assertIsInstance(reconstructed, ResearchContext)
        self.assertEqual(reconstructed.ticker, "AAPL")
        self.assertEqual(reconstructed.market, "US")
        self.assertEqual(len(reconstructed.document_evidence), 1)
        self.assertEqual(reconstructed.document_evidence[0]["sec_accession_number"], "0000320193-23-000106")
        self.assertEqual(reconstructed.document_evidence[0]["sec_form"], "10-K")
        self.assertIn("financials", reconstructed.provenance)
        self.assertIsInstance(reconstructed.provenance["financials"], ProviderProvenance)
        self.assertEqual(reconstructed.provenance["financials"].primary_provider, "sec_edgar")
        self.assertEqual(reconstructed.provenance["financials"].source, "sec_edgar")
        self.assertEqual(reconstructed.provenance["financials"].data_status, "complete")

        # 3. Verify chatbot context reconstruction
        chatbot_context = ResearchSessionService.build_chatbot_context(session.id)
        self.assertIn("financial", chatbot_context["evidence"])
        self.assertIn("synthesis", chatbot_context["evidence"])
        self.assertEqual(
            chatbot_context["evidence"]["financial"]["structured_data"]["document_evidence"][0]["sec_accession_number"],
            "0000320193-23-000106",
        )

    def test_sec_evidence_no_data_loss(self):
        """Phase 5.4: Verify saving workflow result does not reduce populated document_evidence to empty, None, or string blob."""
        session = ResearchSessionService.create_session(
            user_message="Test no data loss",
            ticker="MSFT",
            market="US",
            route="financial",
        )

        populated_evidence = [
            {
                "chunk_id": f"chunk-{i}",
                "document_id": f"doc-{i}",
                "sec_form": "10-Q",
                "sec_accession_number": f"0000789019-24-00000{i}",
                "sec_filing_date": "2024-01-25",
                "sec_cik": "0000789019",
                "source_url": f"https://www.sec.gov/edgar/doc-{i}",
                "score": 0.85 + (i * 0.02),
                "page": i,
                "text": f"Sample excerpt from Form 10-Q chunk {i}",
                "metadata": {"item": "Part I Item 1"},
            }
            for i in range(1, 4)
        ]

        state = AgentState(
            user_message="Test no data loss",
            ticker="MSFT",
            market="US",
            research_context=ResearchContext(
                ticker="MSFT",
                market="US",
                document_evidence=populated_evidence,
            ),
            results={
                "financial": AgentResult(
                    response="MSFT 10-Q analysis.",
                    tools_used=["search_financial_documents"],
                    data={"document_evidence": populated_evidence},
                ),
            },
        )

        ResearchSessionService.save_workflow_result(session.id, state)

        fin_ev = ResearchEvidence.objects.get(session=session, agent_name="financial")
        docs = fin_ev.structured_data.get("document_evidence")

        # Crucial assertions against data loss:
        self.assertIsNotNone(docs)
        self.assertNotEqual(docs, [])
        self.assertNotIsInstance(docs, str)
        self.assertIsInstance(docs, list)
        self.assertEqual(len(docs), 3)

        # Check all identifiers retained
        for i, doc in enumerate(docs, start=1):
            self.assertEqual(doc["chunk_id"], f"chunk-{i}")
            self.assertEqual(doc["document_id"], f"doc-{i}")
            self.assertEqual(doc["sec_form"], "10-Q")
            self.assertEqual(doc["sec_accession_number"], f"0000789019-24-00000{i}")
            self.assertEqual(doc["sec_cik"], "0000789019")
            self.assertEqual(doc["source_url"], f"https://www.sec.gov/edgar/doc-{i}")
            self.assertAlmostEqual(doc["score"], 0.85 + (i * 0.02))

    def test_backward_compatibility_legacy_and_india_session(self):
        """Phase 5.4: Ensure existing historical/India sessions without SEC evidence load without error."""
        # 1. Historical legacy session with no document_evidence
        legacy_session = ResearchSessionService.create_session(
            user_message="Legacy query",
            ticker="INFY",
            market="IN",
            route="financial",
        )
        ResearchEvidence.objects.create(
            session=legacy_session,
            agent_name="financial",
            response="Legacy financial analysis without SEC evidence.",
            tools_used=["get_financials"],
            structured_data={"revenue": 45000, "ebitda": 11000},
        )

        rc_legacy = ResearchSessionService.reconstruct_research_context(legacy_session.id)
        self.assertIsNotNone(rc_legacy)
        self.assertEqual(rc_legacy.ticker, "INFY")
        self.assertEqual(rc_legacy.market, "IN")
        self.assertEqual(rc_legacy.document_evidence, [])
        self.assertEqual(rc_legacy.provenance, {})

        # 2. India-market deterministic financial session
        india_session = ResearchSessionService.create_session(
            user_message="Analyze RELIANCE financial performance",
            ticker="RELIANCE",
            market="IN",
            route="financial",
        )

        india_provenance = ProviderProvenance(
            primary_provider="upstox",
            source="upstox",
            fallback_used=False,
            data_status="complete",
        )

        state = AgentState(
            user_message="Analyze RELIANCE financial performance",
            ticker="RELIANCE",
            market="IN",
            route="financial",
            results={
                "financial": AgentResult(
                    response="RELIANCE revenue grew 12% YoY.",
                    tools_used=["get_financials", "get_key_metrics"],
                    data={
                        "revenue": 950000,
                        "currency": "INR",
                        "provenance": {"financials": india_provenance},
                    },
                ),
            },
        )

        ResearchSessionService.save_workflow_result(india_session.id, state)
        rc_india = ResearchSessionService.reconstruct_research_context(india_session.id)

        self.assertIsNotNone(rc_india)
        self.assertEqual(rc_india.ticker, "RELIANCE")
        self.assertEqual(rc_india.market, "IN")
        self.assertEqual(rc_india.document_evidence, [])
        self.assertIn("financials", rc_india.provenance)
        self.assertEqual(rc_india.provenance["financials"].primary_provider, "upstox")
        self.assertEqual(rc_india.provenance["financials"].source, "upstox")
        self.assertFalse(rc_india.provenance["financials"].fallback_used)

    def test_citation_metadata_survives_persistence(self):
        """Phase 5.4: Ensure SEC citation-related metadata needed for attribution survives persistence."""
        session = ResearchSessionService.create_session(
            user_message="Citation attribution test",
            ticker="NVDA",
            market="US",
            route="financial",
        )

        sec_evidence = [
            {
                "chunk_id": "nvda-chunk-01",
                "sec_form": "10-K",
                "sec_accession_number": "0001045810-24-000029",
                "sec_filing_date": "2024-02-21",
                "source_url": "https://www.sec.gov/ix?doc=/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm",
                "citation": "SEC Form 10-K (0001045810-24-000029), p.35",
                "score": 0.95,
            }
        ]

        state = AgentState(
            user_message="Citation attribution test",
            ticker="NVDA",
            market="US",
            results={
                "financial": AgentResult(
                    response="NVDA gross margin reached 72.7% per SEC Form 10-K (0001045810-24-000029).",
                    tools_used=["search_financial_documents"],
                    data={"document_evidence": sec_evidence},
                ),
                "synthesis": AgentResult(
                    response="Synthesized attribution: NVDA reported stellar margins [SEC Form 10-K, Accession: 0001045810-24-000029].",
                    tools_used=["llm_synthesis"],
                    data={"document_evidence": sec_evidence},
                ),
            },
        )

        saved = ResearchSessionService.save_workflow_result(session.id, state)
        self.assertIn("0001045810-24-000029", saved.final_synthesis)

        evidence = ResearchSessionService.get_evidence(session.id)
        synth_item = next(e for e in evidence if e.agent_name == "synthesis")
        self.assertIn("0001045810-24-000029", synth_item.response)

        reconstructed_rc = ResearchSessionService.reconstruct_research_context(session.id)
        doc = reconstructed_rc.document_evidence[0]
        self.assertEqual(doc["citation"], "SEC Form 10-K (0001045810-24-000029), p.35")
        self.assertEqual(doc["sec_accession_number"], "0001045810-24-000029")
        self.assertEqual(doc["sec_filing_date"], "2024-02-21")
        self.assertEqual(doc["source_url"], "https://www.sec.gov/ix?doc=/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm")

    def test_json_safety_types_round_trip(self):
        """Phase 5.4: Ensure structured_data handles Enum, float NaN/inf, UUID, date/datetime cleanly for JSONField."""
        import datetime
        import enum

        class DummyStatus(str, enum.Enum):
            ACTIVE = "active"

        session = ResearchSessionService.create_session(user_message="JSON types test")
        state = AgentState(
            user_message="JSON types test",
            results={
                "financial": AgentResult(
                    response="Types test",
                    tools_used=[],
                    data={
                        "status_enum": DummyStatus.ACTIVE,
                        "uuid_field": uuid.uuid4(),
                        "date_field": datetime.date(2023, 11, 3),
                        "nan_field": float("nan"),
                        "inf_field": float("inf"),
                        "nested_list": [{"score": 0.99}],
                    },
                )
            },
        )

        ResearchSessionService.save_workflow_result(session.id, state)

        ev = ResearchEvidence.objects.get(session=session, agent_name="financial")
        self.assertEqual(ev.structured_data["status_enum"], "active")
        self.assertIsInstance(ev.structured_data["uuid_field"], str)
        self.assertEqual(ev.structured_data["date_field"], "2023-11-03")
        self.assertIsNone(ev.structured_data["nan_field"])
        self.assertIsNone(ev.structured_data["inf_field"])
        self.assertEqual(ev.structured_data["nested_list"][0]["score"], 0.99)
        # Ensure json.dumps works without error
        json.dumps(ev.structured_data)
