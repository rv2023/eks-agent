from dataclasses import dataclass
from typing import Dict, Any, Literal
from datetime import datetime, timezone
import uuid

Tool = Literal["kubectl", "aws", "cloudwatch", "user_paste"]

@dataclass(frozen=True)
class Evidence:
    id: str
    tool: Tool
    timestamp: str
    summary: str
    raw: str
    meta: Dict[str, Any]

    @staticmethod
    def create(tool: Tool, summary: str, raw: str, meta: Dict[str, Any]):
        return Evidence(
            id=str(uuid.uuid4()),
            tool=tool,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            raw=raw,
            meta=meta,
        )

