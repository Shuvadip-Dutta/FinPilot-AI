import redis
from django.conf import settings
from django.db import connection
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
    checks = {
        "database": "ok",
        "redis": "ok",
    }

    # 1. PostgreSQL check
    try:
        connection.ensure_connection()
    except Exception as exc:
        logger.error("Health check database probe failed: %s", exc)
        checks["database"] = "error"

    # 2. Redis check
    redis_url = getattr(settings, "CELERY_BROKER_URL", None) or getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_client = redis.Redis.from_url(
            redis_url,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        try:
            redis_client.ping()
        finally:
            redis_client.close()
    except Exception as exc:
        logger.error("Health check Redis probe failed: %s", exc)
        checks["redis"] = "error"

    all_healthy = all(check_status == "ok" for check_status in checks.values())
    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JsonResponse(
        {
            "status": "ok" if all_healthy else "error",
            "service": "finpilot-api",
            "checks": checks,
        },
        status=http_status,
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