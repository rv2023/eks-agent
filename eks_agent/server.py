from fastapi import FastAPI
from eks_agent.bedrock import ask_claude
from eks_agent.memory import add_message, get_messages
from eks_agent.prompts import SYSTEM_PROMPT

app = FastAPI()


@app.post("/ask")
def ask(payload: dict):
    session_id = payload.get("session_id")
    question = payload.get("question")

    if not session_id or not question:
        return {"mode": "error", "text": "Missing session_id or question"}

    # detect and wrap input
    input_type = detect_input_type(question)
    print(f"[debug] detected input type: {input_type}")

    if input_type == "logs":
        wrapped = f"<logs>\n{question}\n</logs>"
    elif input_type == "yaml":
        wrapped = f"<yaml>\n{question}\n</yaml>"
    else:
        wrapped = question

    # store user message
    add_message(session_id, "user", wrapped)

    history = get_messages(session_id)

    # build conversation text
    conversation = ""
    for msg in history:
        conversation += f"{msg['role']}: {msg['text']}\n"

    try:
        answer = ask_claude(SYSTEM_PROMPT, conversation)
    except Exception as e:
        return {"mode": "error", "text": str(e)}

    # enforce evidence discipline
    status = extract_evidence_status(answer)
    answer = strip_summary_if_needed(answer, status)

    # store assistant reply
    add_message(session_id, "assistant", answer)

    return {"mode": "answer", "text": answer}


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
    t = text.strip()
    tl = t.lower()

    # error / log signals (case-insensitive)
    if (
        "exception" in tl
        or "traceback" in tl
        or "crashloopbackoff" in tl
        or "oomkilled" in tl
        or "back-off" in tl
        or "restarting" in tl
        or "error" in tl
        or "err" in tl
        or "exit" in tl
        or "fail" in tl
        or "crash" in tl
        or "kill" in tl
    ):
        return "logs"

    # yaml only if clearly a manifest
    if tl.startswith("apiversion:") and "\nkind:" in tl:
        return "yaml"

    return "text"