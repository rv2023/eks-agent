# app/phase5.py
import json
import app.config as config
from app.audit import audit_write
from app.bedrock import BedrockClient
from app.phase5_models import Phase5Request, Phase5Response


def _phase5_system_prompt() -> str:
    return """
You are a senior Kubernetes SRE.

Rules:
- You MUST only explain using the provided verified evidence.
- You MUST NOT ask questions.
- You MUST NOT request more data.
- You MUST NOT generate commands.
- You MUST NOT suggest automated actions.
- You MAY suggest human actions in plain English only.

Output MUST be valid JSON matching the provided schema.
"""


def _phase5_user_prompt(req: Phase5Request) -> str:
    return f"""
VERIFIED CONTEXT:
Plane: {req.plane}

Evidence summaries:
{json.dumps(req.verified_evidence_summaries, indent=2)}

Phase 3 summary:
{req.phase3_summary}

Hypotheses:
{json.dumps(req.hypotheses, indent=2)}

TASK:
Explain the issue clearly for a human operator.
"""


def run_phase5(req: Phase5Request) -> Phase5Response:
    client = BedrockClient(region=config.settings.aws_region)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 600,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _phase5_system_prompt() + "\n\n" + _phase5_user_prompt(req)
                    }
                ],
            }
        ],
    }

    try:
        raw = client.invoke(
            model_id=config.settings.bedrock_model_id,
            body=payload,
        )
        data = json.loads(raw)
        text = data["content"][0]["text"].strip()

        if not text.startswith("{"):
            raise ValueError("Phase 5 response not JSON")

        parsed = json.loads(text)
        resp = Phase5Response.model_validate(parsed)

    except Exception as e:
        audit_write(
            config.settings.audit_dir,
            {
                "type": "phase5_error",
                "session_id": req.session_id,
                "error": str(e),
            },
        )
        raise

    audit_write(
        config.settings.audit_dir,
        {
            "type": "phase5_complete",
            "session_id": req.session_id,
            "response": resp.model_dump(),
        },
    )

    return resp