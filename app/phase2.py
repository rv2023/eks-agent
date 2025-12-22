# app/phase2.py
from typing import List, Optional, Literal

from app.agent_planner import ToolPlan, ToolCommand

# ======================================================
# Phase 2 Contract
# ======================================================

REQUIRED_GROUNDING = [
    "grounding.pods",
    "grounding.services",
    "grounding.endpoints",
    "grounding.events",
    "grounding.nodes",
    "grounding.crds",
]

Plane = Literal[
    "WORKLOAD",
    "NETWORK",
    "CONTROL_PLANE",
    "NODE",
    "EXTERNAL",
]

# ======================================================
# Helpers
# ======================================================

def _iter_evidence(store):
    """Iterate immutable Tier-2 evidence."""
    return store.items


def _get_ev(store, summary: str, namespace: str | None = None):
    """Return first matching evidence entry (deterministic)."""
    for ev in _iter_evidence(store):
        if ev.summary == summary:
            if namespace is None or ev.meta.get("namespace") == namespace:
                return ev
    return None

# ======================================================
# Generic grounding
# ======================================================

def generic_grounding_missing(store, namespace: str) -> list[str]:
    """
    Determine which generic grounding summaries are missing.
    """
    present = set()

    for ev in _iter_evidence(store):
        summary = ev.summary

        if summary in {
            "grounding.pods",
            "grounding.services",
            "grounding.endpoints",
            "grounding.events",
        }:
            if ev.meta.get("namespace") == namespace:
                present.add(summary)

        elif summary in {
            "grounding.nodes",
            "grounding.crds",
        }:
            present.add(summary)

    return [s for s in REQUIRED_GROUNDING if s not in present]


def grounding_commands(namespace: str) -> List[ToolCommand]:
    """
    Deterministic mapping from grounding evidence to read-only commands.
    """
    return [
        ToolCommand(
            title="Pods",
            command=f"kubectl get pods -n {namespace} -o wide",
            why="establish workload health and placement",
            signals=["CrashLoopBackOff", "Pending", "Restarts"],
        ),
        ToolCommand(
            title="Services",
            command=f"kubectl get svc -n {namespace}",
            why="establish service intent",
            signals=["ClusterIP", "LoadBalancer"],
        ),
        ToolCommand(
            title="Endpoints",
            command=f"kubectl get endpoints -n {namespace}",
            why="verify service backends",
            signals=["<none>"],
        ),
        ToolCommand(
            title="Events",
            command=f"kubectl get events -n {namespace} --sort-by=.lastTimestamp",
            why="detect scheduling, image, probe failures",
            signals=["Failed", "BackOff", "Unhealthy"],
        ),
        ToolCommand(
            title="Nodes",
            command="kubectl get nodes",
            why="check node readiness and pressure",
            signals=["NotReady"],
        ),
        ToolCommand(
            title="CRDs",
            command="kubectl get crd",
            why="discover installed extensions",
            signals=["Established"],
        ),
    ]

# ======================================================
# Phase 2 Orchestrator
# ======================================================

def phase2_plan(store, namespace: str = "default") -> Optional[ToolPlan]:
    """
    Phase 2 planner.
    - READ-ONLY
    - Deterministic
    - Idempotent
    """

    # 1. Enforce generic grounding
    missing_grounding = generic_grounding_missing(store, namespace)
    if missing_grounding:
        return ToolPlan(
            missing=missing_grounding,
            commands=grounding_commands(namespace),
        )

    # 2. Detect plane (grounding-only)
    plane = detect_plane(store, namespace)

    # 3. WORKLOAD ladder
    if plane == "WORKLOAD":
        pods_ev = _get_ev(store, "grounding.pods", namespace)
        failing_pods = _failing_pods(pods_ev)

        if failing_pods:
            missing = workload_missing(store, namespace)
            if missing:
                return ToolPlan(
                    missing=missing,
                    commands=workload_commands(namespace, failing_pods),
                )

    # 4. Phase 2 complete
    return None

# ======================================================
# Plane detection
# ======================================================

