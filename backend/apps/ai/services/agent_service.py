from datetime import date, datetime
import uuid
from django.shortcuts import get_object_or_404

from apps.ai.graph.portfolio_contracts import PortfolioWorkflowInput
from apps.ai.mcp.access import AgentToolPolicy
from apps.ai.services.schemas import AgentResult


class AgentService:

    def __init__(
        self,
        policy: AgentToolPolicy | None = None,
        workflow: object | None = None,
    ):
        self.policy = policy
        if workflow is None:
            self.workflow = self._create_default_workflow()
        else:
            self.workflow = workflow

    @classmethod
    def create_canonical(cls, policy: AgentToolPolicy | None = None) -> "AgentService":
        return cls(policy=policy)

    @staticmethod
    def _create_default_workflow():
        from apps.ai.agents.financial import FinancialAnalysisAgent
        from apps.ai.agents.market import MarketAnalysisAgent
        from apps.ai.agents.news import NewsIntelligenceAgent
        from apps.ai.agents.portfolio_optimization import PortfolioOptimizationAgent
        from apps.ai.agents.risk import RiskAnalysisAgent
        from apps.ai.agents.synthesis import FinalSynthesisAgent
        from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
        from apps.ai.graph.router import WorkflowRouter
        from apps.ai.portfolio.adapters import create_portfolio_market_data_adapter
        from apps.ai.portfolio.intelligence import PortfolioIntelligenceService

        return LangGraphResearchWorkflow(
            router=WorkflowRouter(),
            financial_agent=FinancialAnalysisAgent(),
            market_agent=MarketAnalysisAgent(),
            news_agent=NewsIntelligenceAgent(),
            synthesis_agent=FinalSynthesisAgent(),
            risk_agent=RiskAnalysisAgent(),
            portfolio_intelligence=PortfolioIntelligenceService(
                market_data_tool=create_portfolio_market_data_adapter()
            ),
            portfolio_optimization_agent=PortfolioOptimizationAgent(),
            portfolio_backtest_engine=None,   # default: instantiated lazily inside node
            portfolio_backtest_evaluator=None, # default: instantiated lazily inside node
        )


    def run_workflow(
        self,
        message: str,
        user: object = None,
        ticker: str | None = None,
        market: str | None = None,
        portfolio_input: PortfolioWorkflowInput | None = None,
        portfolio_id: str | uuid.UUID | None = None,
        thread_id: str = "default",
        reference_date: date | datetime | None = None,
    ) -> AgentResult:
        if self.workflow is None:
            self.workflow = self._create_default_workflow()

        if portfolio_id is not None:
            if user is None or getattr(user, "is_anonymous", False):
                raise ValueError("Authentication is required to access portfolio.")

            from apps.portfolio.models import Portfolio

            try:
                portfolio_pk = uuid.UUID(str(portfolio_id))
            except (ValueError, AttributeError, TypeError) as exc:
                raise ValueError(f"Invalid portfolio id '{portfolio_id}': expected a valid UUID.") from exc

            portfolio_orm = get_object_or_404(Portfolio, pk=portfolio_pk, user=user)

            if portfolio_input is None:
                from apps.portfolio.builder import PortfolioWorkflowInputBuilder

                include_opt = "optimiz" in message.casefold()
                builder = PortfolioWorkflowInputBuilder()
                portfolio_input = builder.build_workflow_input(
                    portfolio=portfolio_orm,
                    include_optimization=include_opt,
                )
            portfolio_input.django_portfolio_id = str(portfolio_orm.pk)

        from apps.ai.graph.router import WorkflowRouter

        if WorkflowRouter.is_backtest_intent(message):
            from apps.ai.portfolio.backtest_extractor import BacktestParameterExtractor

            extracted_config = BacktestParameterExtractor.extract(
                message, reference_date=reference_date
            )

            # Security guard: conversational backtest requires a trusted portfolio context
            if portfolio_input is None and portfolio_id is None:
                raise ValueError("A portfolio is required for backtesting.")

            # If an authenticated user is present and portfolio_input has a django_portfolio_id, verify ownership
            if (
                user is not None
                and not getattr(user, "is_anonymous", False)
                and portfolio_input is not None
                and portfolio_input.django_portfolio_id is not None
                and portfolio_id is None
            ):
                raw_id = str(portfolio_input.django_portfolio_id)
                if not raw_id.startswith(("synth-", "mock-", "test-")):
                    try:
                        portfolio_uuid = uuid.UUID(raw_id)
                    except (ValueError, AttributeError, TypeError) as exc:
                        raise ValueError(
                            f"Invalid portfolio id '{raw_id}': expected a valid UUID."
                        ) from exc

                    from apps.portfolio.models import Portfolio

                    get_object_or_404(Portfolio, pk=portfolio_uuid, user=user)

            if portfolio_input is not None:
                portfolio_input.include_backtest = True
                for field_name, val in extracted_config.to_workflow_kwargs().items():
                    setattr(portfolio_input, field_name, val)

        workflow_kwargs = {
            "user_message": message,
            "user": user,
            "ticker": ticker,
            "market": market,
            "thread_id": thread_id,
        }
        if portfolio_input is not None:
            workflow_kwargs["portfolio_input"] = portfolio_input

        state = self.workflow.run(**workflow_kwargs)

        response_text = ""
        tools_used: list[str] = []

        if "synthesis" in state.results:
            syn = state.results["synthesis"]
            if hasattr(syn, "response"):
                response_text = syn.response
            elif isinstance(syn, dict):
                response_text = syn.get("response", "")
        elif state.route and state.route in state.results:
            route_res = state.results[state.route]
            if hasattr(route_res, "response"):
                response_text = route_res.response
            elif isinstance(route_res, dict):
                response_text = route_res.get("response", "")

        if not response_text:
            for val in state.results.values():
                if hasattr(val, "response") and val.response:
                    response_text = val.response
                    break
                elif isinstance(val, dict) and val.get("response"):
                    response_text = val.get("response")
                    break

        for val in state.results.values():
            t_list = []
            if hasattr(val, "tools_used"):
                t_list = val.tools_used
            elif isinstance(val, dict):
                t_list = val.get("tools_used", [])
            if isinstance(t_list, list):
                for tool in t_list:
                    if tool not in tools_used:
                        tools_used.append(tool)

        data_payload: dict[str, object] = {
            "route": state.route,
            "ticker": state.ticker,
            "market": state.market,
        }
        if state.research_context and state.research_context.provenance:
            data_payload["provenance"] = {
                k: v.model_dump() for k, v in state.research_context.provenance.items()
            }

        return AgentResult(
            response=response_text,
            tools_used=tools_used,
            data=data_payload,
        )

    def run(
        self,
        message: str,
        user: object = None,
        ticker: str | None = None,
        market: str | None = None,
        portfolio_input: PortfolioWorkflowInput | None = None,
        portfolio_id: str | uuid.UUID | None = None,
        thread_id: str = "default",
        reference_date: date | datetime | None = None,
    ) -> AgentResult:
        return self.run_workflow(
            message=message,
            user=user,
            ticker=ticker,
            market=market,
            portfolio_input=portfolio_input,
            portfolio_id=portfolio_id,
            thread_id=thread_id,
            reference_date=reference_date,
        )
