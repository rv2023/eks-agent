import sys
import uuid
import requests

if sys.version_info < (3, 10):
    raise RuntimeError("eks-agent requires Python 3.10+")

SESSION_FILE = ".eks_agent_session"


def load_or_create_session():
    try:
        with open(SESSION_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        sid = str(uuid.uuid4())
        with open(SESSION_FILE, "w") as f:
            f.write(sid)
        return sid


def main():
    session_id = load_or_create_session()
    print(f"Session: {session_id}")
    print("Type your message. Type 'exit' to quit.\n")

    while True:
        try:
            question = input("you> ").strip()
        except KeyboardInterrupt:
            print("\nExiting.")
            break

        if question.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        if not question:
            continue

        try:
            response = requests.post(
                "http://127.0.0.1:8080/ask",
                json={
                    "session_id": session_id,
                    "question": question,
                },
                timeout=30,
            )
        except requests.RequestException as e:
            print(f"Error: could not reach server: {e}")
            continue

        if response.status_code != 200:
            print(f"Server error: {response.status_code}")
            print(response.text)
            continue

        data = response.json()
        print(f"agent> {data.get('text', '')}\n")


if __name__ == "__main__":
    main()