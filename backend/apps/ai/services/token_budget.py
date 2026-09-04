from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
import json
import math
import threading
import time
from typing import Any


class DegradationTier(str, Enum):
    NORMAL = "normal"
    CONSTRAINED = "constrained"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class TokenBudgetExceededError(Exception):
    """Raised when an estimated LLM request exceeds the effective per-request token budget limit."""

    def __init__(
        self,
        estimated_tokens: int,
        effective_limit: int,
        max_request_tokens: int,
        safety_reserve_tokens: int,
        message: str | None = None,
    ) -> None:
        self.estimated_tokens = estimated_tokens
        self.effective_limit = effective_limit
        self.max_request_tokens = max_request_tokens
        self.safety_reserve_tokens = safety_reserve_tokens
        if message is None:
            message = (
                f"Estimated request token size ({estimated_tokens}) exceeds "
                f"effective limit ({effective_limit} = max {max_request_tokens} "
                f"- reserve {safety_reserve_tokens})."
            )
        self.message = message
        super().__init__(self.message)


class TPMLimitExceededError(Exception):
    """Raised when an estimated LLM request exceeds the Tokens Per Minute (TPM) limit."""

    def __init__(
        self,
        estimated_tokens: int,
        current_tpm_usage: int,
        tpm_limit: int,
        remaining_tpm: int,
        message: str | None = None,
    ) -> None:
        self.estimated_tokens = estimated_tokens
        self.current_tpm_usage = current_tpm_usage
        self.tpm_limit = tpm_limit
        self.remaining_tpm = remaining_tpm
        if message is None:
            message = (
                f"Estimated request token size ({estimated_tokens}) exceeds remaining "
                f"TPM quota ({remaining_tpm} = limit {tpm_limit} - current {current_tpm_usage})."
            )
        self.message = message
        super().__init__(self.message)


class TPDLimitExceededError(Exception):
    """Raised when an estimated LLM request exceeds the Tokens Per Day (TPD) limit."""

    def __init__(
        self,
        estimated_tokens: int,
        current_tpd_usage: int,
        tpd_limit: int,
        remaining_tpd: int,
        message: str | None = None,
    ) -> None:
        self.estimated_tokens = estimated_tokens
        self.current_tpd_usage = current_tpd_usage
        self.tpd_limit = tpd_limit
        self.remaining_tpd = remaining_tpd
        if message is None:
            message = (
                f"Estimated request token size ({estimated_tokens}) exceeds remaining "
                f"TPD quota ({remaining_tpd} = limit {tpd_limit} - current {current_tpd_usage})."
            )
        self.message = message
        super().__init__(self.message)


@dataclass(frozen=True)
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            raise ValueError("prompt_tokens must be non-negative.")
        if self.completion_tokens < 0:
            raise ValueError("completion_tokens must be non-negative.")
        if self.total_tokens < 0:
            raise ValueError("total_tokens must be non-negative.")
        if not self.model or not str(self.model).strip():
            raise ValueError("model must be a non-empty string.")


@dataclass(frozen=True)
class TokenBudgetCheck:
    estimated_input_tokens: int
    requested_output_tokens: int
    estimated_total_tokens: int
    allowed: bool
    remaining_budget: int
    reason: str
    degradation_tier: DegradationTier = DegradationTier.NORMAL


_default_manager: TokenBudgetManager | None = None
_default_manager_lock = threading.Lock()


def get_default_token_budget_manager() -> TokenBudgetManager:
    """Return the process-level shared TokenBudgetManager instance."""
    global _default_manager
    if _default_manager is None:
        with _default_manager_lock:
            if _default_manager is None:
                max_req = 32768
                safety_res = 1024
                tpm_limit = None
                tpd_limit = None
                try:
                    from django.conf import settings

                    max_req = getattr(settings, "GROQ_MAX_REQUEST_TOKENS", 32768)
                    safety_res = getattr(settings, "GROQ_SAFETY_RESERVE_TOKENS", 1024)
                    tpm_limit = getattr(settings, "GROQ_TPM_LIMIT", None)
                    tpd_limit = getattr(settings, "GROQ_TPD_LIMIT", None)
                except Exception:
                    pass

                _default_manager = TokenBudgetManager(
                    max_request_tokens=max_req,
                    safety_reserve_tokens=safety_res,
                    tpm_limit=tpm_limit,
                    tpd_limit=tpd_limit,
                )
    return _default_manager


