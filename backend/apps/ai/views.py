import uuid

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.exceptions import AIError
from apps.ai.serializers import AIChatSerializer
from apps.ai.services.agent_service import AgentService
from apps.research.models import ResearchSession


class AIChatView(APIView):
    throttle_scope = "ai_heavy"

    def post(self, request):
        serializer = AIChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data["message"]
        ticker = serializer.validated_data.get("ticker")
        market = serializer.validated_data.get("market")
        thread_id = serializer.validated_data.get("thread_id") or str(uuid.uuid4())

        service = AgentService.create_canonical()

        try:
            result = service.run(
                message,
                user=request.user,
                ticker=ticker,
                market=market,
                thread_id=thread_id,
            )
        except (ValueError, AIError) as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = None
        if hasattr(request.user, "is_authenticated") and request.user.is_authenticated:
            session = (
                ResearchSession.objects.filter(
                    thread_id=thread_id,
                    user=request.user,
                )
                .order_by("-created_at")
                .first()
            )

        session_id = str(session.id) if session else None
        route = (
            session.route
            if session
            else (result.data.get("route") if isinstance(result.data, dict) else "general")
        )

        provenance = None
        if isinstance(result.data, dict) and "provenance" in result.data:
            provenance = result.data["provenance"]

        structured_data: dict[str, object] = {}
        if session is not None:
            for item in session.evidence_items.all():
                if item.structured_data:
                    structured_data[item.agent_name] = item.structured_data

        return Response(
            {
                "response": result.response,
                "tools_used": result.tools_used,
                "session_id": session_id,
                "thread_id": thread_id,
                "route": route,
                "provenance": provenance,
                "structured_data": structured_data or None,
            },
            status=status.HTTP_200_OK,
        )