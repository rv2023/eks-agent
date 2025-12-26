Perfect 👍
Below is a **clean, complete, copy-paste ready `README.md`** that reflects the **actual architecture, design decisions, code flow, flags, safety rules, and contribution model** of your current system — **no assumptions, no aspirational features**.

This README is aligned with:

* Phase 2 (internal RAG)
* Phase 3 (permission-gated tools)
* Debug flag
* Scope enforcement
* Multi-round tool loop
* SDK-based execution

---

# `eks-agent`

`eks-agent` is a **safe, conversational Kubernetes / Amazon EKS troubleshooting assistant**.

It is designed to behave like a **senior on-call SRE**:

* never guessing
* never mutating cluster state
* progressively reducing uncertainty
* collecting **only read-only evidence**, with **explicit user permission**

The system is intentionally built in **phases**, prioritizing:

* correctness
* debuggability
* safety
* explainability

---

## What `eks-agent` does (today)

✅ Interactive CLI for Kubernetes troubleshooting
✅ Multi-turn conversation with memory
✅ Failure-class–first reasoning (not root-cause guessing)
✅ Internal experience (RAG) for background only
✅ Permission-gated, read-only Kubernetes data collection
✅ Python Kubernetes SDK execution (no shelling out)
✅ Multi-round tool loops (collect → reason → collect again)
✅ Debug mode to inspect backend execution safely

---

## What `eks-agent` explicitly does NOT do

❌ No write operations
❌ No kubectl execution in the backend
❌ No Secrets or ConfigMaps access
❌ No speculative root causes
❌ No automatic data collection without consent
❌ No hidden tool calls

---

## High-level architecture

```
┌────────────┐
│    CLI     │
│ eks_agent  │
└─────┬──────┘
      │ HTTP (JSON)
      ▼
┌────────────┐
│ FastAPI    │  server.py
│ Controller │
└─────┬──────┘
      │
      ├─▶ Conversation Memory
      │
      ├─▶ Internal RAG (Phase 2)
      │
      ├─▶ LLM (AWS Bedrock / Claude)
      │
      └─▶ Tool Executor (Phase 3)
             │
             ▼
        Kubernetes Python SDK
```

---

## Core design principles

### 1. Failure class first

The agent **always** identifies a failure class before proposing actions.

Examples:

* `CrashLoopBackOff`
* `ImagePullBackOff`
* `OOMKilled`
* `SchedulingFailure`

Failure class ≠ root cause.

---

### 2. Evidence-driven progression

The agent tracks:

* what it knows
* what is missing
* what evidence would materially reduce uncertainty

It will **not proceed** if evidence is insufficient.

---

### 3. User-controlled data collection (Phase 3)

When more data is needed:

* the agent explains *why*
* proposes *exactly what* to collect
* waits for user approval

No silent execution.

---

### 4. Strict safety boundaries

Enforced in code:

* Forbidden kinds: `Secret`, `ConfigMap`
* Read-only SDK calls only
* Scope enforcement (no cluster-wide listing without namespace)

---

## Codebase structure

```
eks-agent/
├── cli/
│   └── eks_agent.py        # Interactive CLI + permission loop
│
├── eks_agent/
│   ├── server.py           # Main FastAPI controller
│   ├── prompts.py          # System prompt (rules + contracts)
│   ├── memory.py           # Conversation memory
│   │
│   ├── rag/
│   │   ├── store.py        # Load internal docs
│   │   ├── retrieve.py     # Vector retrieval
│   │   └── format.py       # Prompt-safe formatting
│   │
│   └── tools/
│       ├── model.py        # ToolRequest / ToolCall schemas
│       ├── k8s_client.py   # Kubernetes client init
│       ├── k8s_reader.py   # Read-only Kubernetes access
│       ├── gate.py         # Kind validation / forbidden list
│       └── render.py       # Tool evidence rendering
```

---

## Request flow (step by step)

### Step 1 — User input

```bash
python cli/eks_agent.py ask "my pod is crashing"
```

CLI sends:

```json
{
  "session_id": "...",
  "question": "my pod is crashing"
}
```

---

### Step 2 — Initial reasoning (no tools)

The agent:

* wraps logs/YAML if needed
* reasons using history
* identifies a failure class
* decides if evidence is sufficient

---

### Step 3 — Tool proposal (if needed)

If evidence is insufficient, the LLM emits:

