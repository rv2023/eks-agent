from fastapi import FastAPI
from eks_agent.bedrock import ask_claude
from eks_agent.memory import add_message, get_messages


app = FastAPI()
@app.post("/ask")
def ask(payload: dict):
    session_id = payload.get("session_id")
    question = payload.get("question")

    if not session_id or not question:
        return {"mode": "error", "text": "Missing session_id or question"}

    # store user message
    add_message(session_id, "user", question)

    history = get_messages(session_id)

    # build a combined prompt
    conversation = ""
    for msg in history:
        conversation += f"{msg['role']}: {msg['text']}\n"

    system_prompt = (
        "You are a Kubernetes and EKS troubleshooting assistant. "
        "Continue the conversation and ask for missing details if needed."
    )

    try:
        answer = ask_claude(system_prompt, conversation)
    except Exception as e:
        return {"mode": "error", "text": str(e)}

    # store assistant reply
    add_message(session_id, "assistant", answer)

    return {"mode": "answer", "text": answer}