def detect_plane(store, namespace: str) -> Plane:
    """
    Determine the unhealthy plane using grounding evidence only.
    """

    pods = _get_ev(store, "grounding.pods", namespace)
    services = _get_ev(store, "grounding.services", namespace)
    endpoints = _get_ev(store, "grounding.endpoints", namespace)
    events = _get_ev(store, "grounding.events", namespace)
    nodes = _get_ev(store, "grounding.nodes")
    crds = _get_ev(store, "grounding.crds")

    # ---- Rule 1: NODE ----
    if _nodes_unhealthy(nodes) or _events_contain(events, ["FailedScheduling"]):
        return "NODE"

    # ---- Rule 2: CONTROL PLANE ----
    if _crds_not_established(crds) or _events_contain(events, ["FailedCreate", "Webhook"]):
        return "CONTROL_PLANE"

    # ---- Rule 3: NETWORK ----
    if _services_present(services) and _endpoints_empty(endpoints):
        return "NETWORK"

    # ---- Rule 4: WORKLOAD ----
    if _pods_unhealthy(pods) or _events_contain(events, ["BackOff", "Unhealthy", "FailedMount"]):
        return "WORKLOAD"

    # ---- Rule 5: EXTERNAL ----
    return "EXTERNAL"

# ======================================================
# Grounding analysis helpers
# ======================================================

def _nodes_unhealthy(nodes_ev) -> bool:
    if not nodes_ev:
        return False
    return any("NotReady" in line for line in nodes_ev.raw.splitlines())


def _crds_not_established(crds_ev) -> bool:
    if not crds_ev:
        return False
    return "Established" in crds_ev.raw and "False" in crds_ev.raw


def _services_present(svc_ev) -> bool:
    if not svc_ev:
        return False
    return "items" in svc_ev.raw


def _endpoints_empty(ep_ev) -> bool:
    if not ep_ev:
        return False
    return "<none>" in ep_ev.raw or "subsets" in ep_ev.raw and "[]" in ep_ev.raw


def _pods_unhealthy(pods_ev) -> bool:
    if not pods_ev:
        return False
    return any(
        s in pods_ev.raw
        for s in ["CrashLoopBackOff", "ImagePullBackOff", "Pending"]
    )


def _events_contain(events_ev, reasons: list[str]) -> bool:
    if not events_ev:
        return False
    return any(r in events_ev.raw for r in reasons)

# ======================================================
# Workload ladder
# ======================================================

def _failing_pods(pods_ev) -> list[str]:
    """
    Extract unhealthy pod names (conservative string parsing).
    """
    if not pods_ev:
        return []

    failing = set()
    for line in pods_ev.raw.splitlines():
        if any(s in line for s in ["CrashLoopBackOff", "ImagePullBackOff", "Pending"]):
            parts = line.split()
            if parts:
                failing.add(parts[0])
    return list(failing)


def workload_missing(store, namespace: str) -> list[str]:
    """
    Determine missing workload-level evidence.
    """
    present = set()

    for ev in _iter_evidence(store):
        if ev.summary in {
            "workload.pod_describe",
            "workload.container_logs",
        } and ev.meta.get("namespace") == namespace:
            present.add(ev.summary)

    missing = []
    if "workload.pod_describe" not in present:
        missing.append("workload.pod_describe")
    if "workload.container_logs" not in present:
        missing.append("workload.container_logs")

    return missing


def workload_commands(namespace: str, pods: list[str]) -> list[ToolCommand]:
    """
    Generate exact read-only commands for workload ladder.
    One describe + one logs per failing pod.
    """
    commands: list[ToolCommand] = []

    for pod in sorted(pods):
        commands.append(
            ToolCommand(
                title=f"Describe pod {pod}",
                command=f"kubectl describe pod {pod} -n {namespace}",
                why="inspect container state, probes, mounts, scheduling",
                signals=["Events", "State", "Reason"],
            )
        )

        commands.append(
            ToolCommand(
                title=f"Logs for pod {pod}",
                command=f"kubectl logs {pod} -n {namespace} --tail=100",
                why="inspect runtime failure messages",
                signals=["Exception", "Error", "Traceback"],
            )
        )

    return commands