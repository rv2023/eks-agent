import shlex
import subprocess

ALLOWED_VERBS = {"get", "describe", "logs"}
DENY = {"apply","delete","edit","exec","patch","scale","rollout","port-forward","cp"}

def verify(cmd: str):
    toks = shlex.split(cmd)
    if toks[0] != "kubectl":
        return False, "not kubectl"

    for t in toks:
        if t in DENY:
            return False, f"forbidden verb {t}"

    if len(toks) < 2 or toks[1] not in ALLOWED_VERBS:
        return False, "only get/describe/logs allowed"

    return True, "ok"

def run(cmd: str):
    ok, reason = verify(cmd)
    if not ok:
        return {"ok": False, "error": reason}

    p = subprocess.run(
        shlex.split(cmd),
        capture_output=True,
        text=True,
        timeout=20
    )
    return {
        "ok": p.returncode == 0,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }