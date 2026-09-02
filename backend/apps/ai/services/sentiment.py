"""Finance-focused sentiment classification utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.ai.services.schemas import SentimentResult


@dataclass
class FinancialSentimentClassifier:
    """Lightweight financial sentiment interface with lazy model loading."""

    model_name: str | None = None
    device: str | None = None
    _model: Any = None

    def __post_init__(self):
        self.model_name = self.model_name or getattr(
            settings,
            "FINANCIAL_SENTIMENT_MODEL",
            "ProsusAI/finbert",
        )
        self.device = self.device or getattr(
            settings,
            "FINANCIAL_SENTIMENT_DEVICE",
            "cpu",
        )

    def _ensure_loaded(self):
        if self._model is not None:
            return self._model

        try:
            from transformers import pipeline
        except ImportError as exc:
            raise ImportError(
                "transformers is required for financial sentiment analysis."
            ) from exc

        self._model = pipeline(
            "text-classification",
            model=self.model_name,
            device=self.device,
        )
        return self._model

    @staticmethod
    def _normalize_label(label: str) -> str:
        normalized = str(label).lower()
        if "positive" in normalized or normalized.endswith("1"):
            return "positive"
        if "negative" in normalized or normalized.endswith("0"):
            return "negative"
        return "neutral"

    def __call__(self, text: str) -> SentimentResult:
        return self.classify(text)

    def classify(self, text: str) -> SentimentResult:
        if not isinstance(text, str) or not text.strip():
            return SentimentResult(label="neutral", confidence=0.0)

        model = self._ensure_loaded()
        result = model(text.strip())

        if isinstance(result, list) and result:
            prediction = result[0]
            label = str(prediction.get("label", "neutral"))
            confidence = float(prediction.get("score", 0.0))
            normalized_label = self._normalize_label(label)
            return SentimentResult(
                label=normalized_label,
                confidence=confidence,
                source=self.model_name,
            )

        return SentimentResult(label="neutral", confidence=0.0, source=self.model_name)
