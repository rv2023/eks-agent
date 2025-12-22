#!/usr/bin/env python3
import argparse
import json
import os
import sys
import uuid
import time
import subprocess
import requests
import signal

# ======================================================
# Config
# ======================================================
API_URL = "http://127.0.0.1:8000"
HEALTH_URL = f"{API_URL}/health"
SESSION_FILE = os.path.expanduser("~/.eks_agent_session")

# ======================================================
# Backend lifecycle
# ======================================================
def backend_running() -> bool:
    try:
        r = requests.get(HEALTH_URL, timeout=0.5)
        return r.status_code == 200
    except Exception:
        return False


def start_backend():
    print("🚀 Starting EKS Agent backend...")

    # Resolve repo root robustly (works with symlinks)
    cli_path = os.path.realpath(__file__)
    cli_dir = os.path.dirname(cli_path)
    repo_root = os.path.abspath(os.path.join(cli_dir, ".."))

    venv_python = os.path.join(repo_root, ".venv", "bin", "python")

    if not os.path.exists(venv_python):
        print("❌ .venv not found. Backend requires project virtualenv.")
        print(f"Expected at: {venv_python}")
        sys.exit(1)

    # Verify uvicorn exists in venv
    try:
        subprocess.check_output([venv_python, "-m", "uvicorn", "--version"])
    except Exception:
        print("❌ uvicorn not installed in .venv")
        print("Run: pip install uvicorn")
        sys.exit(1)

    cmd = [
        venv_python,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--log-level", "warning",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=repo_root,               # 🔑 app/ becomes importable
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,        # detach process group
    )

    # Wait for backend readiness
    for _ in range(40):
        if backend_running():
            print("✅ Backend ready\n")
            return
        time.sleep(0.5)

    stderr = proc.stderr.read().decode()
    print("❌ Backend failed to start")
    print("---- uvicorn stderr ----")
    print(stderr or "(no output)")
    sys.exit(1)

# ======================================================
# Session handling
# ======================================================
def load_session_id():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            return f.read().strip()

    sid = str(uuid.uuid4())
    with open(SESSION_FILE, "w") as f:
        f.write(sid)
    return sid

# ======================================================
# API helpers
# ======================================================
def ask(session_id, question, namespace):
    resp = requests.post(
        f"{API_URL}/ask",
        json={
            "session_id": session_id,
            "question": question,
            "hints": {"namespace": namespace},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_evidence(session_id, kind, raw, namespace):
    resp = requests.post(
        f"{API_URL}/evidence",
        json={
            "session_id": session_id,
            "kind": kind,
            "raw": raw,
            "meta": {"namespace": namespace},
        },
        timeout=30,
    )
    resp.raise_for_status()

# ======================================================
# Rendering (human-friendly)
# ======================================================
def render(response):
    mode = response.get("mode")

    if mode == "need_evidence":
        phase = response.get("phase")
        print(f"\n🔍 Phase {phase}: More information needed\n")

        cmds = (
            response.get("commands", [])
            if phase == 2
            else response.get("verification_plan", [])
        )

        for i, c in enumerate(cmds, 1):
            cmd = c.get("command") or c.get("read_only_command")
            print(f"{i}. {cmd}")

        print("\n📋 Paste command output below (Ctrl+D to finish):\n")
        raw = sys.stdin.read()
        return ("evidence", raw, cmds)

    if mode == "answer":
        analysis = response.get("analysis", {})
        summary = analysis.get("summary", "")

        print("\n✅ Analysis complete\n")
        print(summary)

        hypotheses = analysis.get("hypotheses", [])
        if hypotheses:
            print("\nPossible causes:")
            for h in hypotheses:
                print(f"- {h.get('description')}")

        return ("done", None, None)

    print("\n⚠️ Unexpected response:\n")
    print(json.dumps(response, indent=2))
    return ("done", None, None)

# ======================================================
# Main CLI
# ======================================================
def main():
    if not backend_running():
        start_backend()

    parser = argparse.ArgumentParser(prog="eks-agent")
    parser.add_argument("ask", nargs="+", help="Question to ask the agent")
    parser.add_argument("--namespace", default="default")
    args = parser.parse_args()

    session_id = load_session_id()
    question = " ".join(args.ask)

    response = ask(session_id, question, args.namespace)

    while True:
        state, payload, cmds = render(response)

        if state == "done":
            break

        if state == "evidence":
            for c in cmds:
                kind = c.get("evidence_type") or c.get("kind")
                send_evidence(session_id, kind, payload, args.namespace)

            response = ask(session_id, question, args.namespace)

# ======================================================
# Entry
# ======================================================
if __name__ == "__main__":
    main()
