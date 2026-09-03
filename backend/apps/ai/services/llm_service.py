from __future__ import annotations

from enum import Enum

from django.conf import settings

from apps.ai.services.providers.groq import GroqProvider


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

    def __init__(self, model: str | ModelTier | None = None):
        self.model = self._resolve_model(model)
        self.provider = GroqProvider(model=self.model)

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

    def generate(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        return self.provider.generate(messages)

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ):
        return self.provider.generate_with_tools(
            messages=messages,
            tools=tools,
        )