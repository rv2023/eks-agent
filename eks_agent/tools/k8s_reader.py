from typing import Any
from eks_agent.tools.k8s_client import get_clients
from eks_agent.tools.gate import validate_kind


def _safe_meta(obj) -> dict:
    return {
        "name": obj.metadata.name if obj.metadata else None,
        "namespace": obj.metadata.namespace if obj.metadata else None,
        "labels": obj.metadata.labels if obj.metadata else None,
    }


def _safe_status(obj) -> Any:
    """
    Return JSON-safe status only.
    """
    status = getattr(obj, "status", None)
    if status is None:
        return None

    # Kubernetes SDK objects
    if hasattr(status, "to_dict"):
        return status.to_dict()

    # Already safe (CRDs, dicts)
    if isinstance(status, dict):
        return status

    # Fallback
    return str(status)


def _summarize(obj) -> dict:
    """
    Generic sanitizer for any Kubernetes object.

    STRICT RULE:
    - metadata (safe)
    - status only (NO spec, NO data)
    """
    return {
        "kind": obj.kind,
        "metadata": _safe_meta(obj),
        "status": _safe_status(obj),
    }


def read_object(
    kind: str,
    namespace: str | None = None,
    name: str | None = None,
):
    """
    Generic READ primitive.

    Rules:
    - name provided  -> GET
    - name is None   -> LIST
    - forbidden kinds are blocked
    - only metadata + status are returned
    """

    validate_kind(kind)
    clients = get_clients()
    k = kind.lower()

    core = clients["core"]
    apps = clients["apps"]
    autoscaling = clients["autoscaling"]
    custom = clients["custom"]

    # --------------------------------------------------
    # Core API
    # --------------------------------------------------
    if k == "pod":
        if name:
            obj = core.read_namespaced_pod(name, namespace)
            return _summarize(obj)
        objs = core.list_namespaced_pod(namespace)
        return [_summarize(o) for o in objs.items]

    if k == "service":
        if name:
            obj = core.read_namespaced_service(name, namespace)
            return _summarize(obj)
        objs = core.list_namespaced_service(namespace)
        return [_summarize(o) for o in objs.items]

    if k == "event":
        objs = core.list_namespaced_event(namespace)
        return [_summarize(o) for o in objs.items]

    if k == "node":
        objs = core.list_node()
        return [_summarize(o) for o in objs.items]

    # --------------------------------------------------
    # Apps API
    # --------------------------------------------------
    if k == "deployment":
        if name:
            obj = apps.read_namespaced_deployment(name, namespace)
            return _summarize(obj)
        objs = apps.list_namespaced_deployment(namespace)
        return [_summarize(o) for o in objs.items]

    if k == "replicaset":
        if name:
            obj = apps.read_namespaced_replica_set(name, namespace)
            return _summarize(obj)
        objs = apps.list_namespaced_replica_set(namespace)
        return [_summarize(o) for o in objs.items]

    if k == "statefulset":
        if name:
            obj = apps.read_namespaced_stateful_set(name, namespace)
            return _summarize(obj)
        objs = apps.list_namespaced_stateful_set(namespace)
        return [_summarize(o) for o in objs.items]

    if k == "daemonset":
        if name:
            obj = apps.read_namespaced_daemon_set(name, namespace)
            return _summarize(obj)
        objs = apps.list_namespaced_daemon_set(namespace)
        return [_summarize(o) for o in objs.items]

    # --------------------------------------------------
    # Autoscaling
    # --------------------------------------------------
    if k == "horizontalpodautoscaler":
        if name:
            obj = autoscaling.read_namespaced_horizontal_pod_autoscaler(
                name, namespace
            )
            return _summarize(obj)
        objs = autoscaling.list_namespaced_horizontal_pod_autoscaler(namespace)
        return [_summarize(o) for o in objs.items]

    # --------------------------------------------------
    # CRDs / Custom Resources
    # --------------------------------------------------
    if "." in k:
        plural, group = k.split(".", 1)

        if name:
            obj = custom.get_namespaced_custom_object(
                group=group,
                version="v1",
                namespace=namespace,
                plural=plural,
                name=name,
            )
            return {
                "kind": kind,
                "metadata": obj.get("metadata"),
                "status": obj.get("status"),
            }

        objs = custom.list_namespaced_custom_object(
            group=group,
            version="v1",
            namespace=namespace,
            plural=plural,
        )
        return [
            {
                "kind": kind,
                "metadata": o.get("metadata"),
                "status": o.get("status"),
            }
            for o in objs.get("items", [])
        ]

    raise ValueError(
        f"Unsupported kind '{kind}'. "
        "If this is a CRD, use '<plural>.<group>' format."
    )
