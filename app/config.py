import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    max_phase2_iterations: int = 5
    max_ask_loops: int = 10
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_profile: str = os.getenv("AWS_PROFILE", "default")
    bedrock_model_id: str = os.getenv(
        "BEDROCK_MODEL_ID",
        "anthropic.claude-3-sonnet-20240229-v1:0"
    )
    allowlist_path: str = os.getenv("ALLOWLIST_PATH", "allowlist.yaml")
    audit_dir: str = os.getenv("AUDIT_DIR", "runtime/audit")


# ✅ REQUIRED: module-level instance
settings = Settings()
