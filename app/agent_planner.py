from dataclasses import dataclass
from typing import List

@dataclass
class ToolCommand:
    title: str
    command: str
    why: str
    signals: List[str]

@dataclass
class ToolPlan:
    missing: List[str]
    commands: List[ToolCommand]