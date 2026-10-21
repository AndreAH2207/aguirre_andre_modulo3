from enum import Enum

from pydantic import BaseModel, Field


class FinalAnswer(BaseModel):
    answer:str
    facts:list[str]=Field(default_factory=list)
    warnings:list[str]=Field(default_factory=list)


# The router decision is also a structured output.
class Route(str, Enum):
    RAG="rag"
    SQL="sql"
    TOOLS="tools"
    DIRECT="direct"
    CLARIFY="clarify"


class RouteDecision(BaseModel):
    route:Route
    confidence:float=Field(ge=0.0,le=1.0)
    reason:str
    clarification_question:str|None=None
