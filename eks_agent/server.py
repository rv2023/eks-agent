from fastapi import FastAPI
from eks_agent.bedrock import ask_claude
from eks_agent.memory import add_message, get_messages
from eks_agent.prompts import SYSTEM_PROMPT  # optional, if you split it


app = FastAPI()
@app.post("/ask")
def ask(payload: dict):
    session_id = payload.get("session_id")
    question = payload.get("question")

    if not session_id or not question:
        return {"mode": "error", "text": "Missing session_id or question"}

    # store user message
    input_type = detect_input_type(question)
    print(f"[debug] detected input type: {input_type}")
    if input_type == "logs":
        wrapped = f"<logs>\n{question}\n</logs>"
    elif input_type == "yaml":
        wrapped = f"<yaml>\n{question}\n</yaml>"
    elif input_type == "error":
        wrapped = f"<error>\n{question}\n</error>"
    else:
        wrapped = question

    add_message(session_id, "user", wrapped)

    history = get_messages(session_id)

    # build a combined prompt
    conversation = ""
    for msg in history:
        conversation += f"{msg['role']}: {msg['text']}\n"

    try:
        answer = ask_claude(SYSTEM_PROMPT, conversation)
    except Exception as e:
        return {"mode": "error", "text": str(e)}

    # store assistant reply
    add_message(session_id, "assistant", answer)

    return {"mode": "answer", "text": answer}

def detect_input_type(text: str) -> str:
    t = text.strip()
    t1 = t.lower()

    # 1. Error / log signals take priority
    if (
        "Exception" in t1
        or "Traceback" in t1
        or "CrashLoopBackOff" in t1
        or "OOMKilled" in t1
        or "Back-off" in t1
        or "restarting" in t1
        or "Error" in t
        or "Err" in t1
        or "Exit" in t1
        or "Fail" in t1
        or "Crash" in t1
        or "Kill" in t1
    ):
        return "logs"

    # 2. YAML only if it clearly looks like YAML
    if t1.startswith("apiVersion:") and "\nkind:" in t1:
        return "yaml"
    
    # 3. Fallback
    return "text"