from django.core.exceptions import ValidationError
from django.db import transaction

from apps.research.models import ResearchEvidence, ResearchSession


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

    @staticmethod
    def save_workflow_result(
        session_id: object,
        agent_state: object,
        latency_ms: float | None = None,
        status: str = "COMPLETED",
    ) -> ResearchSession:
        session = ResearchSessionService.get_session(session_id)

        results = {}
        if hasattr(agent_state, "results") and isinstance(agent_state.results, dict):
            results = agent_state.results
        elif isinstance(agent_state, dict) and "results" in agent_state:
            results = agent_state["results"]

        with transaction.atomic():
            for agent_name, raw_result in results.items():
                response, tools_used, structured_data = (
                    ResearchSessionService._coerce_agent_result(raw_result)
                )

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

    @staticmethod
    def _coerce_agent_result(
        raw: object,
    ) -> tuple[str, list[str], dict[str, object] | None]:
        if isinstance(raw, dict):
            response = str(raw.get("response", ""))
            tools_used = list(raw.get("tools_used", []))
            structured_data = raw.get("data")
            if isinstance(structured_data, dict):
                structured_data = dict(structured_data)
            else:
                structured_data = None
            return response, tools_used, structured_data
        elif hasattr(raw, "response"):
            response = str(getattr(raw, "response", ""))
            tools_used = list(getattr(raw, "tools_used", []))
            structured_data = getattr(raw, "data", None)
            if isinstance(structured_data, dict):
                structured_data = dict(structured_data)
            else:
                structured_data = None
            return response, tools_used, structured_data
        else:
            return str(raw), [], None