```json
{
  "type": "tool_request",
  "tools": [
    {
      "kind": "Pod",
      "namespace": "payments",
      "name": null,
      "why": "Identify crashing pod"
    }
  ]
}
```

The backend:

* validates safety
* enforces scope
* pauses execution
* asks the user for permission

---

### Step 4 — Permission loop

The CLI displays:

```
kubectl get pods -n payments
```

User chooses:

* auto (SDK)
* or manual

---

### Step 5 — Tool execution (SDK)

If approved:

* backend executes via Kubernetes Python SDK
* sanitizes output (metadata + status only)
* feeds evidence back to the LLM

---

### Step 6 — Repeat or conclude

The agent may:

* request another tool (multi-round)
* or conclude with `Evidence status: SUFFICIENT`

---

## Debug mode

Debug mode exposes **backend execution details**, safely.

### Enable debug

```bash
python cli/eks_agent.py ask "my pod is crashing" --debug
```

### What debug shows

* Executed tool calls
* Sanitized tool output
* Tool history (deduped)
* Raw tool evidence passed to the LLM

### What debug never shows

* Secrets
* Tokens
* Full object specs
* Prompt internals unless explicitly safe

Debug output is **only visible when enabled**.

---

## Safety rules (enforced in code)

* ❌ No Secrets / ConfigMaps
* ❌ No write APIs
* ❌ No speculative fixes
* ❌ No repeated tool calls
* ❌ No unscoped LIST requests
* ✅ Read-only SDK calls only
* ✅ Explicit permission gating

---

## Contribution guidelines

### How to contribute safely

1. **Do not weaken safety gates**
2. **Do not add write operations**
3. **Keep prompts deterministic**
4. **Prefer server-side enforcement over prompt rules**
5. **Add tests for new tool kinds**

---

### Good contribution examples

* New read-only Kubernetes kinds
* Better scope extraction
* Improved failure-class detection
* Stronger evidence sufficiency checks
* Better debug tooling

---

### Bad contribution examples

* Auto-running tools without permission
* Accessing Secrets or ConfigMaps
* Adding kubectl shell execution
* Letting the model bypass scope checks

---

## Current phase status

| Phase   | Description                  | Status |
| ------- | ---------------------------- | ------ |
| Phase 1 | Conversational CLI           | ✅      |
| Phase 2 | Internal RAG                 | ✅      |
| Phase 3 | Permission-gated tools       | ✅      |
| Phase 4 | External knowledge / metrics | ⏳      |
| Phase 5 | Remediation planning         | ⏳      |

---

## Philosophy

> **Never guess.
> Never mutate.
> Always explain.
> Evidence before answers.**



---
## Sample snippet

eks-agent$ python cli/eks_agent.py --debug
Session: 03a15ea2-55c3-4e3b-b4a0-7e3c2cb3058b
DEBUG MODE ENABLED

Type your message. Type 'exit' to quit.

you> my pod is crashing

agent> I need more scope information before collecting data.

Please tell me:
- the namespace
- and (if known) the pod or deployment name

Blocked request due to missing scope: Pod

Failure class: CrashLoopBackOff
Evidence status: INSUFFICIENT 

you> payments

Agent needs more evidence to continue.

It wants to run the following READ-ONLY commands:

  kubectl get pods -n payments

--- DEBUG (backend execution) ---
raw_tool_request:
{
  "type": "tool_request", 
  "tools": [
    {
      "kind": "Pod",
      "namespace": "payments",
      "name": null,
      "why": "List pods to identify the crashing instance"
    }
  ]
}
--- END DEBUG ---


Allow the agent to fetch this data itself?
[y] Yes (auto)
[n] No, I will run them manually
> y

Agent needs more evidence to continue.

It wants to run the following READ-ONLY commands:

  kubectl get pod payments-api-5bb796cd77-vrjw5 -n payments

--- DEBUG (backend execution) ---
executed_tools:
[{'executed': {'kind': 'Pod', 'namespace': 'payments', 'name': None}}]
tool_history:
['Pod:payments:None']
raw_tool_request:
{
  "type": "tool_request",
  "tools": [
    {
      "kind": "Pod",
      "namespace": "payments",
      "name": "payments-api-5bb796cd77-vrjw5",
      "why": "Inspect pod events and status for more details on image pull failure"
    }
  ]
}
--- END DEBUG ---


