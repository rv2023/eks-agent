# app/phase2_grounding.py
from __future__ import annotations

import json
from typing import Dict, Any, Optional

from app.evidence.models import Evidence
from app.state import get_store
from app.k8s_ro import K8sReadOnlyClient


GROUNDING_KINDS = [
    "grounding.pods",
    "grounding.services",
    "grounding.endpoints",
    "grounding.events",
    "grounding.nodes",
    "grounding.crds",
]


def ingest_grounding(session_id: str, namespace: str, kube_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Pull generic grounding via Kubernetes APIs (read-only) and store as evidence.
    Returns ids for auditability.
    """
    store = get_store(session_id)
    k8s = K8sReadOnlyClient(kube_context=kube_context)
    g = k8s.collect_grounding(namespace=namespace)

    results = {}

    payloads = {
        "grounding.pods": g.pods,
        "grounding.services": g.services,
        "grounding.endpoints": g.endpoints,
        "grounding.events": g.events,
        "grounding.nodes": g.nodes,
        "grounding.crds": g.crds,
    }

    for kind, data in payloads.items():
        raw = json.dumps(data, indent=2, sort_keys=True)
        ev = Evidence.create(
            "kubectl",
            kind,
            raw,
            {
                "namespace": namespace,
                "kube_context": kube_context or "default",
                "phase": "phase2",
            },
        )
        store.add(ev)
        results[kind] = ev.id


    return {"ok": True, "namespace": namespace, "evidence_ids": results}