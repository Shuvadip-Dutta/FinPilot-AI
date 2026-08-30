"""Typed contracts for deterministic model evaluation."""

from typing import Literal

from pydantic import BaseModel


EvaluationCategory = Literal[
    "finance",
    "market",
    "news",
    "risk",
    "portfolio",
]


class EvaluationCase(BaseModel):
    """A single objectively gradable finance-model benchmark case."""

    case_id: str
    category: EvaluationCategory
    question: str
    reference_answer: str
    required_concepts: list[str]


class EvaluationResult(BaseModel):
    """Deterministic evaluation outcome for one benchmark case."""

    case_id: str
    category: EvaluationCategory
    question: str
    response: str
    passed: bool
    score: float
    missing_concepts: list[str]


class EvaluationReport(BaseModel):
    """Aggregate outcome for a collection of evaluation cases."""

    total_cases: int
    passed_cases: int
    failed_cases: int
    average_score: float
    results: list[EvaluationResult]
