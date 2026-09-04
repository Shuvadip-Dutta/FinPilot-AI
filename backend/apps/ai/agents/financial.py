"""Deterministic agent for company financial analysis."""

import json
import re
from collections.abc import Callable
from datetime import datetime

from django.conf import settings

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import LLMError, ToolExecutionError
from apps.ai.services import research_tools
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    get_default_token_budget_manager,
)


ResearchTool = Callable[[str, str], dict[str, object]]
LLMCallable = Callable[[list[dict[str, str]]], str]


class FinancialAnalysisContextBuilder:
    """Prepare a bounded, deterministic financial-analysis prompt."""

    PRIORITY_METRICS = (
        "revenue",
        "total_revenue",
        "net_income",
        "profit_after_tax",
        "operating_income",
        "ebitda",
        "free_cash_flow",
        "operating_cash_flow",
        "cash_flow",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "current_assets",
        "current_liabilities",
        "gross_margin",
        "operating_margin",
        "ebitda_margin",
        "roe",
        "roa",
        "roce",
        "debt_to_equity",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    )

    def __init__(self, max_chars: int | None = None):
        configured_limit = getattr(
            settings,
            "FINANCIAL_ANALYSIS_CONTEXT_CHAR_LIMIT",
            18000,
        )
        self.max_chars = int(max_chars if max_chars is not None else configured_limit)

    def prepare(
        self,
        message: str,
        ticker: str,
        financials: dict[str, object],
        key_metrics: dict[str, object],
        tier: DegradationTier = DegradationTier.NORMAL,
    ) -> dict[str, object]:
        base_context = {
            "user_question": message,
            "ticker": ticker,
            "financial_statement_data": self._prepare_financial_statement_data(financials),
            "key_metrics_data": self._prepare_key_metrics_data(key_metrics),
        }

        if tier == DegradationTier.CONSTRAINED:
            reduced_context = self._apply_structural_reduction(base_context)
            return {
                **reduced_context,
                "context_reduction_applied": True,
                "omitted_information": (
                    "Older financial periods were omitted to keep the prompt within "
                    "the constrained quota budget while preserving recent, relevant "
                    "statement data and key metrics."
                ),
            }

        if tier == DegradationTier.CRITICAL:
            minimal_context = self._apply_minimal_reduction(base_context)
            return {
                **minimal_context,
                "context_reduction_applied": True,
                "omitted_information": (
                    "Older financial periods and non-essential fields were omitted to "
                    "keep the context within the critical quota budget."
                ),
            }

        if self._approximate_size(base_context) <= self.max_chars:
            return base_context

        reduced_context = self._apply_structural_reduction(base_context)
        if self._approximate_size(reduced_context) <= self.max_chars:
            return {
                **reduced_context,
                "context_reduction_applied": True,
                "omitted_information": (
                    "Older financial periods were omitted to keep the prompt within "
                    "the configured context budget while preserving recent, relevant "
                    "statement data and key metrics."
                ),
            }

        minimal_context = self._apply_minimal_reduction(base_context)
        if self._approximate_size(minimal_context) <= self.max_chars:
            return {
                **minimal_context,
                "context_reduction_applied": True,
                "omitted_information": (
                    "Older financial periods and lower-priority fields were omitted to "
                    "keep the context within the configured budget."
                ),
            }

        return {
            "user_question": message,
            "ticker": ticker,
            "financial_statement_data": "Financial statement data was omitted because the supplied dataset exceeded the configured context budget.",
            "key_metrics_data": "Key metrics were omitted because the supplied dataset exceeded the configured context budget.",
            "context_reduction_applied": True,
            "omitted_information": (
                "Context reduction was applied to keep the LLM prompt within the "
                "configured budget; no values were fabricated and older periods were "
                "discarded before low-priority fields."
            ),
        }

    def _prepare_financial_statement_data(
        self,
        financials: dict[str, object],
    ) -> list[dict[str, object]] | str:
        if not isinstance(financials, dict):
            return "No financial statement data was returned."

        records = list(financials.get("financials") or [])
        if not records:
            return "No financial statement data was returned."

        prepared: list[dict[str, object]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            metrics = record.get("metrics") or []
            prepared_metrics: list[dict[str, object]] = []
            for metric in metrics:
                if not isinstance(metric, dict):
                    continue
                prepared_metrics.append(
                    {
                        "name": metric.get("name"),
                        "key": metric.get("key"),
                        "value": metric.get("value"),
                    }
                )
            prepared.append(
                {
                    "statement_type": record.get("statement_type"),
                    "period": record.get("period"),
                    "fiscal_year": record.get("fiscal_year"),
                    "end_date": record.get("end_date"),
                    "period_type": record.get("period_type"),
                    "period_length": record.get("period_length"),
                    "metrics": prepared_metrics,
                }
            )

        return prepared or "No financial statement data was returned."

    def _prepare_key_metrics_data(
        self,
        key_metrics: dict[str, object],
    ) -> list[dict[str, object]] | str:
        if not isinstance(key_metrics, dict):
            return "No key metrics were returned."

        metrics = list(key_metrics.get("metrics") or [])
        if not metrics:
            return "No key metrics were returned."

        prepared: list[dict[str, object]] = []
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            prepared.append(
                {
                    "category": metric.get("category"),
                    "name": metric.get("name"),
                    "key": metric.get("key"),
                    "value": metric.get("value"),
                    "raw_value": metric.get("raw_value"),
                }
            )

        return prepared or "No key metrics were returned."

    def _apply_structural_reduction(
        self,
        context: dict[str, object],
    ) -> dict[str, object]:
        financial_statement_data = context.get("financial_statement_data")
        key_metrics_data = context.get("key_metrics_data")

        if isinstance(financial_statement_data, list):
            trimmed_statements = self._select_recent_statements(financial_statement_data)
        else:
            trimmed_statements = financial_statement_data

        if isinstance(key_metrics_data, list):
            trimmed_metrics = self._select_priority_metrics(key_metrics_data, limit=6)
        else:
            trimmed_metrics = key_metrics_data

        return {
            "user_question": context.get("user_question"),
            "ticker": context.get("ticker"),
            "financial_statement_data": trimmed_statements,
            "key_metrics_data": trimmed_metrics,
        }

    def _apply_minimal_reduction(
        self,
        context: dict[str, object],
    ) -> dict[str, object]:
        financial_statement_data = context.get("financial_statement_data")
        key_metrics_data = context.get("key_metrics_data")

        if isinstance(financial_statement_data, list):
            trimmed_statements = self._select_statement_summaries(financial_statement_data)
        else:
            trimmed_statements = financial_statement_data

        if isinstance(key_metrics_data, list):
            trimmed_metrics = self._select_priority_metrics(key_metrics_data, limit=5)
        else:
            trimmed_metrics = key_metrics_data

        return {
            "user_question": context.get("user_question"),
            "ticker": context.get("ticker"),
            "financial_statement_data": trimmed_statements,
            "key_metrics_data": trimmed_metrics,
        }

    def _select_recent_statements(
        self,
        statements: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        if not statements:
            return statements

        recent_by_type: dict[str, list[dict[str, object]]] = {}
        for statement in sorted(
            statements,
            key=self._statement_sort_key,
            reverse=True,
        ):
            statement_type = str(statement.get("statement_type") or "unknown")
            recent_by_type.setdefault(statement_type, []).append(statement)

        selected: list[dict[str, object]] = []
        for statement_type in sorted(recent_by_type, key=lambda value: value.casefold()):
            for statement in recent_by_type[statement_type][:1]:
                selected.append(
                    {
                        **statement,
                        "metrics": self._select_priority_metrics(
                            list(statement.get("metrics") or []),
                            limit=4,
                        ),
                    }
                )

        return sorted(selected, key=self._statement_sort_key, reverse=True)

    def _select_statement_summaries(
        self,
        statements: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        selected = self._select_recent_statements(statements)
        summary: list[dict[str, object]] = []
        seen: set[str] = set()
        for statement in selected:
            statement_type = str(statement.get("statement_type") or "unknown")
            if statement_type in seen:
                continue
            seen.add(statement_type)
            summary.append(
                {
                    "statement_type": statement.get("statement_type"),
                    "fiscal_year": statement.get("fiscal_year"),
                    "end_date": statement.get("end_date"),
                    "period_type": statement.get("period_type"),
                    "period_length": statement.get("period_length"),
                    "metrics": self._select_priority_metrics(
                        list(statement.get("metrics") or []),
                        limit=3,
                    ),
                }
            )
        return summary

    def _select_priority_metrics(
        self,
        metrics: list[dict[str, object]],
        limit: int = 12,
    ) -> list[dict[str, object]]:
        if not metrics:
            return metrics

        prioritized = sorted(
            metrics,
            key=lambda item: (
                self._metric_priority(item),
                str(item.get("name") or item.get("key") or "").casefold(),
            ),
        )
        return prioritized[:limit]

    def _metric_priority(self, metric: dict[str, object]) -> int:
        key = str(metric.get("key") or metric.get("name") or "").casefold()
        for position, candidate in enumerate(self.PRIORITY_METRICS):
            if candidate in key:
                return position
        return len(self.PRIORITY_METRICS)

    @staticmethod
    def _statement_sort_key(statement: dict[str, object]) -> tuple[int, str, str]:
        raw_value = statement.get("end_date") or statement.get("fiscal_year") or "0000"
        value = str(raw_value)
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
            year = parsed.year
        except ValueError:
            try:
                year = int(re.search(r"(\d{4})", value).group(1))
            except (AttributeError, TypeError, ValueError):
                year = 0

        return (year, str(statement.get("statement_type") or "").casefold(), value)

    @staticmethod
    def _approximate_size(value: object) -> int:
        return len(json.dumps(value, ensure_ascii=False, default=str))


class FinancialAnalysisAgent(BaseAgent):
    """Retrieve financial data and interpret it with the reasoning model."""

    def __init__(
        self,
        financials_tool: ResearchTool | None = None,
        key_metrics_tool: ResearchTool | None = None,
        ticker: str | None = None,
        market: str = "IN",
        llm_service: LLMCallable | None = None,
    ):
        self.financials_tool = (
            financials_tool or research_tools.get_financials
        )
        self.key_metrics_tool = (
            key_metrics_tool or research_tools.get_key_metrics
        )
        self.ticker = ticker.upper() if ticker else None
        self.market = market.upper()
        self.max_context_chars = int(
            getattr(settings, "FINANCIAL_ANALYSIS_CONTEXT_CHAR_LIMIT", 18000)
        )
        self.llm_service = llm_service or LLMService(model="financial")

    @property
    def name(self) -> str:
        return "financial"

    def run(self, message: str) -> AgentResult:
        """Return a deterministic financial-data summary interpreted by LLM."""
        ticker = self.ticker or self._extract_ticker(message)

        if ticker is None:
            return AgentResult(
                response=(
                    "Please provide a ticker symbol to analyze financials."
                ),
                tools_used=[],
            )

        tools_used: list[str] = []

        try:
            financials = self.financials_tool(
                ticker=ticker,
                market=self.market,
            )
            tools_used.append("get_financials")

            key_metrics = self.key_metrics_tool(
                ticker=ticker,
                market=self.market,
            )
            tools_used.append("get_key_metrics")
        except (ToolExecutionError, ValueError, TypeError) as exc:
            return AgentResult(
                response=(
                    f"Unable to retrieve financial analysis for {ticker}: {exc}"
                ),
                tools_used=tools_used,
            )

        tier = self._get_degradation_tier()
        context_builder = FinancialAnalysisContextBuilder(max_chars=self.max_context_chars)

        if tier == DegradationTier.EXHAUSTED:
            evidence = context_builder.prepare(
                message=message,
                ticker=ticker,
                financials=financials,
                key_metrics=key_metrics,
            )
            return AgentResult(
                response=(
                    f"Financial analysis for {ticker} could not be completed: "
                    "the LLM budget is exhausted."
                ),
                tools_used=tools_used,
                data=evidence,
            )

        messages = self._build_analysis_messages(
            message=message,
            ticker=ticker,
            financials=financials,
            key_metrics=key_metrics,
            tier=tier,
        )
        self._enforce_context_budget(messages)

        max_tokens = self._get_max_completion_tokens_for_tier(tier)

        try:
            response = self._call_llm(messages, max_completion_tokens=max_tokens)
        except LLMError:
            raise

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    "Unable to analyze financials for "
                    f"{ticker}: the reasoning model returned an empty response."
                ),
                tools_used=tools_used,
            )

        return AgentResult(
            response=response.strip(),
            tools_used=tools_used,
            data=json.loads(messages[1]["content"]),
        )

    def _get_degradation_tier(self) -> DegradationTier:
        manager = getattr(self.llm_service, "token_budget_manager", None)
        if manager is None and hasattr(self.llm_service, "__self__"):
            manager = getattr(
                self.llm_service.__self__, "token_budget_manager", None
            )

        if manager is not None and hasattr(manager, "get_degradation_tier"):
            res = manager.get_degradation_tier()
            if isinstance(res, DegradationTier):
                return res

        return get_default_token_budget_manager().get_degradation_tier()

    @staticmethod
    def _get_max_completion_tokens_for_tier(tier: DegradationTier) -> int | None:
        if tier == DegradationTier.CONSTRAINED:
            return 2000
        if tier == DegradationTier.CRITICAL:
            return 1000
        return None

    def _call_llm(
        self,
        messages: list[dict[str, str]],
        max_completion_tokens: int | None = None,
    ) -> str:
        try:
            if isinstance(self.llm_service, LLMService):
                return self.llm_service.generate(
                    messages, max_completion_tokens=max_completion_tokens
                )
        except TypeError:
            pass

        if max_completion_tokens is not None:
            try:
                return self.llm_service(
                    messages, max_completion_tokens=max_completion_tokens
                )
            except TypeError:
                pass

        return self.llm_service(messages)

    @staticmethod
    def _extract_ticker(message: str) -> str | None:
        """Extract an explicit all-caps ticker without using an LLM."""
        excluded_words = {
            "ANALYZE",
            "FINANCIAL",
            "FINANCIALS",
            "METRICS",
            "REVENUE",
            "PROFIT",
            "EARNINGS",
            "SHOW",
            "WHAT",
        }

        for candidate in re.findall(r"\b[A-Z]{2,10}\b", message):
            if candidate not in excluded_words:
                return candidate

        return None

    def _enforce_context_budget(self, messages: list[dict[str, str]]) -> None:
        if len(messages) < 2:
            return
        payload = messages[1].get("content", "")
        if len(payload) > self.max_context_chars:
            raise ValueError(
                "Financial analysis context exceeded the configured budget before "
                "calling the reasoning model."
            )

    def _build_analysis_messages(
        self,
        message: str,
        ticker: str,
        financials: dict[str, object],
        key_metrics: dict[str, object],
        tier: DegradationTier = DegradationTier.NORMAL,
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are the financial analysis specialist for FinPilot AI. "
            "Use only the financial data provided in this prompt. "
            "Identify trends across multiple periods when available, "
            "discuss profitability and financial condition when supported, "
            "call out notable strengths and weaknesses, and explain important "
            "metrics when relevant. Distinguish factual observations from "
            "interpretation. State when information is unavailable and never "
            "invent missing values or infer precise facts that are not supported "
            "by the supplied data. Do not promise future returns or performance."
        )

        context_builder = FinancialAnalysisContextBuilder(max_chars=self.max_context_chars)
        context = context_builder.prepare(
            message=message,
            ticker=ticker,
            financials=financials,
            key_metrics=key_metrics,
            tier=tier,
        )

        payload = json.dumps(
            context,
            ensure_ascii=False,
            default=str,
        )
        if len(payload) > self.max_context_chars:
            raise ValueError(
                "Financial analysis context exceeded the configured budget after "
                "deterministic reduction."
            )

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": payload,
            },
        ]

