"""Alert and portfolio monitoring persistence service.

Handles:
- Cooldown and deduplication of detected monitoring events
- Atomic persistence of Alert records
- Deterministic acknowledgement of alerts
- Preservation of tenant ownership invariants
"""

from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.portfolio.models import Alert, AlertStatus, AlertType, Portfolio
from apps.portfolio.monitor import MonitoringEvent, MonitoringResult
from apps.portfolio.serializers import AlertSerializer


class AlertService:
    """Service for cooldown evaluation, alert persistence, and alert lifecycle management."""

    DEFAULT_COOLDOWN_HOURS = 24

    def is_event_suppressed(
        self,
        event: MonitoringEvent,
        recent_alerts: list[Alert],
        seen_in_batch: set[tuple[str, str | None]],
    ) -> bool:
        """Determine whether a monitoring event should be suppressed by cooldown or intra-batch deduplication."""
        ticker = (event.metadata or {}).get("ticker")
        if ticker:
            ticker = str(ticker).strip().upper()

        event_key = (
            event.alert_type,
            ticker if event.alert_type == AlertType.CONCENTRATION_BREACH else None,
        )
        if event_key in seen_in_batch:
            return True

        matching_alerts = [a for a in recent_alerts if a.alert_type == event.alert_type]
        if not matching_alerts:
            return False

        if event.alert_type == AlertType.CONCENTRATION_BREACH and ticker:
            for alert in matching_alerts:
                alert_title_upper = alert.title.upper()
                if f": {ticker}" in alert_title_upper or alert_title_upper.endswith(ticker):
                    return True
            return False

        return len(matching_alerts) > 0

    def process_monitoring_result(
        self,
        portfolio: Portfolio,
        result: MonitoringResult,
        cooldown_hours: int = DEFAULT_COOLDOWN_HOURS,
    ) -> dict[str, Any]:
        """Evaluate monitoring result against cooldown, persist unsuppressed alerts atomically, and return summary."""
        cooldown_cutoff = result.evaluated_at - timedelta(hours=cooldown_hours)

        created_alerts: list[Alert] = []
        suppressed_events: list[MonitoringEvent] = []

        with transaction.atomic():
            # Lock the portfolio row to serialize concurrent monitoring evaluations for this portfolio
            locked_portfolio = (
                Portfolio.objects.select_for_update()
                .select_related("user")
                .get(pk=portfolio.pk)
            )

            recent_alerts = list(
                Alert.objects.filter(
                    portfolio=locked_portfolio,
                    created_at__gte=cooldown_cutoff,
                ).only("id", "alert_type", "title", "created_at")
            )

            seen_in_batch: set[tuple[str, str | None]] = set()
            unsuppressed_events: list[MonitoringEvent] = []

            for event in result.events:
                ticker = (event.metadata or {}).get("ticker")
                if ticker:
                    ticker = str(ticker).strip().upper()
                event_key = (
                    event.alert_type,
                    ticker if event.alert_type == AlertType.CONCENTRATION_BREACH else None,
                )

                if self.is_event_suppressed(event, recent_alerts, seen_in_batch):
                    suppressed_events.append(event)
                else:
                    seen_in_batch.add(event_key)
                    unsuppressed_events.append(event)

            for event in unsuppressed_events:
                alert = Alert.objects.create(
                    portfolio=locked_portfolio,
                    user=locked_portfolio.user,
                    alert_type=event.alert_type,
                    severity=event.severity,
                    title=event.title,
                    message=event.message,
                    metric_value=event.metric_value,
                    threshold_value=event.threshold_value,
                    status=AlertStatus.ACTIVE,
                )
                created_alerts.append(alert)

        event_dicts = [
            {
                "alert_type": e.alert_type,
                "severity": e.severity,
                "title": e.title,
                "message": e.message,
                "metric_value": str(e.metric_value),
                "threshold_value": str(e.threshold_value),
                "metadata": e.metadata,
            }
            for e in result.events
        ]

        suppressed_dicts = [
            {
                "alert_type": e.alert_type,
                "title": e.title,
                "metric_value": str(e.metric_value),
                "threshold_value": str(e.threshold_value),
                "metadata": e.metadata,
                "reason": "cooldown_active",
            }
            for e in suppressed_events
        ]

        return {
            "portfolio_id": str(portfolio.id),
            "evaluated_at": result.evaluated_at.isoformat(),
            "events": event_dicts,
            "detected_events": event_dicts,
            "alerts_created": AlertSerializer(created_alerts, many=True).data,
            "alerts_suppressed": suppressed_dicts,
        }


    def acknowledge_alert(self, alert: Alert) -> Alert:
        """Idempotently acknowledge an active or existing alert."""
        if alert.status != AlertStatus.ACKNOWLEDGED:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = timezone.now()
            alert.save(update_fields=["status", "acknowledged_at"])
        return alert
