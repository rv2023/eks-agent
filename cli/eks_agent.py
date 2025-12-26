# cli/eks_agent.py
import sys
import uuid
import requests

SESSION_FILE = ".eks_agent_session"
SERVER_URL = "http://127.0.0.1:8080/ask"


def load_or_create_session() -> str:
    try:
        with open(SESSION_FILE, "r") as f:
            sid = f.read().strip()
            if sid:
                return sid
    except FileNotFoundError:
        pass

    sid = str(uuid.uuid4())
    with open(SESSION_FILE, "w") as f:
        f.write(sid)
    return sid


def post(payload: dict) -> dict:
    r = requests.post(SERVER_URL, json=payload)
    if not r.ok:
        raise RuntimeError(f"Server error: {r.status_code}\n{r.text}")
    return r.json()


def print_debug(res: dict):
    debug = res.get("debug")
    if not debug:
        return

    print("\n--- DEBUG (backend execution) ---")
    for k, v in debug.items():
        print(f"{k}:")
        print(v)
    print("--- END DEBUG ---\n")


def handle_permission(session_id: str, res: dict, debug: bool) -> dict:
    """
    Handle one or more permission rounds until resolved.
    """
    while res.get("mode") == "permission":
        print("\nAgent needs more evidence to continue.\n")
        print("It wants to run the following READ-ONLY commands:\n")

        for c in res.get("kubectl_commands", []):
            print(" ", c)

        if debug:
            print_debug(res)

        choice = input(
            "\nAllow the agent to fetch this data itself?\n"
            "[y] Yes (auto)\n"
            "[n] No, I will run them manually\n"
            "> "
        ).strip().lower()

        tool_choice = "self" if choice.startswith("y") else "manual"

        res = post({
            "session_id": session_id,
            "tool_choice": tool_choice,
            "debug": debug,
        })

    return res


def run_one_turn(session_id: str, question: str, debug: bool) -> None:
    res = post({
        "session_id": session_id,
        "question": question,
        "debug": debug,
    })

    res = handle_permission(session_id, res, debug)

    if debug:
        print_debug(res)

    text = res.get("text", "").strip()
    if text:
        print("\nagent>", text, "\n")
    else:
        print("\nagent> (no response)\n")


def main():
    debug = "--debug" in sys.argv
    args = [a for a in sys.argv if a != "--debug"]

    session_id = load_or_create_session()

    # One-shot mode
    if len(args) >= 3 and args[1] == "ask":
        question = " ".join(args[2:]).strip()
        print(f"Session: {session_id}")
        try:
            run_one_turn(session_id, question, debug)
        except Exception as e:
            print("\nagent> ERROR:", str(e), "\n")
        return

    # Interactive mode
    print(f"Session: {session_id}")
    if debug:
        print("DEBUG MODE ENABLED\n")

    print("Type your message. Type 'exit' to quit.\n")

    while True:
        try:
            question = input("you> ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break

        if question in ("exit", "quit"):
            print("Goodbye.")
            break

        if not question:
            continue

        try:
            run_one_turn(session_id, question, debug)
        except Exception as e:
            print("\nagent> ERROR:", str(e), "\n")


if __name__ == "__main__":
    main()