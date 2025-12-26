# eks_agent/tools/render.py

import json
from typing import Any

MAX_CHARS = 8000
MAX_LIST_ITEMS = 20


def _safe_json(obj: Any) -> str:
    """
    Best-effort JSON serialization that NEVER throws.
    """
    try:
        return json.dumps(obj, indent=2, default=str)
    except Exception:
        return json.dumps(str(obj), indent=2)


def _truncate(text: str, limit: int = MAX_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...<truncated>..."


def render_tool_evidence(results: list[dict]) -> str:
    """
    Render tool execution results in a stable, LLM-friendly format.

    Input contract:
    [
      {
        "kind": str,
        "namespace": str | None,
        "name": str | None,
        "output": dict | list | scalar
      }
    ]
    """

    lines: list[str] = []

    for r in results:
        lines.append(f"- kind: {r.get('kind')}")
        if r.get("namespace") is not None:
            lines.append(f"  namespace: {r.get('namespace')}")
        if r.get("name") is not None:
            lines.append(f"  name: {r.get('name')}")

        output = r.get("output")

        # -----------------------------
        # LIST output (most common)
        # -----------------------------
        if isinstance(output, list):
            lines.append(f"  output_type: list")
            lines.append(f"  item_count: {len(output)}")

            sliced = output[:MAX_LIST_ITEMS]
            payload = _safe_json(sliced)

            payload = _truncate(payload)
            lines.append("  output:")
            for ln in payload.splitlines():
                lines.append(f"    {ln}")

            if len(output) > MAX_LIST_ITEMS:
                lines.append(
                    f"    ... ({len(output) - MAX_LIST_ITEMS} more items omitted)"
                )

        # -----------------------------
        # SINGLE object
        # -----------------------------
        else:
            lines.append("  output_type: object")
            payload = _safe_json(output)
            payload = _truncate(payload)

            lines.append("  output:")
            for ln in payload.splitlines():
                lines.append(f"    {ln}")

        lines.append("")  # spacing between tool calls

    return "\n".join(lines)