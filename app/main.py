from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.config import settings
from app.audit import audit_write
from app.allowlist import load_allowlist, AllowlistError

app = FastAPI(title="EKS Agent (MVP)", version="0.0.1")

class HealthOut(BaseModel):
    ok: bool
    aws_region: str
    allowlist_loaded: bool
    allowlist_fail_closed: bool = True

@app.get("/health", response_model=HealthOut)
def health():
    allowlist_loaded = False
    try:
        _ = load_allowlist(settings.allowlist_path)
        allowlist_loaded = True
    except Exception:
        allowlist_loaded = False
    return HealthOut(ok=True, aws_region=settings.aws_region, allowlist_loaded=allowlist_loaded)

class SuggestComponentsIn(BaseModel):
    request_id: str = Field(..., description="Client-generated request id for audit correlation")
    need: str = Field(..., description="What capability you want (e.g., ingress, logging)")

@app.post("/suggest-components")
def suggest_components(body: SuggestComponentsIn):
    # FAIL CLOSED until allowlist is properly filled
    try:
        allowlist = load_allowlist(settings.allowlist_path)
    except AllowlistError as e:
        audit_write(settings.audit_dir, {
            "type": "deny",
            "request_id": body.request_id,
            "reason": f"allowlist_error: {str(e)}",
            "input": body.model_dump(),
        })
        raise HTTPException(status_code=400, detail=f"Allowlist invalid: {str(e)}")
    # If allowlist categories are empty, deny recommendations.
    cats = allowlist.get("categories", {})
    if all((not v) for v in cats.values()):
        audit_write(settings.audit_dir, {
            "type": "deny",
            "request_id": body.request_id,
            "reason": "allowlist_empty_fail_closed",
            "input": body.model_dump(),
        })
        raise HTTPException(
            status_code=403,
            detail="Allowlist is empty. Provide enabled components allowlist to get recommendations."
        )

    # MVP: do not actually recommend anything yet—Phase 3 will implement real enforcement and suggestions.
    audit_write(settings.audit_dir, {
        "type": "noop",
        "request_id": body.request_id,
        "reason": "mvp_placeholder",
        "input": body.model_dump(),
    })
    return {"ok": True, "note": "MVP placeholder. Phase 3 will implement allowlist-only recommendations."}
