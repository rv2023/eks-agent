from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

# ---- Config (IMPORT MODULE, NOT ATTRIBUTE) ----
import app.config as config

# ---- Core imports ----
from app.audit import audit_write
from app.bedrock import BedrockClient
from app.prompts import build_prompt
from app.allowlist import load_allowlist, AllowlistError
from app.state import get_store
from app.evidence.models import Evidence

# ---- Phase 2 ----
from app.phase2 import phase2_plan, detect_plane
from app.phase2_grounding import ingest_grounding

# ---- Phase 3 ----
from app.phase3 import run_phase3
from app.phase3_models import Phase3Request, Phase3Response

# ======================================================
# FastAPI App (MUST be created before decorators)
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
    request_id: str = Field(..., description="Client-generated request id for audit correlation")
    need: str = Field(..., description="What capability you want (e.g., ingress, logging)")

# ======================================================
# Phase 3 Route
# ======================================================

@app.post("/phase3/reason", response_model=Phase3Response)
def phase3_reason(req: Phase3Request):
    return run_phase3(req)

# ======================================================
# Routes
# ======================================================

@app.post("/llm-test")
def llm_test(body: LLMTestIn):
    if not body.tier2_evidence.strip():
        audit_write(config.settings.audit_dir, {
            "type": "refuse",
            "request_id": body.request_id,
            "reason": "missing_tier2_evidence",
            "question": body.question,
        })
        raise HTTPException(
            status_code=400,
            detail="Tier-2 evidence is required. Provide verified tool output."
        )

    prompt = build_prompt(tier2=body.tier2_evidence)
    client = BedrockClient(config.settings.aws_region)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt + "\nQUESTION:\n" + body.question
                    }
                ]
            }
        ]
    }

    try:
        output = client.invoke(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            body=payload
        )
    except Exception as e:
        audit_write(config.settings.audit_dir, {
            "type": "error",
            "request_id": body.request_id,
            "stage": "bedrock_invoke",
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=str(e))

    audit_write(config.settings.audit_dir, {
        "type": "llm_call",
        "request_id": body.request_id,
        "prompt": prompt,
        "question": body.question,
        "response": output,
    })

    return {"response": output}


@app.get("/health", response_model=HealthOut)
def health():
    try:
        _ = load_allowlist(config.settings.allowlist_path)
        allowlist_loaded = True
    except Exception:
        allowlist_loaded = False

    return HealthOut(
        ok=True,
        aws_region=config.settings.aws_region,
        allowlist_loaded=allowlist_loaded
    )


@app.post("/suggest-components")
def suggest_components(body: SuggestComponentsIn):
    try:
        allowlist = load_allowlist(config.settings.allowlist_path)
    except AllowlistError as e:
        audit_write(config.settings.audit_dir, {
            "type": "deny",
            "request_id": body.request_id,
            "reason": f"allowlist_error: {str(e)}",
            "input": body.model_dump(),
        })
        raise HTTPException(status_code=400, detail=f"Allowlist invalid: {str(e)}")

    cats = allowlist.get("categories", {})

    if all((not v) for v in cats.values()):
        audit_write(config.settings.audit_dir, {
            "type": "deny",
            "request_id": body.request_id,
            "reason": "allowlist_empty_fail_closed",
            "input": body.model_dump(),
        })
        raise HTTPException(
            status_code=403,
            detail="Allowlist is empty. Provide enabled components allowlist to get recommendations."
        )

    audit_write(config.settings.audit_dir, {
        "type": "noop",
        "request_id": body.request_id,
        "reason": "mvp_placeholder",
        "input": body.model_dump(),
    })

    return {
        "ok": True,
        "note": "MVP placeholder. Phase 3 will implement allowlist-only recommendations."
    }


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


@app.post("/ask")
@app.post("/ask")
def ask(body: AskIn):
    store = get_store(body.session_id)
    namespace = body.hints.get("namespace", "default")

    # -------------------------------
    # Phase 2 — Evidence enforcement
    # -------------------------------
    plan = phase2_plan(store, namespace)

    if plan:
        audit_write(config.settings.audit_dir, {
            "type": "phase2_need_evidence",
            "session_id": body.session_id,
            "missing": plan.missing,
            "commands": [c.command for c in plan.commands],
        })

        return {
            "mode": "need_evidence",
            "missing": plan.missing,
            "commands": [c.__dict__ for c in plan.commands],
        }

    # -------------------------------
    # Phase 3 — Reasoning
    # -------------------------------
    plane = detect_plane(store, namespace)

    phase3_req = Phase3Request(
        session_id=body.session_id,
        question=body.question,
        plane=plane,
    )

    resp = run_phase3(phase3_req)

    audit_write(config.settings.audit_dir, {
        "type": "ask_complete",
        "session_id": body.session_id,
        "plane": plane,
        "question": body.question,
    })

    return {
        "mode": "answer",
        "plane": plane,
        "analysis": resp.model_dump(),
    }


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
        "namespace": body.namespace,
        "kube_context": body.kube_context,
        "result": out,
    })

    return out


@app.post("/phase2/plan")
def phase2_plan_endpoint(session_id: str, namespace: str = "default"):
    store = get_store(session_id)

    plan = phase2_plan(store, namespace)
    plane = detect_plane(store, namespace)

    if plan:
        audit_write(config.settings.audit_dir, {
            "type": "phase2_need_evidence",
            "session_id": session_id,
            "plane": plane,
            "missing": plan.missing,
            "commands": [c.command for c in plan.commands],
        })

        return {
            "mode": "need_evidence",
            "plane": plane,
            "missing": plan.missing,
            "commands": [c.__dict__ for c in plan.commands],
        }

    audit_write(config.settings.audit_dir, {
        "type": "phase2_complete",
        "session_id": session_id,
        "plane": plane,
    })

    return {
        "mode": "ready",
        "plane": plane,
        "next": "phase3",
    }
