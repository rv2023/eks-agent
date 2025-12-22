# app/phase5_models.py
from pydantic import BaseModel
from typing import List

class Phase5Request(BaseModel):
    session_id: str
    plane: str
    verified_evidence_summaries: List[str]
    phase3_summary: str
    hypotheses: list


class Phase5Response(BaseModel):
    summary: str
    root_cause: str
    evidence_used: List[str]
    confidence: str
    suggested_human_actions: List[str]
    safety_note: str
