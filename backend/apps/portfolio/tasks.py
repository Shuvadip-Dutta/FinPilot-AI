"""Background Celery tasks for portfolio monitoring and periodic scheduling."""

import logging
from typing import Any

from celery import shared_task
from django.core.exceptions import ValidationError
from django.db import OperationalError

from apps.ai.portfolio.intelligence import PortfolioMarketDataError
from apps.portfolio.alert_service import AlertService
from apps.portfolio.models import Portfolio
from apps.portfolio.monitor import PortfolioMonitorService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="apps.portfolio.tasks.monitor_portfolio",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def monitor_portfolio(self, portfolio_id: str) -> dict[str, Any]:
    """Evaluate a single portfolio against monitoring conditions in the background.

    Security / Tenant Isolation:
    - Accepts ONLY portfolio_id. Does NOT accept user_id.
    - Authoritative user ownership is resolved directly from the database record.
    - Deterministic evaluation and alert persistence are delegated strictly to
      PortfolioMonitorService and AlertService.process_monitoring_result().
    """
    logger.info("Starting background portfolio monitoring for portfolio_id=%s", portfolio_id)

    try:
        portfolio = (
            Portfolio.objects.select_related("user")
            .prefetch_related("holdings")
            .get(pk=portfolio_id)
        )
    except Portfolio.DoesNotExist:
        logger.warning(
            "Portfolio %s not found for monitoring; skipping task.",
            portfolio_id,
        )
        return {
            "status": "not_found",
            "portfolio_id": str(portfolio_id),
            "events_detected": 0,
            "alerts_created": 0,
            "alerts_suppressed": 0,
        }
    except (ValidationError, ValueError) as exc:
        logger.warning(
            "Invalid portfolio_id %s: %s; skipping task.",
            portfolio_id,
            exc,
        )
        return {
            "status": "invalid_id",
            "portfolio_id": str(portfolio_id),
            "events_detected": 0,
            "alerts_created": 0,
            "alerts_suppressed": 0,
        }

    try:
        monitor_service = PortfolioMonitorService()
        monitoring_result = monitor_service.evaluate(
            portfolio=portfolio,
            user=portfolio.user,
        )

        alert_service = AlertService()
        persistence_result = alert_service.process_monitoring_result(
            portfolio=portfolio,
            result=monitoring_result,
        )
    except (PortfolioMarketDataError, OperationalError) as exc:
        logger.warning(
            "Transient failure monitoring portfolio %s: %s. Retrying...",
            portfolio_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=60, max_retries=3)

    events_detected = len(monitoring_result.events)
    alerts_created = len(persistence_result.get("alerts_created", []))
    alerts_suppressed = len(persistence_result.get("alerts_suppressed", []))

    result = {
        "status": "success",
        "portfolio_id": str(portfolio.id),
        "events_detected": events_detected,
        "alerts_created": alerts_created,
        "alerts_suppressed": alerts_suppressed,
    }

    logger.info(
        "Completed background monitoring for portfolio_id=%s: "
        "events=%d, created=%d, suppressed=%d",
        portfolio.id,
        events_detected,
        alerts_created,
        alerts_suppressed,
    )
    return result


@shared_task(
    name="apps.portfolio.tasks.monitor_all_portfolios",
    ignore_result=False,
)
def monitor_all_portfolios() -> dict[str, Any]:
    """Periodic Celery Beat task that discovers portfolios and fans out monitor_portfolio tasks."""
    logger.info("Starting periodic portfolio discovery for monitoring fan-out.")

    portfolio_ids = [
        str(pid)
        for pid in Portfolio.objects.order_by("id").values_list("id", flat=True)
    ]

    dispatched_count = 0
    for pid in portfolio_ids:
        monitor_portfolio.delay(pid)
        dispatched_count += 1

    logger.info("Dispatched %d portfolio monitoring tasks.", dispatched_count)
    return {
        "status": "success",
        "dispatched_count": dispatched_count,
        "portfolio_ids": portfolio_ids,
    }
