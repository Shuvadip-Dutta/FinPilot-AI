"""Final synthesis agent for combining multi-agent analysis."""

import json
from collections.abc import Callable

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


LLMGenerate = Callable[[list[dict[str, str]]], str]


class FinalSynthesisAgent(BaseAgent):
    """Combine specialist evidence into a user-facing synthesis."""

    SYNTHESIS_CONTEXT_CHAR_LIMIT = 9000

    def __init__(
        self,
        llm_service: LLMGenerate | None = None,
    ):
        self.llm_service = llm_service or LLMService(model="synthesis").generate

    @property
    def name(self) -> str:
        return "synthesis"

    def run(
        self,
        state: AgentState,
    ) -> AgentResult:
        """Synthesize the available workflow results."""
        tier = self._get_degradation_tier()
        tools_used = self._collect_specialist_tools_used(state)

        if tier == DegradationTier.EXHAUSTED:
            evidence = self._collect_structured_evidence(state)
            missing_info = evidence.get("missing_information", [])

            available_keys = [
                key.replace("_optimization", "").replace("_", " ").title()
                for key, val in state.results.items()
                if isinstance(val, AgentResult) and val.response and val.response.strip()
            ]
            available_str = (
                f"Available specialist results: {', '.join(available_keys)}."
                if available_keys
                else "No specialist results available."
            )
            missing_str = (
                f" Missing: {' '.join(missing_info)}"
                if missing_info
                else ""
            )

            return AgentResult(
                response=(
                    f"Final synthesis for {state.ticker or 'the requested company'} could not be completed: "
                    f"the LLM budget is exhausted. {available_str}{missing_str}"
                ),
                tools_used=tools_used,
                data=evidence,
            )

        context = self._build_context(state, tier=tier)
        messages = self._build_messages(state, context)
        max_tokens = self._get_max_completion_tokens_for_tier(tier)

        try:
            response = self._call_llm(messages, max_completion_tokens=max_tokens)
        except LLMError:
            raise
        except (ValueError, TypeError) as exc:
            return AgentResult(
                response=(
                    "Unable to generate the final synthesis: "
                    f"{exc}"
                ),
                tools_used=tools_used,
                data=self._collect_structured_evidence(state),
            )

        if not isinstance(response, str) or not response.strip():
            return AgentResult(
                response=(
                    "Unable to generate the final synthesis: "
                    "the language model returned an empty response."
                ),
                tools_used=tools_used,
                data=self._collect_structured_evidence(state),
            )

        all_tools = list(tools_used)
        if "llm_synthesis" not in all_tools:
            all_tools.append("llm_synthesis")

        return AgentResult(
            response=response.strip(),
            tools_used=all_tools,
            data=self._collect_structured_evidence(state),
        )

    @classmethod
    def build_canonical_context(
        cls,
        state: AgentState,
    ) -> ResearchContext:
        """Construct a unified ResearchContext from specialist results in AgentState when structured models are available."""
        if state.research_context is not None:
            ctx = state.research_context
            for key in ("financial", "market", "news", "risk"):
                res = state.results.get(key)
                if isinstance(res, AgentResult) and isinstance(res.data, dict):
                    p_dict = res.data.get("provenance")
                    if isinstance(p_dict, dict):
                        for sec_name, prov_val in p_dict.items():
                            if sec_name not in ctx.provenance and isinstance(prov_val, dict):
                                status_val = str(prov_val.get("data_status") or "complete")
                                ctx.provenance[sec_name] = ProviderProvenance(
                                    primary_provider=str(prov_val.get("primary_provider") or prov_val.get("source") or "upstox"),
                                    source=str(prov_val.get("source") or prov_val.get("provider_used") or "upstox"),
                                    fallback_used=bool(prov_val.get("fallback_used", False)),
                                    data_status=status_val if status_val in ("complete", "partial", "empty", "failed") else "complete",
                                    fallback_reason=str(prov_val.get("fallback_reason")) if prov_val.get("fallback_reason") else None,
                                )
            return ctx

        ticker = state.ticker or ""
        market = state.market or "IN"
        provenance_dict: dict[str, ProviderProvenance] = {}

        for key in ("financial", "market", "news", "risk"):
            res = state.results.get(key)
            if isinstance(res, AgentResult) and isinstance(res.data, dict):
                p_dict = res.data.get("provenance")
                if isinstance(p_dict, dict):
                    for sec_name, prov_val in p_dict.items():
                        if isinstance(prov_val, dict):
                            status_val = str(prov_val.get("data_status") or "complete")
                            provenance_dict[sec_name] = ProviderProvenance(
                                primary_provider=str(prov_val.get("primary_provider") or prov_val.get("source") or "upstox"),
                                source=str(prov_val.get("source") or prov_val.get("provider_used") or "upstox"),
                                fallback_used=bool(prov_val.get("fallback_used", False)),
                                data_status=status_val if status_val in ("complete", "partial", "empty", "failed") else "complete",
                                fallback_reason=str(prov_val.get("fallback_reason")) if prov_val.get("fallback_reason") else None,
                            )

        return ResearchContext(
            ticker=ticker,
            market=market,
            provenance=provenance_dict,
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
        if max_completion_tokens is not None:
            try:
                return self.llm_service(
                    messages, max_completion_tokens=max_completion_tokens
                )
            except TypeError:
                pass

        return self.llm_service(messages)

    @staticmethod
    def _collect_specialist_tools_used(state: AgentState) -> list[str]:
        tools: list[str] = []
        for value in state.results.values():
            if not isinstance(value, AgentResult):
                continue
            for tool in value.tools_used:
                if tool not in tools:
                    tools.append(tool)
        return tools

    @staticmethod
    def _collect_structured_evidence(state: AgentState) -> dict[str, object]:
        evidence: dict[str, object] = {}
        missing_information: list[str] = []

        ordered_names = [
            ("financial", "Financial analysis was not available."),
            ("market", "Market analysis was not available."),
            ("news", "News intelligence was not available."),
            ("risk", "Risk analysis was not available."),
            ("portfolio_optimization", "Portfolio analysis was not available."),
        ]

        provenance_dict: dict[str, dict] = {}

        for result_key, missing_text in ordered_names:
            val = state.results.get(result_key)
            if isinstance(val, AgentResult):
                if val.data is not None:
                    evidence[result_key] = val.data
                    if isinstance(val.data, dict) and "provenance" in val.data:
                        p_data = val.data["provenance"]
                        if isinstance(p_data, dict):
                            provenance_dict.update(p_data)
                if not val.response or not val.response.strip():
                    missing_information.append(missing_text)
            elif isinstance(val, dict):
                evidence[result_key] = val
                if "provenance" in val and isinstance(val["provenance"], dict):
                    provenance_dict.update(val["provenance"])
            elif val is not None:
                evidence[result_key] = str(val)
            else:
                missing_information.append(missing_text)

        if provenance_dict:
            evidence["provenance"] = provenance_dict

        evidence["missing_information"] = missing_information
        if state.errors:
            evidence["workflow_errors"] = state.errors
        return evidence

    @staticmethod
    def _build_messages(
        state: AgentState,
        context: dict[str, object],
    ) -> list[dict[str, str]]:
        system_prompt = (
            "You are the final synthesis specialist for FinPilot AI. "
            "Answer the user's original request directly using the supplied specialist outputs as evidence. "
            "Synthesize specialist findings rather than merely repeating their raw text. "
            "Prioritize evidence provided by the specialists, preserve important supplied numerical values exactly, and reconcile conflicting findings when present. "
            "Structured specialist evidence is authoritative for numerical values and deterministic outputs; use it over prose when they differ. "
            "Identify uncertainty, disagreement, and important missing information. Distinguish factual observations from interpretation. "
            "Do not invent financial, market, news, sentiment, portfolio, or risk data. Do not create unsupported quantitative metrics. "
            "Never invent dates, prices, percentages, allocations, ratios, returns, or other values. "
            "Never claim an action was executed unless the supplied context explicitly confirms it. "
            "Avoid guarantees or certainty about future market performance. Avoid unconditional buy/sell recommendations. "
            "Do not independently retrieve external information or recalculate portfolio optimization metrics. "
            "If portfolio optimization or risk results are supplied, explain them using the exact values provided and do not replace them with unsupported values. "
            "Do not describe a company as debt-heavy or highly leveraged unless the structured evidence contains sufficient debt or leverage measurements; otherwise state that leverage cannot be assessed from the supplied data. "
            "Use only the information provided in the context. Clearly mark missing or unavailable information and do not fabricate it. "
            "Remain concise but useful."
        )

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "USER REQUEST": state.user_message,
                        "SPECIALIST EVIDENCE": context,
                        "SYNTHESIS INSTRUCTIONS": [
                            "Answer the user's original request directly.",
                            "Synthesize specialist outputs rather than restating them verbatim.",
                            "Use only the evidence supplied by specialists and workflow metadata.",
                            "Preserve important numerical values exactly as provided.",
                            "Reconcile inconsistencies and note uncertainty or disagreement.",
                            "Highlight missing information and workflow errors when relevant.",
                            "Distinguish facts from interpretation.",
                            "Do not invent unsupported facts or metrics.",
                            "Do not claim future performance certainty or provide unconditional recommendations.",
                        ],
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ]

    @staticmethod
    def _build_context(
        state: AgentState,
        tier: DegradationTier = DegradationTier.NORMAL,
    ) -> dict[str, object]:
        sections: dict[str, object] = {}
        missing_information: list[str] = []

        ordered_names = [
            ("financial", "FINANCIAL ANALYSIS", "Financial analysis was not available."),
            ("market", "MARKET ANALYSIS", "Market analysis was not available."),
            ("news", "NEWS INTELLIGENCE", "News intelligence was not available."),
            ("risk", "RISK ANALYSIS", "Risk analysis was not available."),
            ("portfolio_optimization", "PORTFOLIO ANALYSIS", "Portfolio analysis was not available."),
        ]

        for result_key, title, missing_text in ordered_names:
            value = state.results.get(result_key)
            if isinstance(value, AgentResult):
                if value.response and value.response.strip():
                    sections[title] = {
                        "response": FinalSynthesisAgent._bounded_response(
                            value.response,
                            result_key,
                        ),
                        "tools_used": value.tools_used,
                    }
                    if value.data is not None:
                        sections[title]["data"] = FinalSynthesisAgent._reduce_data(
                            result_key,
                            value.data,
                        )
                else:
                    sections[title] = {
                        "response": "No specialist response was produced.",
                        "tools_used": value.tools_used,
                    }
            elif value is not None:
                sections[title] = {
                    "response": str(value),
                    "tools_used": [],
                }
            else:
                missing_information.append(missing_text)

        if state.errors:
            sections["WORKFLOW ERRORS / MISSING INFORMATION"] = {
                "workflow_errors": state.errors,
                "missing_information": missing_information or ["No additional missing specialist information was recorded."],
            }
        elif missing_information:
            sections["WORKFLOW ERRORS / MISSING INFORMATION"] = {
                "workflow_errors": [],
                "missing_information": missing_information,
            }

        sections["_CONTEXT_METADATA"] = {
            "missing_information": missing_information,
        }

        if tier == DegradationTier.CRITICAL:
            for title, section in sections.items():
                if isinstance(section, dict) and "response" in section:
                    section["response"] = FinalSynthesisAgent._bounded_text(
                        section["response"],
                        150 if title != "PORTFOLIO ANALYSIS" else 300,
                    )
                if isinstance(section, dict) and "data" in section:
                    section["data"] = FinalSynthesisAgent._minimum_data(section["data"])
                if isinstance(section, dict):
                    section.pop("tools_used", None)
            sections["_CONTEXT_METADATA"] = {"missing_information": missing_information}
            return sections

        if tier == DegradationTier.CONSTRAINED:
            for title, section in sections.items():
                if isinstance(section, dict) and "response" in section:
                    section["response"] = FinalSynthesisAgent._bounded_text(
                        section["response"],
                        350 if title != "PORTFOLIO ANALYSIS" else 700,
                    )
            sections["_CONTEXT_METADATA"] = {"missing_information": missing_information}
            if FinalSynthesisAgent._serialized_size(sections) <= FinalSynthesisAgent.SYNTHESIS_CONTEXT_CHAR_LIMIT:
                return sections

        if FinalSynthesisAgent._serialized_size(sections) <= FinalSynthesisAgent.SYNTHESIS_CONTEXT_CHAR_LIMIT:
            return sections

        # Preserve structured evidence first; reduce only explanatory prose and optional metadata.
        for title, section in sections.items():
            if isinstance(section, dict) and "response" in section:
                section["response"] = FinalSynthesisAgent._bounded_text(
                    section["response"],
                    350 if title != "PORTFOLIO ANALYSIS" else 700,
                )
        sections["_CONTEXT_METADATA"] = {"missing_information": []}
        if FinalSynthesisAgent._serialized_size(sections) > FinalSynthesisAgent.SYNTHESIS_CONTEXT_CHAR_LIMIT:
            for title, section in sections.items():
                if not isinstance(section, dict):
                    continue
                if "response" in section:
                    section["response"] = FinalSynthesisAgent._bounded_text(
                        section["response"],
                        150 if title != "PORTFOLIO ANALYSIS" else 300,
                    )
                if "data" in section:
                    section["data"] = FinalSynthesisAgent._minimum_data(section["data"])
                section.pop("tools_used", None)
        if FinalSynthesisAgent._serialized_size(sections) > FinalSynthesisAgent.SYNTHESIS_CONTEXT_CHAR_LIMIT:
            sections = {
                title: section
                for title, section in sections.items()
                if title in {
                    "FINANCIAL ANALYSIS", "MARKET ANALYSIS", "NEWS INTELLIGENCE",
                    "RISK ANALYSIS", "PORTFOLIO ANALYSIS",
                }
            }
        return sections

    @staticmethod
    def _serialized_size(value: object) -> int:
        return len(json.dumps(value, ensure_ascii=False, default=str))

    @staticmethod
    def _bounded_text(value: object, limit: int) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        boundary = text.rfind(" ", 0, limit + 1)
        return text[: boundary if boundary > 0 else limit].rstrip() + "..."

    @classmethod
    def _bounded_response(cls, response: str, result_key: str) -> str:
        limits = {
            "financial": 600,
            "market": 500,
            "news": 600,
            "risk": 700,
            "portfolio_optimization": 1200,
        }
        return cls._bounded_text(response, limits.get(result_key, 500))

    @staticmethod
    def _reduce_data(result_key: str, data: dict[str, object]) -> dict[str, object]:
        if result_key == "financial":
            return FinalSynthesisAgent._reduce_financial_data(data)
        if result_key == "market":
            return FinalSynthesisAgent._reduce_market_data(data)
        if result_key == "news":
            return FinalSynthesisAgent._reduce_news_data(data)
        return data

    @staticmethod
    def _reduce_financial_data(data: dict[str, object]) -> dict[str, object]:
        reduced = {key: data[key] for key in ("ticker", "market", "context_reduction_applied", "omitted_information") if key in data}
        for key in ("financial_statement_data", "financials"):
            records = data.get(key)
            if isinstance(records, list):
                reduced[key] = [
                    {
                        field: record[field]
                        for field in ("statement_type", "fiscal_year", "end_date", "period_type", "metrics")
                        if field in record
                    }
                    for record in records[-3:]
                    if isinstance(record, dict)
                ]
        for key in ("key_metrics_data", "key_metrics"):
            metrics = data.get(key)
            if isinstance(metrics, list):
                reduced[key] = [metric for metric in metrics[:16] if isinstance(metric, dict)]
        return reduced

    @staticmethod
    def _reduce_market_data(data: dict[str, object]) -> dict[str, object]:
        reduced = {key: data[key] for key in ("ticker", "market") if key in data}
        for key in ("market_data", "current_market_data"):
            value = data.get(key)
            if isinstance(value, dict) and isinstance(value.get("quotes"), list):
                reduced[key] = {
                    "quotes": [quote for quote in value["quotes"] if isinstance(quote, dict)]
                }
        for key in ("historical_data", "historical_market_data"):
            value = data.get(key)
            if isinstance(value, dict) and isinstance(value.get("candles"), list):
                reduced[key] = {"candles": value["candles"][-10:]}
        return reduced

    @staticmethod
    def _reduce_news_data(data: dict[str, object]) -> dict[str, object]:
        reduced = {key: data[key] for key in ("ticker", "market", "aggregated_sentiment") if key in data}
        for key in ("articles", "article_level_sentiment"):
            articles = data.get(key)
            if isinstance(articles, list):
                reduced[key] = [
                    {
                        field: article[field]
                        for field in ("title", "source", "relevance_type", "sentiment")
                        if field in article
                    }
                    for article in articles[:5]
                    if isinstance(article, dict)
                ]
        return reduced

    @staticmethod
    def _minimum_data(data: object) -> object:
        if not isinstance(data, dict):
            return data
        minimum = {
            key: data[key]
            for key in ("ticker", "market", "aggregated_sentiment")
            if key in data
        }
        for key in ("market_data", "current_market_data"):
            value = data.get(key)
            if isinstance(value, dict) and isinstance(value.get("quotes"), list):
                minimum[key] = {"quotes": value["quotes"]}
        for key in ("financial_statement_data", "financials", "key_metrics_data", "key_metrics"):
            value = data.get(key)
            if isinstance(value, list) and value:
                minimum[key] = value[:1]
        for key in ("articles", "article_level_sentiment"):
            value = data.get(key)
            if isinstance(value, list):
                minimum[key] = value[:2]
        return minimum

    @staticmethod
    def _collect_tools_used(
        state: AgentState,
    ) -> list[str]:
        tools: list[str] = []

        for value in state.results.values():
            if not isinstance(value, AgentResult):
                continue

            for tool in value.tools_used:
                if tool not in tools:
                    tools.append(tool)

        if "llm_synthesis" not in tools:
            tools.append("llm_synthesis")

        return tools