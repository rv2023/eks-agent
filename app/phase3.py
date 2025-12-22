import json
from fastapi import HTTPException

import app.config as config
from app.bedrock import BedrockClient
from app.audit import audit_write
from app.evidence.store import EvidenceStore

from app.phase3_models import Phase3Request, Phase3Response
from app.phase3_prompts import phase3_system_prompt, phase3_user_prompt


def run_phase3(req: Phase3Request) -> Phase3Response:
    # -------------------------------------------------
    # Load immutable Tier-2 evidence (Phase 2 output)
    # -------------------------------------------------
    evidence = EvidenceStore.load(req.session_id)
    summaries = [e.summary for e in evidence]
    allowed = set(summaries)

    # -------------------------------------------------
    # Explicit stop if no evidence
    # -------------------------------------------------
    if not summaries:
        resp = Phase3Response(
            plane=req.plane,
            summary="Insufficient Tier-2 evidence to reason safely.",
            hypotheses=[],
            optional_next_checks=[
                "Collect relevant read-only evidence before reasoning."
            ],
        )
        audit_write(
            config.settings.audit_dir,
            {
                "type": "phase3_no_evidence",
                "session_id": req.session_id,
                "response": resp.model_dump(),
            },
        )
        return resp

    # -------------------------------------------------
    # Build deterministic reasoning prompt
    # -------------------------------------------------
    sys_prompt = phase3_system_prompt()
    usr_prompt = phase3_user_prompt(req.question, req.plane, summaries)

    # -------------------------------------------------
    # Call Bedrock (reasoning only)
    # -------------------------------------------------
    try:
        client = BedrockClient(region=config.settings.aws_region)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": sys_prompt + "\n\n" + usr_prompt
                        }
                    ],
                }
            ],
        }

        raw = client.invoke(
            model_id=config.settings.bedrock_model_id,
            body=body,
        )

        envelope = json.loads(raw)
        text = envelope["content"][0]["text"].strip()

        # Hard guard: JSON only
        if not text.startswith("{"):
            raise HTTPException(
                status_code=400,
                detail="Phase 3 model response was not pure JSON"
            )

        data = json.loads(text)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Bedrock failed: {e}"
        )

    # -------------------------------------------------
    # Validate response schema
    # -------------------------------------------------
    resp = Phase3Response.model_validate(data)

    # -------------------------------------------------
    # Enforce evidence integrity (NO invention)
    # -------------------------------------------------
    for h in resp.hypotheses:
        for ev in h.evidence:
            if ev not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Hypothesis {h.id} cites unknown evidence: {ev}",
                )

    # -------------------------------------------------
    # Audit (full traceability)
    # -------------------------------------------------
    audit_write(
        config.settings.audit_dir,
        {
            "type": "phase3_complete",
            "session_id": req.session_id,
            "plane": req.plane,
            "question": req.question,
            "response": resp.model_dump(),
            "evidence_ids": [e.id for e in evidence],
        },
    )

    return resp