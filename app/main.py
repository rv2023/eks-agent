from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

# ------------------------------------------------------
# Config
# ------------------------------------------------------
import app.config as config

# ------------------------------------------------------
# Core
# ------------------------------------------------------
from app.audit import audit_write
from app.bedrock import BedrockClient
from app.prompts import build_prompt
from app.allowlist import load_allowlist, AllowlistError
from app.state import get_store, get_session_meta
from app.evidence.models import Evidence

# ------------------------------------------------------
# Phase 2
# ------------------------------------------------------
from app.phase2 import phase2_plan, detect_plane
from app.phase2_grounding import ingest_grounding

# ------------------------------------------------------
# Phase 3
# ------------------------------------------------------
from app.phase3 import run_phase3
from app.phase3_models import Phase3Request, Phase3Response

# ------------------------------------------------------
# Phase 4
# ------------------------------------------------------
from app.phase4 import run_phase4

# ======================================================
# FastAPI App
# ======================================================
app = FastAPI(title="EKS Agent (MVP)", version="0.0.1")

# ======================================================
# Models
# ======================================================

class GroundingIn(BaseModel):
    session_id: str
    namespace: str = "default"
    kube_context: str | None = None


class AskIn(BaseModel):
    session_id: str
    question: str
    hints: dict = Field(default_factory=dict)


class LLMTestIn(BaseModel):
    request_id: str
    tier2_evidence: str
    question: str


class HealthOut(BaseModel):
    ok: bool
    aws_region: str
    allowlist_loaded: bool
    allowlist_fail_closed: bool = True


class SuggestComponentsIn(BaseModel):
    request_id: str
    need: str


# ======================================================
# Phase 3 direct endpoint (debug / internal)
# ======================================================

@app.post("/phase3/reason", response_model=Phase3Response)
def phase3_reason(req: Phase3Request):
    return run_phase3(req)


# ======================================================
# LLM test (explicit, non-agent path)
# ======================================================

@app.post("/llm-test")
def llm_test(body: LLMTestIn):
    if not body.tier2_evidence.strip():
        audit_write(config.settings.audit_dir, {
            "type": "refuse",
            "request_id": body.request_id,
            "reason": "missing_tier2_evidence",
        })
        raise HTTPException(status_code=400, detail="Tier-2 evidence is required.")

    prompt = build_prompt(tier2=body.tier2_evidence)
    client = BedrockClient(config.settings.aws_region)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0,
        "messages": [{
            "role": "user",
            "content": [{"type": "text", "text": prompt + "\nQUESTION:\n" + body.question}]
        }]
    }

    output = client.invoke(
        model_id=config.settings.bedrock_model_id,
        body=payload
    )

    audit_write(config.settings.audit_dir, {
        "type": "llm_call",
        "request_id": body.request_id,
    })

    return {"response": output}


# ======================================================
# Health
# ======================================================

@app.get("/health", response_model=HealthOut)
def health():
    try:
        load_allowlist(config.settings.allowlist_path)
        loaded = True
    except Exception:
        loaded = False

    return HealthOut(
        ok=True,
        aws_region=config.settings.aws_region,
        allowlist_loaded=loaded
    )


# ======================================================
# Suggest components (placeholder)
# ======================================================

@app.post("/suggest-components")
def suggest_components(body: SuggestComponentsIn):
    try:
        allowlist = load_allowlist(config.settings.allowlist_path)
    except AllowlistError as e:
        audit_write(config.settings.audit_dir, {
            "type": "deny",
            "request_id": body.request_id,
            "reason": str(e),
        })
        raise HTTPException(status_code=400, detail=str(e))

    cats = allowlist.get("categories", {})
    if all(not v for v in cats.values()):
        raise HTTPException(status_code=403, detail="Allowlist empty (fail-closed).")

    return {"ok": True, "note": "MVP placeholder"}


# ======================================================
# Evidence ingestion
# ======================================================

