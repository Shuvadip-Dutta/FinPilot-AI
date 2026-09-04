from __future__ import annotations

from enum import Enum
from typing import Any

from django.conf import settings

from apps.ai.services.providers.groq import GroqProvider
from apps.ai.services.token_budget import (
    LLMUsage,
    TokenBudgetManager,
    get_default_token_budget_manager,
)


class ModelTier(str, Enum):
    FINANCIAL = "financial"
    MARKET = "market"
    NEWS = "news"
    RISK = "risk"
    PORTFOLIO = "portfolio"
    REASONING = "reasoning"
    FAST = "fast"
    EVALUATION = "evaluation"
    SYNTHESIS = "synthesis"
    DEFAULT = "default"


class LLMService:

    _MODEL_TIER_MAP = {
        ModelTier.FINANCIAL.value: "FINANCIAL_MODEL",
        ModelTier.MARKET.value: "MARKET_MODEL",
        ModelTier.NEWS.value: "NEWS_MODEL",
        ModelTier.RISK.value: "RISK_MODEL",
        ModelTier.PORTFOLIO.value: "PORTFOLIO_MODEL",
        ModelTier.REASONING.value: "REASONING_MODEL",
        ModelTier.FAST.value: "FAST_MODEL",
        ModelTier.EVALUATION.value: "EVALUATION_MODEL",
        ModelTier.SYNTHESIS.value: "SYNTHESIS_MODEL",
        ModelTier.DEFAULT.value: "REASONING_MODEL",
    }

    def __init__(
        self,
        model: str | ModelTier | None = None,
        token_budget_manager: TokenBudgetManager | None = None,
    ):
        self.model = self._resolve_model(model)
        self.provider = GroqProvider(model=self.model)
        self.token_budget_manager = (
            token_budget_manager
            if token_budget_manager is not None
            else get_default_token_budget_manager()
        )

    def __call__(self, messages: list[dict[str, str]]) -> str:
        return self.generate(messages)

    @classmethod
    def _resolve_model(cls, model: str | ModelTier | None) -> str | None:
        if model is None:
            return getattr(settings, "REASONING_MODEL", None) or getattr(
                settings,
                "GROQ_MODEL",
                None,
            )

        normalized = str(model).strip().lower()
        if normalized in cls._MODEL_TIER_MAP:
            return (
                getattr(settings, cls._MODEL_TIER_MAP[normalized], None)
                or getattr(settings, "GROQ_MODEL", None)
            )

        return model

    def _get_provider_output_ceiling(self) -> int:
        return int(
            getattr(settings, "GROQ_MAX_OUTPUT_TOKENS", 1000)
        )

    def _get_max_output_tokens(self, is_tool_call: bool = False) -> int:
        ceiling = self._get_provider_output_ceiling()
        if is_tool_call:
            configured = int(
                getattr(settings, "TOOL_CALL_MAX_COMPLETION_TOKENS", 512)
            )
        else:
            configured = int(
                getattr(settings, "REASONING_MAX_COMPLETION_TOKENS", 4096)
            )
        return min(configured, ceiling)

    def _record_provider_usage(self, response: Any = None) -> None:
        usage = getattr(self.provider, "last_usage", None)
        if usage is None and response is not None:
            usage_obj = getattr(response, "usage", None)
            if usage_obj is not None:
                p_tokens = getattr(usage_obj, "prompt_tokens", None)
                c_tokens = getattr(usage_obj, "completion_tokens", None)
                t_tokens = getattr(usage_obj, "total_tokens", None)
                if (
                    p_tokens is not None
                    and c_tokens is not None
                    and t_tokens is not None
                ):
                    try:
                        usage = LLMUsage(
                            prompt_tokens=int(p_tokens),
                            completion_tokens=int(c_tokens),
                            total_tokens=int(t_tokens),
                            model=str(self.model),
                        )
                    except Exception:
                        usage = None

        if usage is not None:
            try:
                self.token_budget_manager.record_actual_usage(usage)
            except Exception:
                pass

    def generate(
        self,
        messages: list[dict[str, str]],
        max_completion_tokens: int | None = None,
    ) -> str:
        ceiling = self._get_provider_output_ceiling()
        if max_completion_tokens is not None:
            max_output_tokens = min(int(max_completion_tokens), ceiling)
        else:
            max_output_tokens = self._get_max_output_tokens(is_tool_call=False)

        self.token_budget_manager.validate_request_budget(
            messages=messages,
            max_output_tokens=max_output_tokens,
            tools=None,
        )
        content = self.provider.generate(
            messages=messages,
            max_completion_tokens=max_output_tokens,
        )
        self._record_provider_usage()
        return content

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ):
        max_output_tokens = self._get_max_output_tokens(is_tool_call=True)
        self.token_budget_manager.validate_request_budget(
            messages=messages,
            max_output_tokens=max_output_tokens,
            tools=tools,
        )
        response = self.provider.generate_with_tools(
            messages=messages,
            tools=tools,
            max_completion_tokens=max_output_tokens,
        )
        self._record_provider_usage(response=response)
        return response