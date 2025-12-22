from typing import List, Literal
from pydantic import BaseModel, Field

Plane = Literal["WORKLOAD", "NETWORK", "CONTROL_PLANE", "NODE", "EXTERNAL"]
Confidence = Literal["low", "medium", "high"]


class Phase3Request(BaseModel):
    session_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    plane: Plane


class Hypothesis(BaseModel):
    id: str
    claim: str
    evidence: List[str]          # MUST be exact Evidence.summary
    confidence: Confidence


class Phase3Response(BaseModel):
    plane: Plane
    summary: str
    hypotheses: List[Hypothesis]
    optional_next_checks: List[str]