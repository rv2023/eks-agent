# ImagePullBackOff runbook

ImagePullBackOff occurs when Kubernetes cannot pull the container image.

Internal cases included:
- Incorrect image tag
- Missing or misconfigured imagePullSecrets
- Private registry access issues

Typical checks:
- kubectl describe pod <pod>
- Verify image name and registry credentials

This document is reference-only.
