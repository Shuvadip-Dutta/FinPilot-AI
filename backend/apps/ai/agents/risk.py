"""Reasoning-layer risk synthesis over specialist research results."""

import json
from collections.abc import Callable

from pydantic import ValidationError

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import LLMError
from apps.ai.graph.state import AgentState
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult

LLMCallable = Callable[[list[dict[str, str]]], str]


class RiskAnalysisAgent(BaseAgent):
    """Interpret specialist results into a qualitative risk assessment."""

    RISK_CONTEXT_CHAR_LIMIT = 9000
    SPECIALIST_PROSE_CHAR_LIMIT = 700

    def __init__(
        self,
        llm_service: LLMCallable | None = None,
    ):
        self.llm_service = llm_service

    @property
    def name(self) -> str:
        return "risk"

    def run(self, state: AgentState) -> AgentResult:
        financial_result = self._coerce_result(state.results.get("financial"))
        market_result = self._coerce_result(state.results.get("market"))
        news_result = self._coerce_result(state.results.get("news"))

        missing_information = []
        if financial_result is None:
            missing_information.append("Financial research data is unavailable.")
        if market_result is None:
            missing_information.append("Current market data is unavailable.")
        if news_result is None:
            missing_information.append("News intelligence is unavailable.")

        available_results = [
            result for result in (financial_result, market_result, news_result) if result is not None
        ]
        if not available_results:
            response = (
                f"Risk analysis for {state.ticker or 'the requested company'}: "
                + " ".join(missing_information)
            )
            return AgentResult(response=response, tools_used=[])

        if self.llm_service is None:
            self.llm_service = LLMService(model="reasoning")

        messages = self._build_risk_messages(
            state=state,
            financial_result=financial_result,
            market_result=market_result,
            news_result=news_result,
            missing_information=missing_information,
        )

        try:
            response = self.llm_service(messages)
        except LLMError:
            raise

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    f"Unable to analyze risk for {state.ticker or 'the requested company'}: "
                    "the reasoning model returned an empty response."
                ),
                tools_used=[],
            )

        return AgentResult(response=response.strip(), tools_used=[])

    @staticmethod
    def _coerce_result(value: object) -> AgentResult | None:
        if isinstance(value, dict):
            try:
                value = AgentResult.model_validate(value)
            except ValidationError:
                return None
        if isinstance(value, AgentResult) and value.response.strip():
            return value
        return None

    def _build_risk_messages(
        self,
        state: AgentState,
        financial_result: AgentResult | None,
        market_result: AgentResult | None,
        news_result: AgentResult | None,
        missing_information: list[str],
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are the risk interpretation specialist for FinPilot AI. "
            "Synthesize only the supplied specialist outputs. Identify financial risk signals from the financial research, "
            "market risk signals from the market research, and news/sentiment risks from the news intelligence. "
            "Explain reinforcing signals across categories and conflicting signals when present. Distinguish observed facts from interpretation. "
            "Explicitly identify missing information. Explain which signals contribute most to the overall risk picture and avoid overstating weak evidence. "
            "Do not invent unsupported quantitative risk metrics. Never invent or fabricate values for VaR, beta, Sharpe ratio, volatilities, drawdown, stock prices, dates, sentiment scores, or other quantitative risk metrics not contained in the supplied context. "
            "Keep the analysis qualitative unless the specialist results already include actual quantitative measurements. "
            "Do not make investment recommendations. Do not guarantee outcomes. Do not present speculative future events as facts. "
            "Do not claim certainty about future performance. Never create numbers or metrics that are not present in the provided research context."
            " Prefer structured specialist evidence over prose for factual and quantitative values. "
            "Use authoritative market quotes and historical data when supplied. "
            "Use authoritative news sentiment counts when supplied; do not reconstruct them from prose."
        )

        context = self._build_bounded_context(
            state,
            financial_result,
            market_result,
            news_result,
            missing_information,
        )

        serialized_context = json.dumps(
            context,
            ensure_ascii=False,
            default=str,
        )

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": serialized_context,
            },
        ]

    def _build_bounded_context(
        self,
        state: AgentState,
        financial_result: AgentResult | None,
        market_result: AgentResult | None,
        news_result: AgentResult | None,
        missing_information: list[str],
    ) -> dict[str, object]:
        financial_data = (
            self._reduce_financial_evidence(financial_result.data)
            if financial_result is not None and financial_result.data is not None
            else "Financial structured evidence is unavailable."
        )
        market_data = (
            self._reduce_market_evidence(market_result.data)
            if market_result is not None and market_result.data is not None
            else "Market structured evidence is unavailable."
        )
        news_data = (
            self._reduce_news_evidence(news_result.data)
            if news_result is not None and news_result.data is not None
            else "News structured evidence is unavailable."
        )

        def make_context(prose_limit: int) -> dict[str, object]:
            return {
                "FINANCIAL RESEARCH": self._bounded_prose(
                    financial_result, "Financial research data is unavailable.", prose_limit
                ),
                "FINANCIAL STRUCTURED EVIDENCE": financial_data,
                "MARKET RESEARCH": self._bounded_prose(
                    market_result, "Current market data is unavailable.", prose_limit
                ),
                "MARKET STRUCTURED EVIDENCE": market_data,
                "NEWS INTELLIGENCE": self._bounded_prose(
                    news_result, "News intelligence is unavailable.", prose_limit
                ),
                "NEWS STRUCTURED EVIDENCE": news_data,
                "MISSING INFORMATION": missing_information,
                "USER MESSAGE": self._bounded_text(state.user_message, 300),
                "TICKER": state.ticker,
                "MARKET": state.market,
                "INSTRUCTION": "Provide a focused risk interpretation based only on the supplied specialist outputs; do not invent unsupported quantitative risk metrics.",
            }

        for prose_limit in (self.SPECIALIST_PROSE_CHAR_LIMIT, 350, 150):
            candidate = make_context(prose_limit)
            if self._serialized_size(candidate) <= self.RISK_CONTEXT_CHAR_LIMIT:
                return candidate

        compact_context = make_context(0)
        compact_context["FINANCIAL STRUCTURED EVIDENCE"] = self._compact_financial_evidence(financial_data)
        compact_context["MARKET STRUCTURED EVIDENCE"] = self._compact_market_evidence(market_data)
        compact_context["NEWS STRUCTURED EVIDENCE"] = self._compact_news_evidence(news_data)
        return compact_context

    @staticmethod
    def _serialized_size(value: object) -> int:
        return len(json.dumps(value, ensure_ascii=False, default=str))

    @staticmethod
    def _bounded_text(value: object, limit: int) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        boundary = text.rfind(" ", 0, limit + 1)
        return (text[: boundary if boundary > 0 else limit].rstrip() + "...")

    @classmethod
    def _bounded_prose(
        cls,
        result: AgentResult | None,
        unavailable_message: str,
        limit: int,
    ) -> str:
        if result is None:
            return unavailable_message
        return cls._bounded_text(result.response, limit) if limit else ""

    @staticmethod
    def _compact_financial_evidence(data: object) -> object:
        if not isinstance(data, dict):
            return data
        compact = {key: data[key] for key in ("ticker", "market") if key in data}
        for key in ("financials", "financial_statement_data", "key_metrics", "key_metrics_data"):
            value = data.get(key)
            if isinstance(value, list) and value:
                compact[key] = value[:1]
        return compact

    @staticmethod
    def _compact_market_evidence(data: object) -> object:
        if not isinstance(data, dict):
            return data
        compact = {key: data[key] for key in ("ticker", "market") if key in data}
        for key in ("market_data", "current_market_data"):
            value = data.get(key)
            if isinstance(value, dict) and isinstance(value.get("quotes"), list):
                compact[key] = {"quotes": value["quotes"]}
        return compact

    @staticmethod
    def _compact_news_evidence(data: object) -> object:
        if not isinstance(data, dict):
            return data
        compact = {key: data[key] for key in ("ticker", "market", "aggregated_sentiment") if key in data}
        articles = data.get("articles")
        if isinstance(articles, list):
            compact["articles"] = articles[:3]
        return compact

    @staticmethod
    def _reduce_financial_evidence(data: dict[str, object]) -> dict[str, object]:
        risk_terms = (
            "revenue", "income", "profit", "cash", "debt", "liabil", "asset",
            "equity", "margin", "roe", "roa", "roce", "leverage", "interest",
            "ebitda", "earning", "working_capital",
        )

        reduced: dict[str, object] = {
            key: value
            for key, value in data.items()
            if key in {"ticker", "market", "context_reduction_applied", "omitted_information"}
            or (
                not isinstance(value, (dict, list))
                and any(term in key.lower() for term in risk_terms)
            )
        }
        for key in ("financials", "financial_statement_data"):
            statements = data.get(key)
            if not isinstance(statements, list):
                continue
            selected_statements = []
            for statement in statements[-3:]:
                if not isinstance(statement, dict):
                    continue
                selected = {
                    field: statement[field]
                    for field in (
                        "statement_type", "period", "fiscal_year", "end_date",
                        "period_type", "period_length",
                    )
                    if field in statement
                }
                metrics = statement.get("metrics")
                if isinstance(metrics, list):
                    selected["metrics"] = [
                        metric for metric in metrics
                        if isinstance(metric, dict)
                        and any(
                            term in str(metric.get("key", metric.get("name", ""))).lower()
                            for term in risk_terms
                        )
                    ][:8]
                selected_statements.append(selected)
            if selected_statements:
                reduced[key] = selected_statements

        for key in ("key_metrics", "key_metrics_data"):
            metrics = data.get(key)
            if isinstance(metrics, list):
                reduced[key] = [
                    metric for metric in metrics
                    if isinstance(metric, dict)
                    and any(
                        term in str(metric.get("key", metric.get("name", ""))).lower()
                        for term in risk_terms
                    )
                ][:16]
        return reduced

    @staticmethod
    def _reduce_market_evidence(data: dict[str, object]) -> dict[str, object]:
        reduced = {
            key: value
            for key, value in data.items()
            if key in {"ticker", "market"}
        }
        for key in ("market_data", "current_market_data"):
            value = data.get(key)
            if isinstance(value, dict):
                quotes = value.get("quotes")
                if isinstance(quotes, list):
                    reduced[key] = {
                        **{field: value[field] for field in value if field != "quotes"},
                        "quotes": [
                            {
                                field: quote[field]
                                for field in (
                                    "exchange", "price", "percent_change", "year_high", "year_low",
                                )
                                if field in quote
                            }
                            for quote in quotes
                            if isinstance(quote, dict)
                        ],
                    }
        for key in ("historical_data", "historical_market_data"):
            value = data.get(key)
            if isinstance(value, dict):
                candles = value.get("candles")
                if isinstance(candles, list):
                    reduced[key] = {
                        **{field: value[field] for field in value if field != "candles"},
                        "candles": candles[-20:],
                    }
        return reduced

    @staticmethod
    def _reduce_news_evidence(data: dict[str, object]) -> dict[str, object]:
        reduced = {
            key: data[key]
            for key in ("ticker", "market", "aggregated_sentiment")
            if key in data
        }
        articles = data.get("articles")
        if isinstance(articles, list):
            reduced["articles"] = [
                {
                    field: article[field]
                    for field in ("title", "source", "relevance_type", "sentiment")
                    if field in article
                }
                for article in articles
                if isinstance(article, dict)
            ]
        article_sentiment = data.get("article_level_sentiment")
        if isinstance(article_sentiment, list):
            reduced["article_level_sentiment"] = [
                {
                    field: article[field]
                    for field in ("title", "source", "relevance_type", "sentiment")
                    if field in article
                }
                for article in article_sentiment
                if isinstance(article, dict)
            ]
        return reduced

    @staticmethod
    def _preferred_evidence(
        result: AgentResult | None,
        unavailable_message: str,
    ) -> object:
        if result is None:
            return unavailable_message
        return result.response