# eks_agent/tools/k8s_client.py

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


def get_clients():
    """
    Returns Kubernetes API clients.
    Tries in-cluster config first, then local kubeconfig.
    """
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()

    return {
        "core": client.CoreV1Api(),
        "apps": client.AppsV1Api(),
        "autoscaling": client.AutoscalingV1Api(),
        "custom": client.CustomObjectsApi(),
    }
