# app/evidence/store.py
from typing import List, Dict
from .models import Evidence


class EvidenceStore:
    """
    Session-scoped evidence store.

    - items: immutable evidence collected via Phase 2 / Phase 4
    - meta: mutable session metadata (loop counters, guards, etc.)
    """

    def __init__(self):
        # Verified evidence (append-only)
        self.items: List[Evidence] = []

        # Session-level metadata (NOT evidence)
        # Safe for counters, circuit breakers, flags
        self.meta: Dict[str, int | str | bool] = {}

    # ----------------------------
    # Evidence operations
    # ----------------------------

    def add(self, ev: Evidence):
        """
        Append verified evidence.
        Evidence should be immutable after insertion.
        """
        self.items.append(ev)

    def empty(self) -> bool:
        return len(self.items) == 0

    # ----------------------------
    # Session metadata helpers
    # ----------------------------

    def get_meta(self, key: str, default=None):
        return self.meta.get(key, default)

    def set_meta(self, key: str, value):
        self.meta[key] = value

    # ----------------------------
    # Debug / audit helpers
    # ----------------------------

    def as_text(self) -> str:
        """
        Human-readable dump for debugging / audits.
        """
        blocks = []
        for e in self.items:
            blocks.append(
                f"[{e.id}] {e.tool} @ {e.timestamp}\n"
                f"summary: {e.summary}\n"
                f"meta: {e.meta}\n"
                f"raw:\n{e.raw}"
            )
        return "\n\n---\n\n".join(blocks)
