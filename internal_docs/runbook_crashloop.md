# CrashLoopBackOff runbook

CrashLoopBackOff happens when a container starts and exits repeatedly.

Common internal causes we have seen:
- Application exits immediately due to missing environment variables
- Invalid command or entrypoint
- Config file not found at startup

Typical checks:
- kubectl logs <pod> --previous
- kubectl describe pod <pod>

This document is reference-only.

CrashLoopBackOff
CrashLoopBackOff
CrashLoopBackOff