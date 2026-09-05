from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import RegisterSerializer, UserResponseSerializer
from common.logger import get_logger

logger = get_logger("core")


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    logger.info("Health check endpoint called.")
    return JsonResponse(
        {
            "status": "ok",
            "service": "finpilot-api",
        }
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(f"User '{user.username}' registered successfully.")
        return Response(
            UserResponseSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )