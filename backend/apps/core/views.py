from django.http import JsonResponse
from common.logger import get_logger

logger = get_logger("core")

def health_check(request):
    logger.info("Health check endpoint called.")
    return JsonResponse(
        {
            "status": "ok",
            "service": "finpilot-api",
        }
    )