import json
import os
import time
import uuid
from typing import Any, Dict

def now_ms() -> int:
    return int(time.time() * 1000)

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def audit_write(audit_dir: str, record: Dict[str, Any]) -> str:
    ensure_dir(audit_dir)
    record = dict(record)
    record.setdefault("ts_ms", now_ms())
    record.setdefault("event_id", str(uuid.uuid4()))
    # one file per event for simplicity + immutability
    out_path = os.path.join(audit_dir, f'{record["ts_ms"]}_{record["event_id"]}.json')
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return out_path
