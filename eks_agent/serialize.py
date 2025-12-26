# eks_agent/tools/serialize.py

from kubernetes.client import ApiClient

_api_client = ApiClient()

def k8s_to_dict(obj):
    """
    Convert Kubernetes Python SDK objects into JSON-safe dicts.
    """
    if obj is None:
        return None

    # Kubernetes model objects
    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    # Lists of model objects
    if isinstance(obj, list):
        return [k8s_to_dict(i) for i in obj]

    # Already JSON-safe
    if isinstance(obj, (dict, str, int, float, bool)):
        return obj

    # Fallback: string representation
    return str(obj)
