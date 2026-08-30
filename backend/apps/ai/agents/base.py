from abc import ABC, abstractmethod

from apps.ai.graph.state import AgentState
from apps.ai.services.schemas import AgentResult


class BaseAgent(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def run(
        self,
        input_data: str | AgentState,
    ) -> AgentResult:
        ...
