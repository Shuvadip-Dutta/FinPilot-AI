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
            from apps.ai.agents.financial import FinancialAnalysisAgent
            from apps.ai.agents.market import MarketAnalysisAgent
            from apps.ai.agents.news import NewsIntelligenceAgent
            from apps.ai.agents.risk import RiskAnalysisAgent
            from apps.ai.agents.synthesis import FinalSynthesisAgent
            from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
            from apps.ai.graph.router import WorkflowRouter

            workflow = LangGraphResearchWorkflow(
                router=WorkflowRouter(),
                financial_agent=FinancialAnalysisAgent(),
                market_agent=MarketAnalysisAgent(),
                news_agent=NewsIntelligenceAgent(),
                synthesis_agent=FinalSynthesisAgent(),
                risk_agent=RiskAnalysisAgent(),
            )
        self.workflow = workflow

    @classmethod
    def create_canonical(cls, policy: AgentToolPolicy | None = None) -> "AgentService":
        return cls(policy=policy)

    def run_workflow(
        self,
        message: str,
        user: object = None,
        ticker: str | None = None,
        market: str | None = None,
        thread_id: str = "default",
    ) -> AgentResult:
        if self.workflow is None:
            from apps.ai.agents.financial import FinancialAnalysisAgent
            from apps.ai.agents.market import MarketAnalysisAgent
            from apps.ai.agents.news import NewsIntelligenceAgent
            from apps.ai.agents.risk import RiskAnalysisAgent
            from apps.ai.agents.synthesis import FinalSynthesisAgent
            from apps.ai.graph.langgraph_workflow import LangGraphResearchWorkflow
            from apps.ai.graph.router import WorkflowRouter

            self.workflow = LangGraphResearchWorkflow(
                router=WorkflowRouter(),
                financial_agent=FinancialAnalysisAgent(),
                market_agent=MarketAnalysisAgent(),
                news_agent=NewsIntelligenceAgent(),
                synthesis_agent=FinalSynthesisAgent(),
                risk_agent=RiskAnalysisAgent(),
            )

        state = self.workflow.run(
            user_message=message,
            user=user,
            ticker=ticker,
            market=market,
            thread_id=thread_id,
        )

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
        thread_id: str = "default",
    ) -> AgentResult:
        return self.run_workflow(
            message=message,
            user=user,
            ticker=ticker,
            market=market,
            thread_id=thread_id,
        )


