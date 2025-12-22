# app/k8s_ro.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from kubernetes import client, config
from kubernetes.client import ApiException


@dataclass(frozen=True)
class K8sGrounding:
    namespace: str
    pods: Dict[str, Any]
    services: Dict[str, Any]
    endpoints: Dict[str, Any]
    events: Dict[str, Any]
    nodes: Dict[str, Any]
    crds: Dict[str, Any]


class K8sReadOnlyClient:
    """
    Read-only Kubernetes API client.
    Uses local kubeconfig (same context as kubectl).
    No write methods are exposed.
    """

    def __init__(self, kube_context: Optional[str] = None):
        # Use kubeconfig by default; in-cluster can be added later.
        config.load_kube_config(context=kube_context)
        self.core = client.CoreV1Api()
        self.apiext = client.ApiextensionsV1Api()

    def _safe_list(self, fn, *args, **kwargs) -> Dict[str, Any]:
        """Return a JSON-serializable dict (never raw client objects)."""
        try:
            obj = fn(*args, **kwargs)
            return client.ApiClient().sanitize_for_serialization(obj)
        except ApiException as e:
            return {
                "error": True,
                "status": e.status,
                "reason": e.reason,
                "body": getattr(e, "body", None),
            }

    def collect_grounding(self, namespace: str) -> K8sGrounding:
        # Core grounding set
        pods = self._safe_list(self.core.list_namespaced_pod, namespace=namespace)
        services = self._safe_list(self.core.list_namespaced_service, namespace=namespace)
        endpoints = self._safe_list(self.core.list_namespaced_endpoints, namespace=namespace)
        events = self._safe_list(self.core.list_namespaced_event, namespace=namespace)
        nodes = self._safe_list(self.core.list_node)

        # CRDs: presence + Established condition only (we store full list raw, later we’ll reduce)
        crds = self._safe_list(self.apiext.list_custom_resource_definition)

        return K8sGrounding(
            namespace=namespace,
            pods=pods,
            services=services,
            endpoints=endpoints,
            events=events,
            nodes=nodes,
            crds=crds,
        )