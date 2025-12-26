# eks_agent/tools/model.py
from pydantic import BaseModel
from typing import List, Optional

class ToolCall(BaseModel):
    kind: str
    namespace: Optional[str] = None
    name: Optional[str] = None
    why: Optional[str] = None


class ToolRequest(BaseModel):
    type: str = "tool_request"
    tools: List[ToolCall]

    @property
    def kubectl_commands(self) -> List[str]:
        cmds = []
        for t in self.tools:
            kind = t.kind.lower()
            ns = f"-n {t.namespace}" if t.namespace else ""

            if t.name:
                cmds.append(f"kubectl get {kind} {t.name} {ns}".strip())
            else:
                # LIST
                plural = kind + "s" if not kind.endswith("s") else kind
                cmds.append(f"kubectl get {plural} {ns}".strip())

        return cmds