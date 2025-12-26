from fastapi import FastAPI

from eks_agent.bedrock import ask_claude
from eks_agent.memory import add_message, get_messages
from eks_agent.prompts import SYSTEM_PROMPT

from eks_agent.rag.store import load_internal_docs
from eks_agent.rag.retrieve import build_index, retrieve_top_k
from eks_agent.rag.format import format_internal_refs

app = FastAPI()

_INTERNAL_DOCS = load_internal_docs("internal_docs")
_INTERNAL_INDEX = build_index(_INTERNAL_DOCS)
print(f"[debug] loaded {len(_INTERNAL_DOCS)} internal docs")

@app.post("/ask")
def ask(payload: dict):
    session_id = payload.get("session_id")
    question = payload.get("question")

    if not session_id or not question:
        return {"mode": "error", "text": "Missing session_id or question"}

    # ---------------------------
    # Input classification
    # ---------------------------
    input_type = detect_input_type(question)

    if input_type == "logs":
        wrapped = f"<logs>\n{question}\n</logs>"
    elif input_type == "yaml":
        wrapped = f"<yaml>\n{question}\n</yaml>"
    else:
        wrapped = question

    add_message(session_id, "user", wrapped)

    history = get_messages(session_id)

    base_prompt = ""
    for msg in history:
        base_prompt += f"{msg['role']}: {msg['text']}\n"

    # ---------------------------
    # LLM CALL 1 — failure class only
    # ---------------------------
    try:
        draft = ask_claude(SYSTEM_PROMPT, base_prompt)
    except Exception as e:
        return {"mode": "error", "text": str(e)}

    failure_class = extract_failure_class(draft) or "Unknown"

    if len(failure_class) > 64:
        failure_class = "Unknown"

    # ---------------------------
    # Phase-2 Internal RAG
    # ---------------------------
    internal_block = ""

    if failure_class != "Unknown":
        docs = retrieve_top_k(
            _INTERNAL_INDEX,
            query=failure_class,
            k=3,
            min_score=0.5,
        )
        print(f"[debug] retrieved {len(docs)} internal docs")
        internal_block = format_internal_refs(docs)

    # ---------------------------
    # LLM CALL 2 — final answer
    # ---------------------------
    final_prompt = base_prompt

    if internal_block:
        final_prompt += "\n" + internal_block + "\n"

    try:
        answer = ask_claude(SYSTEM_PROMPT, final_prompt)
    except Exception as e:
        return {"mode": "error", "text": str(e)}

    status = extract_evidence_status(answer)
    answer = strip_summary_if_needed(answer, status)

    add_message(session_id, "assistant", answer)

    return {"mode": "answer", "text": answer}


# =========================================================
# Helpers
# =========================================================

def extract_failure_class(text: str) -> str | None:
    found = None
    for line in text.splitlines():
        if line.lower().startswith("failure class:"):
            found = line.split(":", 1)[1].strip()
    return found


def extract_evidence_status(text: str) -> str:
    tl = text.lower()
    if "evidence status: sufficient" in tl:
        return "sufficient"
    if "evidence status: insufficient" in tl:
        return "insufficient"
    return "unknown"


def strip_summary_if_needed(text: str, status: str) -> str:
    if status != "insufficient":
        return text

    lowered = text.lower()
    idx = lowered.find("summary")
    if idx == -1:
        return text

    return text[:idx].rstrip()


def detect_input_type(text: str) -> str:
    tl = text.lower()

    if any(k in tl for k in [
        "exception", "traceback", "crashloopbackoff",
        "oomkilled", "back-off", "restarting",
        "error", "fail", "crash", "kill"
    ]):
        return "logs"

    if tl.startswith("apiversion:") and "\nkind:" in tl:
        return "yaml"

    return "text"