# eks_agent/tools/gate.py

FORBIDDEN_KINDS = {
    # Sensitive data
    "secret",
    "configmap",

    # Identity / RBAC
    "serviceaccount",
    "role",
    "rolebinding",
    "clusterrole",
    "clusterrolebinding",

    # Control-plane internals
    "lease",
    "endpointslice",
}

def validate_kind(kind: str):
    k = kind.lower()
    if k in FORBIDDEN_KINDS:
        raise ValueError(f"Access to Kubernetes kind '{kind}' is forbidden")