@app.post("/evidence")
def ingest_evidence(
    session_id: str = Body(...),
    kind: str = Body(...),
    raw: str = Body(...),
    meta: dict = Body(default={})
):
    store = get_store(session_id)
    ev = Evidence.create("user_paste", kind, raw, meta)
    store.add(ev)
    return {"ok": True, "evidence_id": ev.id}


# ======================================================
# Phase 2 endpoints
# ======================================================

@app.post("/phase2/grounding")
def phase2_grounding(body: GroundingIn):
    out = ingest_grounding(
        session_id=body.session_id,
        namespace=body.namespace,
        kube_context=body.kube_context,
    )
    audit_write(config.settings.audit_dir, {
        "type": "phase2_grounding",
        "session_id": body.session_id,
    })
    return out


@app.post("/phase2/plan")
def phase2_plan_endpoint(session_id: str, namespace: str = "default"):
    store = get_store(session_id)
    plan = phase2_plan(store, namespace)
    plane = detect_plane(store, namespace)

    if plan:
        return {
            "mode": "need_evidence",
            "plane": plane,
            "missing": plan.missing,
            "commands": [c.__dict__ for c in plan.commands],
        }

    return {"mode": "ready", "plane": plane}


# ======================================================
# /ask — FULL AGENT FLOW (Phase 1–4)
# ======================================================

@app.post("/ask")
def ask(body: AskIn):
    store = get_store(body.session_id)
    namespace = body.hints.get("namespace", "default")

    # -------------------------------
    # Circuit breaker (per session)
    # -------------------------------
    meta = get_session_meta(store)

    meta["ask_loops"] += 1
    if meta["ask_loops"] > config.settings.max_ask_loops:
        audit_write(config.settings.audit_dir, {
            "type": "circuit_breaker",
            "session_id": body.session_id,
            "reason": "max_ask_loops_exceeded",
            "count": meta["ask_loops"],
        })
        raise HTTPException(status_code=429, detail="Too many verification loops.")

    # ---------------- Phase 2 ----------------
    plan = phase2_plan(store, namespace)
    if plan:
        meta["phase2_runs"] += 1
        if meta["phase2_runs"] > config.settings.max_phase2_iterations:
            audit_write(config.settings.audit_dir, {
                "type": "circuit_breaker",
                "session_id": body.session_id,
                "reason": "max_phase2_iterations_exceeded",
            })
            raise HTTPException(status_code=429, detail="Too many evidence attempts.")

        return {
            "mode": "need_evidence",
            "phase": 2,
            "missing": plan.missing,
            "commands": [c.__dict__ for c in plan.commands],
        }

    # ---------------- Phase 3 ----------------
    plane = detect_plane(store, namespace)
    phase3_resp = run_phase3(
        Phase3Request(
            session_id=body.session_id,
            question=body.question,
            plane=plane,
        )
    )

    # ---------------- Phase 4 ----------------
    phase4_resp = run_phase4(
        session_id=body.session_id,
        plane=plane,
        phase3_output=phase3_resp.model_dump(),
    )

    if phase4_resp.mode == "need_evidence":
        return {
            "mode": "need_evidence",
            "phase": 4,
            "verification_plan": [p.model_dump() for p in phase4_resp.verification_plan],
        }

    # ---------------- FINAL -----------
    # ---- Phase 5 — Explanation (LLM, boxed) ----
    from app.phase5 import run_phase5
    from app.phase5_models import Phase5Request

    phase5_resp = run_phase5(
        Phase5Request(
            session_id=body.session_id,
            plane=plane,
            verified_evidence_summaries=[
                ev.summary for ev in get_store(body.session_id).items
            ],
            phase3_summary=phase3_resp.summary,
            hypotheses=phase3_resp.hypotheses,
        )
    )

    return {
        "mode": "answer",
        "phase": 5,
        "plane": plane,
        "analysis": phase3_resp.model_dump(),
        "verification": phase4_resp.model_dump(),
        "explanation": phase5_resp.model_dump(),
    }
