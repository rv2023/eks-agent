# app/phase4.py
from __future__ import annotations

import hashlib
import json
import re
from typing import Dict, List, Optional, Tuple

import app.config as config
from app.audit import audit_write
from app.evidence.store import EvidenceStore

from app.phase4_models import Phase4Check, Phase4Response, VerificationPlanItem


# ======================================================
# Strict safety validation
# ======================================================

SAFE_VALUE_RE = re.compile(r"^[a-zA-Z0-9\-._/=,:]+$")
K8S_NS_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
K8S_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

# Block obvious shell control operators
DISALLOWED_SHELL_CHARS = [";", "&&", "||", "|", ">", "<", "$(", "`"]


def _canonical_targets(targets: Dict[str, str]) -> str:
    return json.dumps(targets, sort_keys=True, separators=(",", ":"))


def _evidence_key(kind: str, cmd: str, targets: Dict[str, str]) -> str:
    raw = f"{kind}|{cmd}|{_canonical_targets(targets)}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_targets(targets: Dict[str, str]) -> None:
    for k, v in targets.items():
        if not v or not SAFE_VALUE_RE.match(v):
            raise ValueError(f"Invalid target value: {k}={v}")

    if "namespace" in targets and not K8S_NS_RE.match(targets["namespace"]):
        raise ValueError(f"Invalid namespace: {targets['namespace']}")

    # Common k8s resource names
    for f in ("pod", "service", "node"):
        if f in targets and not K8S_NAME_RE.match(targets[f]):
            raise ValueError(f"Invalid {f} name: {targets[f]}")


def _validate_command_read_only(cmd: str) -> None:
    for bad in DISALLOWED_SHELL_CHARS:
        if bad in cmd:
            raise ValueError(f"Disallowed shell operator in command: {bad}")

    # Minimal backstop: must start with kubectl and only read-only verbs
    if not cmd.strip().startswith("kubectl "):
        raise ValueError("Only kubectl commands are allowed in Phase 4 (read-only).")

    allowed_verbs = ("get ", "describe ", "logs ")
    rest = cmd.strip()[len("kubectl "):]
    if not rest.startswith(allowed_verbs):
        raise ValueError("kubectl verb not allowed for Phase 4 (must be get/describe/logs).")


# ======================================================
# Deterministic mapping registry (MUST align with phase2.py)
# ======================================================
# IMPORTANT:
# - Phase 4 never accepts commands from the LLM.
# - It accepts (kind, targets) and renders a command here.
# - evidence_type MUST match Phase 2 summary keys exactly.
#
# Canonical Phase 2 workload summaries:
# - workload.pod_describe
# - workload.container_logs
#
# Grounding summaries are Phase 2 responsibility ONLY and should not be planned here.


def _render(kind: str, targets: Dict[str, str]) -> Tuple[str, str]:
    """
    Returns: (evidence_type, read_only_command)
    evidence_type must match EvidenceStore.summary keys used by Phase 2.
    """
    ns = targets.get("namespace", "default")

    # -----------------------
    # WORKLOAD (aligned with phase2.py)
    # -----------------------
    if kind == "workload.pod_describe":
        pod = targets["pod"]
        return ("workload.pod_describe", f"kubectl describe pod {pod} -n {ns}")

    if kind in {"workload.container_logs", "workload.container_logs_previous"}:
        pod = targets["pod"]

        if kind == "workload.container_logs_previous":
            container = targets.get("container")
            if not container:
                raise ValueError("workload.container_logs_previous requires targets.container")

            # Canonical evidence_type remains workload.container_logs (matches Phase 2 ladder)
            return (
                "workload.container_logs",
                f"kubectl logs {pod} -n {ns} -c {container} --previous --tail=200",
            )

        # Canonical evidence_type remains workload.container_logs (matches Phase 2 ladder)
        return ("workload.container_logs", f"kubectl logs {pod} -n {ns} --tail=200")

    # -----------------------
    # NETWORK (optional, future-safe)
    # If you later add a Phase 2 NETWORK ladder, make sure these
    # summaries are also canonical there.
    # -----------------------
    if kind == "network.service_yaml":
        svc = targets["service"]
        return ("network.service", f"kubectl get svc {svc} -n {ns} -o yaml")

    if kind == "network.endpoints_yaml":
        svc = targets["service"]
        return ("network.endpoints", f"kubectl get endpoints {svc} -n {ns} -o yaml")

    # -----------------------
    # HARD FAIL (deterministic)
    # -----------------------
    raise ValueError(f"Unknown or unsupported check kind: {kind}")