Allow the agent to fetch this data itself?
[y] Yes (auto)
[n] No, I will run them manually
> y

--- DEBUG (backend execution) ---
executed_tools:
[{'executed': {'kind': 'Pod', 'namespace': 'payments', 'name': 'payments-api-5bb796cd77-vrjw5'}}]
tool_history:
['Pod:payments:None', 'Pod:payments:payments-api-5bb796cd77-vrjw5']
tool_evidence:
[{'kind': 'Pod', 'namespace': 'payments', 'name': 'payments-api-5bb796cd77-vrjw5', 'output': {'kind': 'Pod', 'metadata': {'name': 'payments-api-5bb796cd77-vrjw5', 'namespace': 'payments', 'labels': {'app': 'payments-api', 'pod-template-hash': '5bb796cd77'}}, 'status': {'conditions': [{'last_probe_time': None, 'last_transition_time': '2025-12-26T09:45:24+00:00', 'message': None, 'observed_generation': None, 'reason': None, 'status': 'True', 'type': 'PodReadyToStartContainers'}, {'last_probe_time': None, 'last_transition_time': '2025-12-26T09:45:23+00:00', 'message': None, 'observed_generation': None, 'reason': None, 'status': 'True', 'type': 'Initialized'}, {'last_probe_time': None, 'last_transition_time': '2025-12-26T09:45:23+00:00', 'message': 'containers with unready status: [app]', 'observed_generation': None, 'reason': 'ContainersNotReady', 'status': 'False', 'type': 'Ready'}, {'last_probe_time': None, 'last_transition_time': '2025-12-26T09:45:23+00:00', 'message': 'containers with unready status: [app]', 'observed_generation': None, 'reason': 'ContainersNotReady', 'status': 'False', 'type': 'ContainersReady'}, {'last_probe_time': None, 'last_transition_time': '2025-12-26T09:45:22+00:00', 'message': None, 'observed_generation': None, 'reason': None, 'status': 'True', 'type': 'PodScheduled'}], 'container_statuses': [{'allocated_resources': None, 'allocated_resources_status': None, 'container_id': None, 'image': 'definitely-not-a-real-image:latest', 'image_id': '', 'last_state': {'running': None, 'terminated': None, 'waiting': None}, 'name': 'app', 'ready': False, 'resources': None, 'restart_count': 0, 'started': False, 'state': {'running': None, 'terminated': None, 'waiting': {'message': 'Back-off pulling image "definitely-not-a-real-image:latest"', 'reason': 'ImagePullBackOff'}}, 'stop_signal': None, 'user': None, 'volume_mounts': None}], 'ephemeral_container_statuses': None, 'extended_resource_claim_status': None, 'host_ip': '172.18.0.3', 'host_i_ps': [{'ip': '172.18.0.3'}], 'init_container_statuses': None, 'message': None, 'nominated_node_name': None, 'observed_generation': None, 'phase': 'Pending', 'pod_ip': '10.244.0.5', 'pod_i_ps': [{'ip': '10.244.0.5'}], 'qos_class': 'BestEffort', 'reason': None, 'resize': None, 'resource_claim_statuses': None, 'start_time': '2025-12-26T09:45:23+00:00'}}}]
--- END DEBUG ---


agent> Based on the provided evidence:

Findings:
- The pod "payments-api-5bb796cd77-vrjw5" in the "payments" namespace is in the "Pending" phase
- The container "app" is in "ImagePullBackOff" state with the reason "Back-off pulling image \"definitely-not-a-real-image:latest\""
- This indicates the Kubernetes cluster is unable to pull the specified container image

Internal experience (source: runbook_crashloop.md):
- Application exits immediately due to missing environment variables
- Invalid command or entrypoint  
- Config file not found at startup
- The internal experience suggests potential causes for CrashLoopBackOff, but does not apply to this ImagePullBackOff case

What to do next:
1. Verify the image name "definitely-not-a-real-image:latest" is correct
2. Check if the image exists in the configured container registry and is accessible
3. Update the deployment with the correct image reference if needed
4. After updating, the pod should automatically restart and pull the new image

Summary:
The pod is stuck in the Pending phase because Kubernetes cannot pull the specified container image. This is likely due to an invalid or inaccessible image name/tag. Fixing the image reference should allow the pod to start successfully.

Failure class: ImagePullBackOff  
Evidence status: SUFFICIENT