from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.serializers import AIChatSerializer
from apps.ai.services.agent_service import AgentService


class AIChatView(APIView):

    def post(self, request):

        serializer = AIChatSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        message = serializer.validated_data[
            "message"
        ]

        service = AgentService()

        try:
            result = service.run(
                message
            )

        except ValueError as exc:
            return Response(
                {
                    "error": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "response": result.response,
                "tools_used": result.tools_used,
            },
            status=status.HTTP_200_OK,
        )