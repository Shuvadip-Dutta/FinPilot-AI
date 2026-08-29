from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str
    content: str
    
class AgentResult(BaseModel):
    response: str
    tools_used: list[str]