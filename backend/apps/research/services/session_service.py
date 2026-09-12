import datetime
import decimal
import json
import math
from typing import Any
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from pydantic import ValidationError as PydanticValidationError

from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.research.models import ResearchEvidence, ResearchSession
from apps.research.services.schemas import (
    CompanyProfile,
    FinancialStatement,
    HistoricalMarketData,
    KeyMetric,
    KeyMetricsResearch,
    NewsResearch,
)



class ResearchSessionService:

    @staticmethod
    def create_session(
        user_message: str,
        user: object = None,
        ticker: str | None = None,
        market: str | None = None,
        route: str = "",
        thread_id: str = "",
    ) -> ResearchSession:
        if user is None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user, _ = User.objects.get_or_create(
                username="system_default",
                defaults={
                    "email": "system_default@finpilot.local",
                    "is_active": False,
                },
            )

        return ResearchSession.objects.create(
            user=user,
            user_message=user_message,
            ticker=ticker,
            market=market,
            route=route,
            thread_id=thread_id,
        )

    @staticmethod
    def get_session(session_id: object) -> ResearchSession:
        try:
            return ResearchSession.objects.get(pk=session_id)
        except (ResearchSession.DoesNotExist, ValueError, ValidationError):
            raise ResearchSession.DoesNotExist(
                f"ResearchSession with id '{session_id}' does not exist."
            )

    @staticmethod
    def get_user_sessions(user: object) -> list[ResearchSession]:
        return list(ResearchSession.objects.filter(user=user).order_by("-created_at"))

    @staticmethod
    def get_user_session(user: object, session_id: object) -> ResearchSession:
        try:
            return ResearchSession.objects.prefetch_related("evidence_items").get(
                pk=session_id, user=user
            )
        except (ResearchSession.DoesNotExist, ValueError, ValidationError):
            raise ResearchSession.DoesNotExist(
                f"ResearchSession with id '{session_id}' does not exist."
            )

    @classmethod
    def save_workflow_result(
        cls,
        session_id: object,
        agent_state: object,
        latency_ms: float | None = None,
        status: str = "COMPLETED",
    ) -> ResearchSession:
        session = cls.get_session(session_id)

        results = {}
        if hasattr(agent_state, "results") and isinstance(agent_state.results, dict):
            results = agent_state.results
        elif isinstance(agent_state, dict) and "results" in agent_state:
            results = agent_state["results"]

        rc = getattr(agent_state, "research_context", None)
        if rc is None and isinstance(agent_state, dict):
            rc = agent_state.get("research_context")

        with transaction.atomic():
            for agent_name, raw_result in results.items():
                response, tools_used, structured_data = (
                    cls._coerce_agent_result(raw_result)
                )

                # Ensure SEC document_evidence and provenance are preserved if present on research_context
                if rc is not None and agent_name in ("synthesis", "financial"):
                    if structured_data is None:
                        structured_data = {}
                    if isinstance(structured_data, dict):
                        rc_docs = getattr(rc, "document_evidence", None) or (
                            rc.get("document_evidence") if isinstance(rc, dict) else None
                        )
                        if rc_docs and not structured_data.get("document_evidence"):
                            structured_data["document_evidence"] = cls._to_json_compatible(rc_docs)

                        rc_prov = getattr(rc, "provenance", None) or (
                            rc.get("provenance") if isinstance(rc, dict) else None
                        )
                        if rc_prov:
                            current_prov = structured_data.get("provenance")
                            if not isinstance(current_prov, dict):
                                structured_data["provenance"] = cls._to_json_compatible(rc_prov)
                            else:
                                for k, v in cls._to_json_compatible(rc_prov).items():
                                    if k not in current_prov:
                                        current_prov[k] = v

                ResearchEvidence.objects.update_or_create(
                    session=session,
                    agent_name=agent_name,
                    defaults={
                        "response": response,
                        "tools_used": tools_used,
                        "structured_data": structured_data,
                    },
                )

                if agent_name == "synthesis" and response:
                    session.final_synthesis = response

            if latency_ms is not None:
                session.latency_ms = latency_ms

            session.status = status
            session.save()

        return session

    @staticmethod
    def get_evidence(session_id: object) -> list[ResearchEvidence]:
        session = ResearchSessionService.get_session(session_id)
        return list(session.evidence_items.all())

    @classmethod
    def reconstruct_research_context(
        cls,
        session_id: object,
    ) -> ResearchContext | None:
        """Reconstruct canonical ResearchContext from persisted session evidence."""
        session = cls.get_session(session_id)
        evidence_items = cls.get_evidence(session.id)
        if not evidence_items:
            if session.ticker:
                return ResearchContext(
                    ticker=session.ticker,
                    market=session.market or "IN",
                )
            return None

        evidence_map = {item.agent_name: item for item in evidence_items}

        # 1. Direct research_context evidence if explicitly stored
        if "research_context" in evidence_map:
            rc_raw = evidence_map["research_context"].structured_data
            if isinstance(rc_raw, dict) and "ticker" in rc_raw:
                try:
                    return ResearchContext.model_validate(rc_raw)
                except (PydanticValidationError, ValueError, TypeError):
                    pass

        ticker = session.ticker or ""
        market = session.market or "IN"

        # 2. Extract document evidence (prefer synthesis, fall back to financial)
        document_evidence: list[dict[str, Any]] = []
        synth_ev = evidence_map.get("synthesis")
        if synth_ev and isinstance(synth_ev.structured_data, dict):
            docs = synth_ev.structured_data.get("document_evidence")
            if isinstance(docs, list) and docs:
                document_evidence = [dict(d) for d in docs if isinstance(d, dict)]

        fin_ev = evidence_map.get("financial")
        if not document_evidence and fin_ev and isinstance(fin_ev.structured_data, dict):
            docs = fin_ev.structured_data.get("document_evidence")
            if isinstance(docs, list) and docs:
                document_evidence = [dict(d) for d in docs if isinstance(d, dict)]

        # 3. Extract section provenance
        provenance_dict: dict[str, ProviderProvenance] = {}
        if synth_ev and isinstance(synth_ev.structured_data, dict):
            p_data = synth_ev.structured_data.get("provenance")
            if isinstance(p_data, dict):
                for k, v in p_data.items():
                    if isinstance(v, dict):
                        try:
                            provenance_dict[k] = ProviderProvenance.model_validate(v)
                        except (PydanticValidationError, ValueError, TypeError):
                            pass
                    elif isinstance(v, ProviderProvenance):
                        provenance_dict[k] = v

        for agent_name, item in evidence_map.items():
            if not isinstance(item.structured_data, dict):
                continue
            p_data = item.structured_data.get("provenance")
            if isinstance(p_data, dict):
                for k, v in p_data.items():
                    if k not in provenance_dict:
                        if isinstance(v, dict):
                            try:
                                provenance_dict[k] = ProviderProvenance.model_validate(v)
                            except (PydanticValidationError, ValueError, TypeError):
                                pass
                        elif isinstance(v, ProviderProvenance):
                            provenance_dict[k] = v

        # 4. Extract domain sections
        financials = None
        key_metrics = None
        market_data = None
        news = None
        company_profile = None

        if fin_ev and isinstance(fin_ev.structured_data, dict):
            raw_fin = fin_ev.structured_data.get("financials") or fin_ev.structured_data.get("financial_statement_data")
            if isinstance(raw_fin, list):
                parsed_fin = []
                for f in raw_fin:
                    if isinstance(f, dict):
                        try:
                            parsed_fin.append(FinancialStatement.model_validate(f))
                        except (PydanticValidationError, ValueError, TypeError):
                            pass
                if parsed_fin:
                    financials = parsed_fin

            raw_km = fin_ev.structured_data.get("key_metrics") or fin_ev.structured_data.get("key_metrics_data")
            if isinstance(raw_km, dict):
                try:
                    key_metrics = KeyMetricsResearch.model_validate(raw_km)
                except (PydanticValidationError, ValueError, TypeError):
                    pass
            elif isinstance(raw_km, list):
                parsed_metrics = []
                for m in raw_km:
                    if isinstance(m, dict):
                        try:
                            parsed_metrics.append(KeyMetric.model_validate(m))
                        except (PydanticValidationError, ValueError, TypeError):
                            pass
                if parsed_metrics:
                    try:
                        key_metrics = KeyMetricsResearch(ticker=ticker, metrics=parsed_metrics)
                    except (PydanticValidationError, ValueError, TypeError):
                        pass

        mkt_ev = evidence_map.get("market")
        if mkt_ev and isinstance(mkt_ev.structured_data, dict):
            raw_mkt = mkt_ev.structured_data.get("market_data") or mkt_ev.structured_data.get("current_market_data")
            if isinstance(raw_mkt, dict):
                try:
                    market_data = HistoricalMarketData.model_validate(raw_mkt)
                except (PydanticValidationError, ValueError, TypeError):
                    pass

        news_ev = evidence_map.get("news")
        if news_ev and isinstance(news_ev.structured_data, dict):
            raw_news = news_ev.structured_data.get("news") or news_ev.structured_data.get("articles")
            if isinstance(raw_news, dict):
                try:
                    news = NewsResearch.model_validate(raw_news)
                except (PydanticValidationError, ValueError, TypeError):
                    pass

        return ResearchContext(
            ticker=ticker,
            market=market,
            company_profile=company_profile,
            financials=financials,
            key_metrics=key_metrics,
            market_data=market_data,
            news=news,
            document_evidence=document_evidence,
            provenance=provenance_dict,
        )

    @staticmethod
    def get_recent_sessions_for_ticker(
        ticker: str,
        limit: int = 5,
        only_completed: bool = True,
    ) -> list[ResearchSession]:
        qs = ResearchSession.objects.filter(ticker=ticker)
        if only_completed:
            qs = qs.filter(status="COMPLETED")
        return list(qs.order_by("-created_at")[:limit])

    @staticmethod
    def get_latest_session_for_ticker(
        ticker: str,
        only_completed: bool = True,
    ) -> ResearchSession | None:
        sessions = ResearchSessionService.get_recent_sessions_for_ticker(
            ticker=ticker,
            limit=1,
            only_completed=only_completed,
        )
        return sessions[0] if sessions else None

    @staticmethod
    def build_chatbot_context(
        session_id: object,
        agent_names: list[str] | None = None,
    ) -> dict:
        session = ResearchSessionService.get_session(session_id)
        evidence_items = ResearchSessionService.get_evidence(session_id)

        evidence_dict = {}
        for item in evidence_items:
            if agent_names is not None and item.agent_name not in agent_names:
                continue
            evidence_dict[item.agent_name] = {
                "response": item.response,
                "tools_used": item.tools_used,
                "structured_data": item.structured_data,
            }

        return {
            "session_id": str(session.id),
            "thread_id": session.thread_id,
            "ticker": session.ticker,
            "market": session.market,
            "route": session.route,
            "status": session.status,
            "user_message": session.user_message,
            "final_synthesis": session.final_synthesis,
            "latency_ms": session.latency_ms,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "evidence": evidence_dict,
        }

    @staticmethod
    def build_multi_session_context(
        ticker: str,
        limit: int = 3,
        agent_names: list[str] | None = None,
        only_completed: bool = True,
    ) -> dict:
        sessions = ResearchSessionService.get_recent_sessions_for_ticker(
            ticker=ticker,
            limit=limit,
            only_completed=only_completed,
        )

        session_list = []
        for session in sessions:
            context = ResearchSessionService.build_chatbot_context(
                session.id,
                agent_names=agent_names,
            )
            session_list.append({
                "session_id": context["session_id"],
                "thread_id": context["thread_id"],
                "created_at": context["created_at"],
                "route": context["route"],
                "status": context["status"],
                "final_synthesis": context["final_synthesis"],
                "evidence": context["evidence"],
            })

        return {
            "ticker": ticker,
            "session_count": len(session_list),
            "sessions": session_list,
        }

    @classmethod
    def _to_json_compatible(cls, val: object) -> object:
        if val is None or isinstance(val, (bool, int, str)):
            return val
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        if hasattr(val, "value") and not isinstance(val, type):
            return cls._to_json_compatible(val.value)
        if hasattr(val, "model_dump") and callable(getattr(val, "model_dump")):
            try:
                dumped = val.model_dump(mode="json")
            except TypeError:
                dumped = val.model_dump()
            return cls._to_json_compatible(dumped)
        if hasattr(val, "dict") and callable(getattr(val, "dict")):
            return cls._to_json_compatible(val.dict())
        if isinstance(val, dict):
            return {str(k): cls._to_json_compatible(v) for k, v in val.items()}
        if isinstance(val, (list, tuple, set)):
            return [cls._to_json_compatible(item) for item in val]
        if isinstance(val, uuid.UUID):
            return str(val)
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.isoformat()
        if isinstance(val, decimal.Decimal):
            return float(val)
        try:
            json.dumps(val)
            return val
        except (TypeError, OverflowError):
            return str(val)

    @classmethod
    def _coerce_agent_result(
        cls,
        raw: object,
    ) -> tuple[str, list[str], dict[str, object] | None]:
        if isinstance(raw, dict):
            response = str(raw.get("response", ""))
            tools_val = raw.get("tools_used", [])
            tools_used = [str(t) for t in tools_val] if isinstance(tools_val, (list, tuple)) else []
            if "data" in raw:
                raw_data = raw["data"]
                if isinstance(raw_data, dict):
                    structured_data = cls._to_json_compatible(raw_data)
                elif hasattr(raw_data, "model_dump") or hasattr(raw_data, "dict"):
                    dumped = cls._to_json_compatible(raw_data)
                    structured_data = dumped if isinstance(dumped, dict) else None
                else:
                    structured_data = None
            else:
                candidate = {
                    k: v for k, v in raw.items() if k not in ("response", "tools_used")
                }
                structured_data = cls._to_json_compatible(candidate) if candidate else None

            if not isinstance(structured_data, dict):
                structured_data = None

            return response, tools_used, structured_data
        elif hasattr(raw, "response"):
            response = str(getattr(raw, "response", ""))
            tools_val = getattr(raw, "tools_used", [])
            tools_used = [str(t) for t in tools_val] if isinstance(tools_val, (list, tuple)) else []
            raw_data = getattr(raw, "data", None)
            if isinstance(raw_data, dict):
                structured_data = cls._to_json_compatible(raw_data)
            elif hasattr(raw_data, "model_dump") or hasattr(raw_data, "dict"):
                dumped = cls._to_json_compatible(raw_data)
                structured_data = dumped if isinstance(dumped, dict) else None
            else:
                structured_data = None

            if not isinstance(structured_data, dict):
                structured_data = None

            return response, tools_used, structured_data
        elif hasattr(raw, "model_dump") and callable(getattr(raw, "model_dump")):
            dumped = cls._to_json_compatible(raw)
            if isinstance(dumped, dict):
                return "", [], dumped
            return str(raw), [], None
        else:
            return str(raw), [], None
