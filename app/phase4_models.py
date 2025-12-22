# app/phase4_models.py
from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


PlannerMode = Literal["need_evidence", "verification_complete"]


class Phase4Check(BaseModel):
    """
    Structured optional check produced by Phase 3 (LLM output).
    Phase 4 refuses anything unstructured.
    """
    id: str
    kind: str
    targets: Dict[str, str] = Field(default_factory=dict)
    rationale_hypothesis_id: str
    description: str


class VerificationPlanItem(BaseModel):
    check_id: str
    description: str
    evidence_type: str
    read_only_command: str
    rationale: Dict[str, str]
    evidence_key: str


class Phase4Response(BaseModel):
    mode: PlannerMode
    verification_plan: List[VerificationPlanItem] = Field(default_factory=list)
