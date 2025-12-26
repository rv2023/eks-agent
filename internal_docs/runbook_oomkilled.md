# OOMKilled runbook

OOMKilled indicates the container exceeded its memory limit.

Patterns observed internally:
- Memory limits set too low for JVM-based apps
- Sudden traffic spikes causing memory pressure
- Missing memory requests causing bad scheduling

Typical checks:
- kubectl describe pod <pod>
- Check container memory limits and requests

This document is reference-only.
