# eks_agent/server.py

from fastapi import FastAPI
import json
from typing import Optional, Any, Tuple

from eks_agent.bedrock import ask_claude
from eks_agent.memory import add_message, get_messages
from eks_agent.prompts import SYSTEM_PROMPT

from eks_agent.rag.store import load_internal_docs
from eks_agent.rag.retrieve import build_index, retrieve_top_k
from eks_agent.rag.format import format_internal_refs

from eks_agent.tools.model import ToolRequest, ToolCall
from eks_agent.tools.k8s_reader import read_object
from eks_agent.tools.render import render_tool_evidence

# =========================================================
# App + global state
# =========================================================

app = FastAPI()

_INTERNAL_DOCS = load_internal_docs("internal_docs")
_INTERNAL_INDEX = build_index(_INTERNAL_DOCS)

_PENDING_TOOLS: dict[str, dict] = {}
_TOOL_HISTORY: dict[str, set[str]] = {}
_SESSION_SCOPE: dict[str, dict] = {}

_FORBIDDEN_KINDS = {"secret", "configmap"}

# =========================================================
# Helpers
# =========================================================

def validate_kind(kind: str):
    if kind.lower() in _FORBIDDEN_KINDS:
        raise ValueError(f"Access to {kind} is forbidden")

def tool_signature(t: ToolCall) -> str:
    return f"{t.kind}:{t.namespace}:{t.name}"

def requires_scope(t: ToolCall) -> bool:
    return t.name is None and t.namespace is None

def build_history_prompt(session_id: str) -> str:
    history = get_messages(session_id)
    return "".join(f"{m['role']}: {m['text']}\n" for m in history)

def wrap_input(text: str) -> str:
    tl = text.lower()
    if any(k in tl for k in ["exception", "traceback", "crash", "oom", "error"]):
        return f"<logs>\n{text}\n</logs>"
    if tl.startswith("apiversion:") and "\nkind:" in tl:
        return f"<yaml>\n{text}\n</yaml>"
    return text

def extract_failure_class(text: str) -> Optional[str]:
    for line in text.splitlines():
        if line.lower().startswith("failure class:"):
            return line.split(":", 1)[1].strip()
    return None

def parse_tool_request(text: str) -> Tuple[Optional[ToolRequest], Optional[str]]:
    text = text.strip()

    try:
        obj = json.loads(text)
        if obj.get("type") == "tool_request":
            return ToolRequest.model_validate(obj), text
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            raw = text[start:end + 1]
            obj = json.loads(raw)
            if obj.get("type") == "tool_request":
                return ToolRequest.model_validate(obj), raw
        except Exception:
            pass

    return None, None

def strip_json(text: str, raw_json: Optional[str]) -> str:
    if not raw_json:
        return text
    return text.replace(raw_json, "").strip()

def extract_scope_from_text(text: str, scope: dict):
    words = text.lower().split()
    if "namespace" in words:
        i = words.index("namespace")
        if i + 1 < len(words):
            scope["namespace"] = words[i + 1]

# =========================================================
# Main endpoint
# =========================================================

