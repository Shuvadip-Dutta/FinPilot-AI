from __future__ import annotations

import re
import sys
import time
from typing import Any

from common.logger import get_logger

logger = get_logger("ai")

_ALLOWED_METADATA_KEYS = {
    "event",
    "thread_id",
    "node",
    "route",
    "status",
    "duration_ms",
    "error_type",
    "error_message",
    "result_count",
    "error_count",
}


class AIObserver:
    """Lightweight lifecycle observer for graph and node execution."""

    def __init__(self, logger_instance: Any | None = None):
        self.logger = logger_instance or logger
        self._graph_start_times: dict[str, float] = {}
        self._node_start_times: dict[tuple[str, str], float] = {}

    @staticmethod
    def _sanitize_error_message(value: Any) -> str:
        text = str(value)
        patterns = [
            (r"(?i)(authorization\s*[:=]\s*)(bearer\s+)[^\s,;]+", r"\1\2[REDACTED]"),
            (r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]"),
            (r"(?i)(password\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]"),
            (r"(?i)(token\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]"),
            (r"(?i)(secret\s*[:=]\s*)[^\s,;]+", r"\1[REDACTED]"),
            (r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]"),
        ]
        sanitized = text
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized

    def _safe_metadata(self, **metadata: Any) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key, value in metadata.items():
            if key not in _ALLOWED_METADATA_KEYS or value is None:
                continue

            if key in {"event", "thread_id", "node", "route", "status", "error_type"}:
                safe[key] = str(value)
            elif key == "error_message":
                safe[key] = self._sanitize_error_message(value)
            elif key == "duration_ms":
                safe[key] = round(float(value), 2)
            elif key in {"result_count", "error_count"}:
                safe[key] = int(value)
        return safe

    def _emit(self, event: str, level: str, **metadata: Any) -> None:
        payload = self._safe_metadata(event=event, **metadata)
        getattr(self.logger, level)(payload)

    def _emit_error(self, event: str, **metadata: Any) -> None:
        payload = self._safe_metadata(event=event, **metadata)
        if sys.exc_info()[0] is not None:
            self.logger.exception(payload)
        else:
            self.logger.error(payload)

    def graph_started(
        self,
        *,
        thread_id: str | None = None,
        route: str | None = None,
        **metadata: Any,
    ) -> None:
        thread_key = str(thread_id or "default")
        self._graph_start_times[thread_key] = time.perf_counter()
        self._emit(
            "graph_started",
            level="info",
            thread_id=thread_id,
            route=route,
            status="started",
            **metadata,
        )

    def graph_completed(
        self,
        *,
        thread_id: str | None = None,
        route: str | None = None,
        duration_ms: float | None = None,
        result_count: int | None = None,
        error_count: int | None = None,
        **metadata: Any,
    ) -> None:
        thread_key = str(thread_id or "default")
        started_at = self._graph_start_times.get(thread_key)
        if started_at is None:
            started_at = time.perf_counter()
        else:
            self._graph_start_times.pop(thread_key, None)
        observed_duration = duration_ms
        if observed_duration is None:
            observed_duration = (time.perf_counter() - started_at) * 1000
        self._emit(
            "graph_completed",
            level="info",
            thread_id=thread_id,
            route=route,
            status="completed",
            duration_ms=round(float(observed_duration), 2),
            result_count=result_count,
            error_count=error_count,
            **metadata,
        )

    def graph_failed(
        self,
        *,
        thread_id: str | None = None,
        route: str | None = None,
        duration_ms: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        **metadata: Any,
    ) -> None:
        thread_key = str(thread_id or "default")
        started_at = self._graph_start_times.get(thread_key)
        if started_at is not None:
            self._graph_start_times.pop(thread_key, None)
        else:
            started_at = time.perf_counter()
        observed_duration = duration_ms
        if observed_duration is None:
            observed_duration = (time.perf_counter() - started_at) * 1000
        self._emit_error(
            "graph_failed",
            thread_id=thread_id,
            route=route,
            status="failed",
            duration_ms=round(float(observed_duration), 2),
            error_type=error_type,
            error_message=error_message,
            **metadata,
        )

    def node_started(
        self,
        *,
        thread_id: str | None = None,
        node: str | None = None,
        route: str | None = None,
        **metadata: Any,
    ) -> None:
        node_key = (str(thread_id or "default"), str(node or "unknown"))
        self._node_start_times[node_key] = time.perf_counter()
        self._emit(
            "node_started",
            level="info",
            thread_id=thread_id,
            node=node,
            route=route,
            status="started",
            **metadata,
        )

    def node_completed(
        self,
        *,
        thread_id: str | None = None,
        node: str | None = None,
        route: str | None = None,
        duration_ms: float | None = None,
        result_count: int | None = None,
        error_count: int | None = None,
        **metadata: Any,
    ) -> None:
        node_key = (str(thread_id or "default"), str(node or "unknown"))
        started_at = self._node_start_times.get(node_key)
        if started_at is None:
            started_at = time.perf_counter()
        else:
            self._node_start_times.pop(node_key, None)
        observed_duration = duration_ms
        if observed_duration is None:
            observed_duration = (time.perf_counter() - started_at) * 1000
        self._emit(
            "node_completed",
            level="info",
            thread_id=thread_id,
            node=node,
            route=route,
            status="completed",
            duration_ms=round(float(observed_duration), 2),
            result_count=result_count,
            error_count=error_count,
            **metadata,
        )

    def node_failed(
        self,
        *,
        thread_id: str | None = None,
        node: str | None = None,
        route: str | None = None,
        duration_ms: float | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        **metadata: Any,
    ) -> None:
        node_key = (str(thread_id or "default"), str(node or "unknown"))
        started_at = self._node_start_times.get(node_key)
        if started_at is not None:
            self._node_start_times.pop(node_key, None)
        else:
            started_at = time.perf_counter()
        observed_duration = duration_ms
        if observed_duration is None:
            observed_duration = (time.perf_counter() - started_at) * 1000
        self._emit_error(
            "node_failed",
            thread_id=thread_id,
            node=node,
            route=route,
            status="failed",
            duration_ms=round(float(observed_duration), 2),
            error_type=error_type,
            error_message=error_message,
            **metadata,
        )
