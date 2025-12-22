import json
import os
import time
import uuid
from typing import Any, Dict


def now_ms() -> int:
    """Current time in milliseconds."""
    return int(time.time() * 1000)


def ensure_dir(path: str) -> None:
    """Ensure audit directory exists."""
    os.makedirs(path, exist_ok=True)


def audit_write(audit_dir: str, record: Dict[str, Any]) -> str:
    """
    Write a single immutable audit record.

    - One file per event (append-only, immutable)
    - Caller controls structure of `record`
    - Timestamp and event_id are enforced here
    """
    ensure_dir(audit_dir)

    event = dict(record)
    event.setdefault("ts_ms", now_ms())
    event.setdefault("event_id", str(uuid.uuid4()))

    out_path = os.path.join(
        audit_dir,
        f'{event["ts_ms"]}_{event["event_id"]}.json'
    )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(event, f, ensure_ascii=False, indent=2)

    return out_path
