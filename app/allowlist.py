from typing import Any, Dict, List
import yaml

class AllowlistError(Exception):
    pass

def load_allowlist(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "categories" not in data:
        raise AllowlistError("allowlist.yaml missing required key: categories")
    return data

def is_component_allowed(allowlist: Dict[str, Any], category: str, name: str) -> bool:
    cats = allowlist.get("categories", {})
    allowed: List[str] = cats.get(category, []) or []
    return name in allowed
