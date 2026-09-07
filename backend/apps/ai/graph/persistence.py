"""LangGraph PostgreSQL checkpoint persistence."""

import psycopg
from django.conf import settings
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class LangGraphPersistence:
    """Manage the lifecycle of a PostgreSQL LangGraph checkpointer."""

    def __init__(self):
        self._connection = None
        self.checkpointer = None

    def start(self) -> PostgresSaver:
        if not settings.LANGGRAPH_POSTGRES_URI:
            raise ValueError(
                "LANGGRAPH_POSTGRES_URI is not configured."
            )

        self._connection = psycopg.connect(
            settings.LANGGRAPH_POSTGRES_URI,
            autocommit=True,
        )

        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=[
                (
                    "apps.ai.services.schemas",
                    "AgentResult",
                ),
                (
                    "apps.ai.graph.portfolio_contracts",
                    "PortfolioWorkflowInput",
                ),
                (
                    "apps.ai.portfolio.schemas",
                    "PortfolioIntelligence",
                ),
                (
                    "apps.ai.portfolio.schemas",
                    "Portfolio",
                ),
                (
                    "apps.ai.portfolio.schemas",
                    "Holding",
                ),
                (
                    "apps.ai.portfolio.schemas",
                    "PortfolioRiskMetrics",
                ),
                (
                    "apps.ai.portfolio.optimization",
                    "OptimizationInput",
                ),
                (
                    "apps.ai.portfolio.optimization",
                    "OptimizationResult",
                ),
            ],
        )

        self.checkpointer = PostgresSaver(
            conn=self._connection,
            serde=serializer,
        )

        self.checkpointer.setup()

        return self.checkpointer

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self.checkpointer = None