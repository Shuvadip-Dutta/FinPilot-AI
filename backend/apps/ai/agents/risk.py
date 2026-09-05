"""Reasoning-layer risk synthesis over specialist research results."""

import json
from collections.abc import Callable

from pydantic import ValidationError

from apps.ai.agents.base import BaseAgent
from apps.ai.exceptions import LLMError
from apps.ai.graph.contracts import ProviderProvenance, ResearchContext
from apps.ai.graph.state import AgentState
from apps.ai.services.llm_service import LLMService
from apps.ai.services.schemas import AgentResult
from apps.ai.services.token_budget import (
    DegradationTier,
    get_default_token_budget_manager,
)

LLMCallable = Callable[[list[dict[str, str]]], str]


class RiskAnalysisAgent(BaseAgent):
    """Interpret specialist results into a qualitative risk assessment."""

    RISK_CONTEXT_CHAR_LIMIT = 9000
    SPECIALIST_PROSE_CHAR_LIMIT = 700

    def __init__(
        self,
        llm_service: LLMCallable | None = None,
    ):
        self.llm_service = llm_service or LLMService(model="risk")

    @property
    def name(self) -> str:
        return "risk"

    def run(self, state: AgentState | ResearchContext) -> AgentResult:
        research_context: ResearchContext | None = None
        ticker: str | None = None

        if isinstance(state, ResearchContext):
            research_context = state
            ticker = research_context.ticker
            financial_result = None
            market_result = None
            news_result = None
        else:
            ticker = state.ticker
            financial_result = self._coerce_result(state.results.get("financial"))
            market_result = self._coerce_result(state.results.get("market"))
            news_result = self._coerce_result(state.results.get("news"))

        has_financial = (financial_result is not None) or (research_context is not None and research_context.financials is not None)
        has_market = (market_result is not None) or (research_context is not None and research_context.market_data is not None)
        has_news = (news_result is not None) or (research_context is not None and research_context.news is not None)

        missing_information = []
        if not has_financial:
            missing_information.append("Financial research data is unavailable.")
        if not has_market:
            missing_information.append("Current market data is unavailable.")
        if not has_news:
            missing_information.append("News intelligence is unavailable.")

        if not (has_financial or has_market or has_news):
            response = (
                f"Risk analysis for {ticker or 'the requested company'}: "
                + " ".join(missing_information)
            )
            return AgentResult(response=response, tools_used=[])

        if self.llm_service is None:
            self.llm_service = LLMService(model="risk")

        tier = self._get_degradation_tier()

        # Collect section provenance from research_context or AgentResult data
        provenance_dict: dict[str, dict] = {}
        if research_context and research_context.provenance:
            provenance_dict = {
                sec: prov.model_dump() for sec, prov in research_context.provenance.items()
            }
        else:
            for agent_name, res in (("financial", financial_result), ("market", market_result), ("news", news_result)):
                if res and isinstance(res.data, dict) and "provenance" in res.data:
                    p_data = res.data["provenance"]
                    if isinstance(p_data, dict):
                        provenance_dict.update(p_data)

        evidence: dict[str, object] = {
            "financial": financial_result.data if financial_result else (research_context.model_dump().get("financials") if research_context else None),
            "market": market_result.data if market_result else (research_context.model_dump().get("market_data") if research_context else None),
            "news": news_result.data if news_result else (research_context.model_dump().get("news") if research_context else None),
            "missing_information": missing_information,
        }
        if provenance_dict:
            evidence["provenance"] = provenance_dict

        if tier == DegradationTier.EXHAUSTED:
            return AgentResult(
                response=(
                    f"Risk analysis for {ticker or 'the requested company'} could not be completed: "
                    "the LLM budget is exhausted."
                ),
                tools_used=[],
                data=evidence,
            )

        messages = self._build_risk_messages(
            state=state if isinstance(state, AgentState) else AgentState(user_message=f"Risk analysis for {ticker}", ticker=ticker),
            financial_result=financial_result,
            market_result=market_result,
            news_result=news_result,
            missing_information=missing_information,
            tier=tier,
        )

        max_tokens = self._get_max_completion_tokens_for_tier(tier)

        try:
            response = self._call_llm(messages, max_completion_tokens=max_tokens)
        except LLMError:
            raise

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    f"Unable to analyze risk for {ticker or 'the requested company'}: "
                    "the reasoning model returned an empty response."
                ),
                tools_used=[],
                data=evidence,
            )

        return AgentResult(response=response.strip(), tools_used=[], data=evidence)


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
            return 1000
        if tier == DegradationTier.CRITICAL:
            return 512
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
        tier: DegradationTier = DegradationTier.NORMAL,
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
            tier=tier,
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
        tier: DegradationTier = DegradationTier.NORMAL,
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

        if tier == DegradationTier.CRITICAL:
            compact_context = make_context(0)
            compact_context["FINANCIAL STRUCTURED EVIDENCE"] = self._compact_financial_evidence(financial_data)
            compact_context["MARKET STRUCTURED EVIDENCE"] = self._compact_market_evidence(market_data)
            compact_context["NEWS STRUCTURED EVIDENCE"] = self._compact_news_evidence(news_data)
            return compact_context

        prose_limits = (350, 150) if tier == DegradationTier.CONSTRAINED else (self.SPECIALIST_PROSE_CHAR_LIMIT, 350, 150)

        for prose_limit in prose_limits:
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