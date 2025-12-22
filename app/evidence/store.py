from typing import List
from .models import Evidence

class EvidenceStore:
    def __init__(self):
        self.items: List[Evidence] = []

    def add(self, ev: Evidence):
        self.items.append(ev)

    def empty(self) -> bool:
        return len(self.items) == 0

    def as_text(self) -> str:
        blocks = []
        for e in self.items:
            blocks.append(
                f"[{e.id}] {e.tool} @ {e.timestamp}\n"
                f"summary: {e.summary}\n"
                f"meta: {e.meta}\n"
                f"raw:\n{e.raw}"
            )
        return "\n\n---\n\n".join(blocks)