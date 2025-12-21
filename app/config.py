import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    aws_profile: str = os.getenv("AWS_PROFILE", "default")
    allowlist_path: str = os.getenv("ALLOWLIST_PATH", "allowlist.yaml")
    audit_dir: str = os.getenv("AUDIT_DIR", "runtime/audit")

settings = Settings()