def _evidence_already_present(
    store: EvidenceStore, evidence_type: str, namespace: Optional[str]
) -> bool:
    """
    Conservative: if any evidence with this summary exists for this namespace,
    treat as present.
    """
    for ev in store.items:
        if ev.summary == evidence_type:
            if namespace is None or ev.meta.get("namespace") == namespace:
                return True
    return False


def run_phase4(*, session_id: str, plane: str, phase3_output: Dict) -> Phase4Response:
    """
    Phase 4 — Verification & Closure
    Pure code. Deterministic. No LLM. No execution.
    """
    evidence = EvidenceStore.load(session_id)

    audit_write(
        config.settings.audit_dir,
        {
            "type": "phase4_start",
            "session_id": session_id,
            "plane": plane,
            "optional_next_checks_count": len(phase3_output.get("optional_next_checks", [])),
            "evidence_count": len(evidence.items),
        },
    )

    # Phase 4 requires structured checks; refuse free-text.
    raw_checks = phase3_output.get("optional_next_checks", [])
    structured: List[Phase4Check] = []

    for idx, item in enumerate(raw_checks):
        if isinstance(item, str):
            audit_write(
                config.settings.audit_dir,
                {
                    "type": "phase4_refused",
                    "session_id": session_id,
                    "reason": "optional_next_checks_contains_string",
                    "index": idx,
                    "value": item[:200],
                },
            )
            raise ValueError(
                "Phase 4 refused: optional_next_checks must be structured objects, not strings."
            )

        structured.append(Phase4Check.model_validate(item))

    plan: List[VerificationPlanItem] = []
    seen_keys = set()

    for chk in structured:
        _validate_targets(chk.targets)

        evidence_type, cmd = _render(chk.kind, chk.targets)
        _validate_command_read_only(cmd)

        ns = chk.targets.get("namespace")

        # Skip if already have evidence type (namespace-scoped)
        if _evidence_already_present(evidence, evidence_type, ns):
            audit_write(
                config.settings.audit_dir,
                {
                    "type": "phase4_skip",
                    "session_id": session_id,
                    "check_id": chk.id,
                    "reason": "evidence_already_present",
                    "evidence_type": evidence_type,
                    "namespace": ns,
                },
            )
            continue

        ek = _evidence_key(chk.kind, cmd, chk.targets)

        if ek in seen_keys:
            audit_write(
                config.settings.audit_dir,
                {
                    "type": "phase4_dedupe",
                    "session_id": session_id,
                    "check_id": chk.id,
                    "evidence_key": ek,
                },
            )
            continue

        seen_keys.add(ek)

        plan.append(
            VerificationPlanItem(
                check_id=f"V_{chk.id}",
                description=chk.description,
                evidence_type=evidence_type,
                read_only_command=cmd,
                rationale={
                    "hypothesis_id": chk.rationale_hypothesis_id,
                    "source_check_id": chk.id,
                },
                evidence_key=ek,
            )
        )

        audit_write(
            config.settings.audit_dir,
            {
                "type": "phase4_planned",
                "session_id": session_id,
                "check_id": chk.id,
                "kind": chk.kind,
                "evidence_type": evidence_type,
                "command": cmd,
                "evidence_key": ek,
            },
        )

    mode = "verification_complete" if not plan else "need_evidence"
    resp = Phase4Response(mode=mode, verification_plan=plan)

    audit_write(
        config.settings.audit_dir,
        {
            "type": "phase4_complete",
            "session_id": session_id,
            "mode": mode,
            "planned": [p.check_id for p in plan],
        },
    )

    return resp