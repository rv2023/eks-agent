import subprocess
import sys
import time
import requests
import os
import signal

BACKEND_URL = "http://127.0.0.1:8000"
HEALTH_URL = f"{BACKEND_URL}/health"

def backend_running() -> bool:
    try:
        r = requests.get(HEALTH_URL, timeout=0.5)
        return r.status_code == 200
    except Exception:
        return False


def start_backend():
    print("🚀 Starting EKS Agent backend...")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
    ]

    # Start detached
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,  # Linux/macOS
    )

    # Wait until health check passes
    for _ in range(20):
        if backend_running():
            print("✅ Backend ready")
            return
        time.sleep(0.5)

    print("❌ Backend failed to start")
    process.terminate()
    sys.exit(1)