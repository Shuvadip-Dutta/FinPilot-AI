from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str
    content: str


class SentimentResult(BaseModel):
    label: str
    confidence: float
    source: str | None = None


class AggregatedSentiment(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    unavailable: int = 0
    average_confidence: float = 0.0


class AgentResult(BaseModel):
    response: str
    tools_used: list[str]
    data: dict[str, object] | None = None