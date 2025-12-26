import sys
import uuid
import requests

SESSION_FILE = ".eks_agent_session"
SERVER_URL = "http://127.0.0.1:8080/ask"


def load_or_create_session():
    try:
        with open(SESSION_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        sid = str(uuid.uuid4())
        with open(SESSION_FILE, "w") as f:
            f.write(sid)
        return sid


def post(payload):
    r = requests.post(SERVER_URL, json=payload)
    r.raise_for_status()
    return r.json()


def handle_permission(session_id, res):
    """
    Handles ONE permission request.
    Returns the next server response.
    """
    print("\nAgent needs more evidence to continue.\n")
    print("It wants to run the following READ-ONLY commands:\n")

    for c in res.get("kubectl_commands", []):
        print(" ", c)

    choice = input(
        "\nAllow the agent to fetch this data itself?\n"
        "[y] Yes (auto)\n"
        "[n] No, I will run them manually\n> "
    )

    tool_choice = "self" if choice.lower().startswith("y") else "manual"

    return post({
        "session_id": session_id,
        "tool_choice": tool_choice,
    })


def main():
    session_id = load_or_create_session()
    print(f"Session: {session_id}")
    print("Type your message. Type 'exit' to quit.\n")

    while True:
        question = input("you> ").strip()
        if question in ("exit", "quit"):
            print("Goodbye.")
            break

        # Initial user question
        res = post({
            "session_id": session_id,
            "question": question,
        })

        # 🔁 LOOP until we get a final answer
        while True:
            mode = res.get("mode")

            if mode == "permission":
                res = handle_permission(session_id, res)
                continue

            if mode == "answer":
                print("\nagent>", res.get("text", ""), "\n")
                break

            # Safety net
            print("\nagent> Unexpected response:", res)
            break


if __name__ == "__main__":
    main()
