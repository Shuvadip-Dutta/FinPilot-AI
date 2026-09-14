from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.core.serializers import RegisterSerializer, UserResponseSerializer
from common.logger import get_logger

logger = get_logger("core")


# ---------------------------------------------------------------------------
# Throttled JWT views
# These subclasses replace the global AnonRateThrottle with the dedicated
# "auth" scope (30/minute by default) so that repeated login/refresh calls
# during local development never exhaust the shared 100/day anon bucket.
# ---------------------------------------------------------------------------


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """JWT token obtain with a dedicated per-minute auth throttle scope."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class ThrottledTokenRefreshView(TokenRefreshView):
    """JWT token refresh with a dedicated per-minute auth throttle scope."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"



@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([])
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