@app.post("/ask")
def ask(payload: dict):
    session_id = payload.get("session_id")
    question = payload.get("question")
    tool_choice = payload.get("tool_choice")
    debug = bool(payload.get("debug", False))

    if not session_id:
        return {"mode": "error", "text": "Missing session_id"}

    _TOOL_HISTORY.setdefault(session_id, set())
    scope = _SESSION_SCOPE.setdefault(session_id, {})

    # =====================================================
    # Phase 3 — tool execution
    # =====================================================
    if tool_choice:
        pending = _PENDING_TOOLS.pop(session_id, None)
        if not pending:
            return {"mode": "error", "text": "No pending tool request"}

        tool_req: ToolRequest = pending["tool_request"]
        internal_block = pending.get("internal_block", "")

        if tool_choice == "manual":
            text = (
                "Run the following commands and paste the output:\n\n"
                + "\n".join(tool_req.kubectl_commands)
            )
            add_message(session_id, "assistant", text)
            return {"mode": "answer", "text": text}

        results = []
        debug_exec = []

        for call in tool_req.tools:
            validate_kind(call.kind)

            sig = tool_signature(call)
            _TOOL_HISTORY[session_id].add(sig)

            output = read_object(
                kind=call.kind,
                namespace=call.namespace,
                name=call.name,
            )

            results.append({
                "kind": call.kind,
                "namespace": call.namespace,
                "name": call.name,
                "output": output,
            })

            if debug:
                debug_exec.append({
                    "executed": {
                        "kind": call.kind,
                        "namespace": call.namespace,
                        "name": call.name,
                    }
                })

        tool_block = render_tool_evidence(results)

        prompt = build_history_prompt(session_id)
        if internal_block:
            prompt += "\n" + internal_block + "\n"

        prompt += "\n<tool_evidence>\n" + tool_block + "\n</tool_evidence>\n"

        answer = ask_claude(SYSTEM_PROMPT, prompt)

        next_tool, raw_json = parse_tool_request(answer)
        if next_tool:
            filtered = []
            for t in next_tool.tools:
                sig = tool_signature(t)
                if sig in _TOOL_HISTORY[session_id]:
                    continue
                if requires_scope(t):
                    continue
                filtered.append(t)

            if filtered:
                next_tool.tools = filtered
                _PENDING_TOOLS[session_id] = {
                    "tool_request": next_tool,
                    "internal_block": internal_block,
                }
                resp = {
                    "mode": "permission",
                    "kubectl_commands": next_tool.kubectl_commands,
                }
                if debug:
                    resp["debug"] = {
                        "executed_tools": debug_exec,
                        "tool_history": sorted(_TOOL_HISTORY[session_id]),
                        "raw_tool_request": raw_json,
                    }
                return resp

        cleaned = strip_json(answer, raw_json)
        add_message(session_id, "assistant", cleaned)

        resp = {"mode": "answer", "text": cleaned}
        if debug:
            resp["debug"] = {
                "executed_tools": debug_exec,
                "tool_history": sorted(_TOOL_HISTORY[session_id]),
                "tool_evidence": results,
            }
        return resp

    # =====================================================
    # Phase 2 — normal question
    # =====================================================
    if not question:
        return {"mode": "error", "text": "Missing question"}

    extract_scope_from_text(question, scope)
    wrapped = wrap_input(question)
    add_message(session_id, "user", wrapped)

    base_prompt = build_history_prompt(session_id)

    if scope.get("namespace"):
        base_prompt += f"\n<known_scope>\nnamespace: {scope['namespace']}\n</known_scope>\n"

    draft = ask_claude(SYSTEM_PROMPT, base_prompt)
    failure_class = extract_failure_class(draft) or "Unknown"

    internal_block = ""
    if failure_class != "Unknown":
        docs = retrieve_top_k(_INTERNAL_INDEX, failure_class, k=3, min_score=0.5)
        internal_block = format_internal_refs(docs)

    prompt = base_prompt
    if internal_block:
        prompt += "\n" + internal_block + "\n"

    answer = ask_claude(SYSTEM_PROMPT, prompt)

    tool_req, raw_json = parse_tool_request(answer)
    if tool_req:
        blocked = [t.kind for t in tool_req.tools if requires_scope(t)]
        if blocked:
            text = (
                "I need more scope information before collecting data.\n\n"
                "Please tell me:\n"
                "- the namespace\n"
                "- and (if known) the pod or deployment name\n\n"
                f"Blocked request due to missing scope: {', '.join(set(blocked))}\n\n"
                f"Failure class: {failure_class}\n"
                "Evidence status: INSUFFICIENT"
            )
            add_message(session_id, "assistant", text)
            return {"mode": "answer", "text": text}

        _PENDING_TOOLS[session_id] = {
            "tool_request": tool_req,
            "internal_block": internal_block,
        }
        resp = {
            "mode": "permission",
            "kubectl_commands": tool_req.kubectl_commands,
        }
        if debug:
            resp["debug"] = {
                "raw_tool_request": raw_json,
            }
        return resp

    cleaned = strip_json(answer, raw_json)
    add_message(session_id, "assistant", cleaned)
    return {"mode": "answer", "text": cleaned}