class TokenBudgetManager:
    """Performs pre-flight token estimation, request limit enforcement, and TPM/TPD quota tracking."""

    MESSAGE_OVERHEAD_TOKENS = 4
    TOOL_OVERHEAD_TOKENS = 8

    def __init__(
        self,
        max_request_tokens: int = 32768,
        safety_reserve_tokens: int = 1024,
        token_estimation_chars_per_token: float = 4.0,
        tpm_limit: int | None = None,
        tpd_limit: int | None = None,
    ) -> None:
        if max_request_tokens <= 0:
            raise ValueError("max_request_tokens must be positive.")
        if safety_reserve_tokens < 0:
            raise ValueError("safety_reserve_tokens must be non-negative.")
        if safety_reserve_tokens >= max_request_tokens:
            raise ValueError(
                "safety_reserve_tokens must be strictly less than max_request_tokens."
            )
        if token_estimation_chars_per_token <= 0:
            raise ValueError("token_estimation_chars_per_token must be positive.")
        if tpm_limit is not None and tpm_limit <= 0:
            raise ValueError("tpm_limit must be positive if specified.")
        if tpd_limit is not None and tpd_limit <= 0:
            raise ValueError("tpd_limit must be positive if specified.")

        self.max_request_tokens = max_request_tokens
        self.safety_reserve_tokens = safety_reserve_tokens
        self.chars_per_token = float(token_estimation_chars_per_token)
        self.tpm_limit = tpm_limit
        self.tpd_limit = tpd_limit

        self.last_usage: LLMUsage | None = None
        self._lock = threading.Lock()
        self._tpm_records: list[tuple[float, int]] = []
        self._tpd_current_date: date | None = None
        self._tpd_usage: int = 0

    def _now_ts(self) -> float:
        return time.time()

    def _now_dt(self) -> datetime:
        return datetime.now(timezone.utc)

    def _clean_tpm_records(self, now_ts: float) -> None:
        cutoff = now_ts - 60.0
        self._tpm_records = [
            (ts, count) for ts, count in self._tpm_records if ts > cutoff
        ]

    def _get_current_tpm_usage(self, now_ts: float) -> int:
        self._clean_tpm_records(now_ts)
        return sum(count for _, count in self._tpm_records)

    def _get_current_tpd_usage(self, now_dt: datetime) -> int:
        current_utc_date = now_dt.date()
        if self._tpd_current_date != current_utc_date:
            self._tpd_current_date = current_utc_date
            self._tpd_usage = 0
        return self._tpd_usage

    def record_actual_usage(self, usage: LLMUsage) -> None:
        if not isinstance(usage, LLMUsage):
            raise ValueError("usage must be an instance of LLMUsage.")

        with self._lock:
            now_ts = self._now_ts()
            now_dt = self._now_dt()

            self._tpm_records.append((now_ts, usage.total_tokens))
            self._clean_tpm_records(now_ts)

            current_utc_date = now_dt.date()
            if self._tpd_current_date != current_utc_date:
                self._tpd_current_date = current_utc_date
                self._tpd_usage = 0
            self._tpd_usage += usage.total_tokens

            self.last_usage = usage

    @staticmethod
    def _ratio_to_tier(ratio: float) -> DegradationTier:
        if ratio <= 0.0:
            return DegradationTier.EXHAUSTED
        if ratio <= 0.10:
            return DegradationTier.CRITICAL
        if ratio <= 0.30:
            return DegradationTier.CONSTRAINED
        return DegradationTier.NORMAL

    def _calculate_degradation_tier_unlocked(
        self, estimated_tokens: int = 0
    ) -> DegradationTier:
        tiers: list[DegradationTier] = []

        if self.effective_limit > 0:
            remaining_req = self.effective_limit - estimated_tokens
            req_ratio = remaining_req / float(self.effective_limit)
            tiers.append(self._ratio_to_tier(req_ratio))

        if self.tpm_limit is not None and self.tpm_limit > 0:
            now_ts = self._now_ts()
            current_tpm = self._get_current_tpm_usage(now_ts)
            remaining_tpm = self.tpm_limit - (current_tpm + estimated_tokens)
            tpm_ratio = remaining_tpm / float(self.tpm_limit)
            tiers.append(self._ratio_to_tier(tpm_ratio))

        if self.tpd_limit is not None and self.tpd_limit > 0:
            now_dt = self._now_dt()
            current_tpd = self._get_current_tpd_usage(now_dt)
            remaining_tpd = self.tpd_limit - (current_tpd + estimated_tokens)
            tpd_ratio = remaining_tpd / float(self.tpd_limit)
            tiers.append(self._ratio_to_tier(tpd_ratio))

        if not tiers:
            return DegradationTier.NORMAL

        tier_severity = {
            DegradationTier.NORMAL: 0,
            DegradationTier.CONSTRAINED: 1,
            DegradationTier.CRITICAL: 2,
            DegradationTier.EXHAUSTED: 3,
        }
        return max(tiers, key=lambda t: tier_severity[t])

    def get_degradation_tier(self, estimated_tokens: int = 0) -> DegradationTier:
        with self._lock:
            return self._calculate_degradation_tier_unlocked(estimated_tokens)

    def get_usage_snapshot(self) -> dict[str, Any]:
        with self._lock:
            now_ts = self._now_ts()
            now_dt = self._now_dt()

            current_tpm = self._get_current_tpm_usage(now_ts)
            current_tpd = self._get_current_tpd_usage(now_dt)

            remaining_tpm = (
                self.tpm_limit - current_tpm
                if self.tpm_limit is not None
                else None
            )
            remaining_tpd = (
                self.tpd_limit - current_tpd
                if self.tpd_limit is not None
                else None
            )

            return {
                "current_tpm_usage": current_tpm,
                "tpm_limit": self.tpm_limit,
                "remaining_tpm": remaining_tpm,
                "current_tpd_usage": current_tpd,
                "tpd_limit": self.tpd_limit,
                "remaining_tpd": remaining_tpd,
                "degradation_tier": self._calculate_degradation_tier_unlocked(0),
            }

    @property
    def effective_limit(self) -> int:
        return self.max_request_tokens - self.safety_reserve_tokens

    def estimate_input_tokens(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> int:
        if not messages and not tools:
            return 0

        total_chars = 0
        message_overhead = len(messages) * self.MESSAGE_OVERHEAD_TOKENS

        for msg in messages:
            role = str(msg.get("role", ""))
            content = msg.get("content", "")
            if isinstance(content, (dict, list)):
                content_str = json.dumps(content)
            else:
                content_str = str(content or "")
            total_chars += len(role) + len(content_str)

            for extra_key in ("name", "tool_call_id"):
                if extra_key in msg and msg[extra_key]:
                    total_chars += len(str(msg[extra_key]))

        tool_overhead = 0
        if tools:
            tool_overhead = self.TOOL_OVERHEAD_TOKENS
            total_chars += len(json.dumps(tools))

        chars_tokens = math.ceil(total_chars / self.chars_per_token)
        return message_overhead + tool_overhead + chars_tokens

    def estimate_request_tokens(
        self,
        messages: list[dict[str, Any]],
        max_output_tokens: int,
        tools: list[dict[str, Any]] | None = None,
    ) -> int:
        if max_output_tokens < 0:
            raise ValueError("max_output_tokens must be non-negative.")

        input_tokens = self.estimate_input_tokens(messages, tools=tools)
        return input_tokens + max_output_tokens

    def check_request_budget(
        self,
        messages: list[dict[str, Any]],
        max_output_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        raise_on_exceeded: bool = False,
    ) -> TokenBudgetCheck:
        if max_output_tokens < 0:
            raise ValueError("max_output_tokens must be non-negative.")

        estimated_input = self.estimate_input_tokens(messages, tools=tools)
        estimated_total = estimated_input + max_output_tokens

        with self._lock:
            effective_limit = self.effective_limit
            now_ts = self._now_ts()
            now_dt = self._now_dt()

            current_tpm = self._get_current_tpm_usage(now_ts)
            current_tpd = self._get_current_tpd_usage(now_dt)
            degradation_tier = self._calculate_degradation_tier_unlocked(
                estimated_total
            )

            # 1. Per-request effective limit check
            if estimated_total > effective_limit:
                reason = (
                    f"Estimated request ({estimated_total} tokens) exceeds the "
                    f"effective limit ({effective_limit} tokens = max {self.max_request_tokens} "
                    f"- reserve {self.safety_reserve_tokens})."
                )
                check_result = TokenBudgetCheck(
                    estimated_input_tokens=estimated_input,
                    requested_output_tokens=max_output_tokens,
                    estimated_total_tokens=estimated_total,
                    allowed=False,
                    remaining_budget=effective_limit - estimated_total,
                    reason=reason,
                    degradation_tier=degradation_tier,
                )
                if raise_on_exceeded:
                    raise TokenBudgetExceededError(
                        estimated_tokens=estimated_total,
                        effective_limit=effective_limit,
                        max_request_tokens=self.max_request_tokens,
                        safety_reserve_tokens=self.safety_reserve_tokens,
                        message=reason,
                    )
                return check_result

            # 2. TPM quota limit check
            if self.tpm_limit is not None:
                remaining_tpm = self.tpm_limit - current_tpm
                if current_tpm + estimated_total > self.tpm_limit:
                    reason = (
                        f"Estimated request ({estimated_total} tokens) exceeds remaining "
                        f"TPM quota ({remaining_tpm} = limit {self.tpm_limit} - current {current_tpm})."
                    )
                    check_result = TokenBudgetCheck(
                        estimated_input_tokens=estimated_input,
                        requested_output_tokens=max_output_tokens,
                        estimated_total_tokens=estimated_total,
                        allowed=False,
                        remaining_budget=remaining_tpm - estimated_total,
                        reason=reason,
                        degradation_tier=degradation_tier,
                    )
                    if raise_on_exceeded:
                        raise TPMLimitExceededError(
                            estimated_tokens=estimated_total,
                            current_tpm_usage=current_tpm,
                            tpm_limit=self.tpm_limit,
                            remaining_tpm=remaining_tpm,
                            message=reason,
                        )
                    return check_result

            # 3. TPD quota limit check
            if self.tpd_limit is not None:
                remaining_tpd = self.tpd_limit - current_tpd
                if current_tpd + estimated_total > self.tpd_limit:
                    reason = (
                        f"Estimated request ({estimated_total} tokens) exceeds remaining "
                        f"TPD quota ({remaining_tpd} = limit {self.tpd_limit} - current {current_tpd})."
                    )
                    check_result = TokenBudgetCheck(
                        estimated_input_tokens=estimated_input,
                        requested_output_tokens=max_output_tokens,
                        estimated_total_tokens=estimated_total,
                        allowed=False,
                        remaining_budget=remaining_tpd - estimated_total,
                        reason=reason,
                        degradation_tier=degradation_tier,
                    )
                    if raise_on_exceeded:
                        raise TPDLimitExceededError(
                            estimated_tokens=estimated_total,
                            current_tpd_usage=current_tpd,
                            tpd_limit=self.tpd_limit,
                            remaining_tpd=remaining_tpd,
                            message=reason,
                        )
                    return check_result

            # Allowed under all limits
            reason = (
                f"Estimated request ({estimated_total} tokens) is within the "
                f"effective limit ({effective_limit} tokens)."
            )
            return TokenBudgetCheck(
                estimated_input_tokens=estimated_input,
                requested_output_tokens=max_output_tokens,
                estimated_total_tokens=estimated_total,
                allowed=True,
                remaining_budget=effective_limit - estimated_total,
                reason=reason,
                degradation_tier=degradation_tier,
            )

    def validate_request_budget(
        self,
        messages: list[dict[str, Any]],
        max_output_tokens: int,
        tools: list[dict[str, Any]] | None = None,
    ) -> TokenBudgetCheck:
        return self.check_request_budget(
            messages=messages,
            max_output_tokens=max_output_tokens,
            tools=tools,
            raise_on_exceeded=True,
        )
