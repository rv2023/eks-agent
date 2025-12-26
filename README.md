Below is a **clean, corrected, and code-accurate `README.md`** for your repo **as it exists today**.

This version:

* Fixes the **LLM call count mismatch**
* Matches **actual server behavior**
* Clearly locks **Phase-2 invariants**
* Does **not** introduce Phase 3 concepts
* Uses **plain language**, no buzzwords
* Makes safety and limits explicit

You can copy-paste this as your new `README.md`.

---

# eks-agent

`eks-agent` is a **conversational Kubernetes / Amazon EKS troubleshooting assistant**.

It is built in **explicit, locked phases** to prioritize:

* correctness
* safety
* debuggability
* deterministic behavior
* controlled evolution

This repository currently implements **Phase 2 — Internal RAG (keyword-based, reference-only)**.

---

## What eks-agent does (today)

* Provides an interactive CLI
* Maintains a short-lived chat session
* Sends user input to a FastAPI backend
* Calls AWS Bedrock (Claude)
* Analyzes Kubernetes issues using Kubernetes-native signals
* Classifies failures before reasoning
* Optionally references internal documentation as **non-authoritative background**
* Enforces strict evidence discipline server-side

---

## What eks-agent does NOT do (by design)

This is intentional.

`eks-agent` does **not**:

* Run `kubectl`
* Access live cluster state
* Modify Kubernetes resources
* Execute tools
* Perform auto-remediation
* Use embeddings or vector databases
* Search the internet
* Use LangChain or MCP
* Assume cluster access or permissions

All of the above are deferred to **future, explicit phases**.

---

## Current phase

### Phase 2 — Internal RAG (LOCKED)

Phase 2 adds **failure-class-driven internal references** while enforcing **evidence-first reasoning**.

**Phase 2 invariants are non-negotiable.**

---

## High-level architecture (Phase 2)

```
┌──────────┐
│   CLI    │
│ (Python) │
└────┬─────┘
     │ HTTP
     ▼
┌────────────────────────┐
│ FastAPI Server         │
│                        │
│ - session memory       │
│ - input classification │
│ - failure class guard  │
│ - evidence enforcement │
│ - internal RAG lookup  │
└────┬───────────────────┘
     │
     │ LLM Call #1 (failure class)
     ▼
┌────────────────────────┐
│ AWS Bedrock (Claude)   │
└────┬───────────────────┘
     │
     │ keyword RAG lookup
     ▼
┌────────────────────────┐
│ Internal Docs (local)  │
└────┬───────────────────┘
     │
     │ LLM Call #2 (final answer)
     ▼
┌────────────────────────┐
│ AWS Bedrock (Claude)   │
└────────────────────────┘
```

---

## Data flow (Phase 2)

### End-to-end request flow

```
User input
↓
CLI
↓
POST /ask
↓
Input classification (text / logs / yaml)
↓
Wrap logs or yaml (<logs>, <yaml>)
↓
Store short-term session memory (last ~6 messages)
↓
LLM Call #1
  → identify Failure class
↓
Extract "Failure class: X"
↓
Keyword lookup over internal_docs/
↓
Format <internal_experience_refs> (reference-only)
↓
LLM Call #2
  → final answer with refs injected
↓
Extract Evidence status
↓
If INSUFFICIENT → strip summary server-side
↓
Return response to CLI
```

---

## Conversation model

Each request includes **only**:

1. **System prompt**

   * Kubernetes-first reasoning
   * Failure class requirement
   * Evidence sufficiency rules

2. **Short-term memory**

   * Last ~6 messages for the session
   * In-memory only
   * Cleared on server restart

3. **Current user input**

   * Logs wrapped in `<logs>`
   * YAML wrapped in `<yaml>`

There is **no hidden state** and **no background execution**.

---

## Input handling

User input may be:

* Plain text questions
* Logs or stack traces
* YAML manifests
* Copied CLI output

The server classifies input as:

* `text`
* `logs`
* `yaml`

Wrapping preserves raw evidence while signaling structure to the model.

---

## Kubernetes-first reasoning

The agent always reasons using Kubernetes signals first:

* CrashLoopBackOff vs OOMKilled
* ImagePullBackOff vs config errors
* Scheduling vs capacity issues
* Readiness vs liveness probe failures

The agent:

* Classifies the failure signal first
* Avoids guessing
* Requests the **minimum next evidence**
* Always provides **exact kubectl commands** when asking for data

---

## Failure class (Phase 2 core concept)

Before deciding whether evidence is sufficient, the model **must emit a failure class**.

Examples (not exhaustive):

* CrashLoopBackOff
* OOMKilled
* ImagePullBackOff
* CreateContainerConfigError
* ProbeFailure
* SchedulingFailure
* Unknown

Exactly one explicit line is required:

```
Failure class: <value>
```

The failure class:

* Is **not** a root cause
* Is **not** a conclusion
* Is used **only** to drive internal reference lookup

---

## Internal RAG (Phase 2)

Phase 2 introduces **Internal RAG** as optional background context.

### What Internal RAG is

* Keyword-based lookup over local markdown files
* Deterministic and auditable
* Triggered **only after failure class identification**
* Injected before the second LLM call
* Reference-only

### What Internal RAG is NOT

* Not embeddings
* Not semantic search
* Not a source of truth
* Not evidence
* Not allowed to upgrade certainty

---

## Internal RAG safety rules (LOCKED)

* User-provided logs and YAML always win
* Internal docs never override user evidence
* Internal docs never upgrade evidence sufficiency
* Internal docs never introduce conclusions
* Conflicts → internal docs are ignored
* All references must show exact source filenames

---

## Internal docs format

Internal docs live locally:

```
internal_docs/
├── runbook_crashloop.md
├── runbook_oomkilled.md
├── runbook_imagepull.md
```

Each doc:

* Markdown only
* Short bullet points
* Observed patterns, not prescriptions
* No absolute language

---

## How internal references appear in responses

```
Internal experience (reference only):
<internal_experience_refs>
- Source: runbook_crashloop.md
  - Application exits immediately due to missing env vars
  - Invalid entrypoint or command
</internal_experience_refs>
```

---

## Evidence sufficiency rule (CORE INVARIANT)

Every response **must** end with exactly one:

```
Evidence status: SUFFICIENT
```

or

```
Evidence status: INSUFFICIENT
```

### If evidence is INSUFFICIENT

* No summary
* No likely solution
* Explain what is missing
* Provide exact kubectl commands

### If evidence is SUFFICIENT

* Findings tied directly to evidence
* Probabilistic summary allowed
* Fix and verification steps allowed

**The server enforces this** by stripping summaries when needed.

---

## Sessions and memory

### Session

* Identified by UUID
* Stored on CLI side in `.eks_agent_session`
* Represents one continuous conversation

### Memory

* In-memory only
* Last ~6 messages
* Cleared on server restart

This is **working memory**, not knowledge storage.

---

## Running the system

### Start the server

```bash
uvicorn eks_agent.server:app --host 127.0.0.1 --port 8080
```

### Start the CLI

```bash
python cli/eks_agent.py
```

---

## Design philosophy

`eks-agent` behaves like a **senior on-call engineer**, not a chatbot:

* Evidence before conclusions
* Clear uncertainty
* Deterministic behavior
* No hidden actions
* Internal knowledge is context, not authority

---

## Future phases (preview only)

* **Phase 3** — Explicit, read-only tools (opt-in, gated)
* **Phase 4** — Embeddings + vector search (non-authoritative)
* **Phase 5** — Optional web search (explicit, high-risk, guarded)

Each phase will be additive and will **not weaken Phase 2 guarantees**.