`eks-agent` is a **conversational Kubernetes / Amazon EKS troubleshooting assistant**.

It is intentionally built in **explicit, incremental phases** to prioritize:

- correctness
- debuggability
- safety
- learning
- controlled evolution

This repository currently implements **Phase 2 — Internal RAG (keyword-based, reference-only)**.

---

## What eks-agent does (today)

- Provides an interactive CLI
- Maintains a continuous chat session
- Sends user input to a backend server
- Calls AWS Bedrock (Claude)
- Returns human-readable Kubernetes troubleshooting guidance
- Remembers short-term conversation context
- Optionally references **internal documentation** as **non-authoritative background**

---

## What eks-agent does NOT do (by design)

This is intentional.

`eks-agent` does **not**:

- Run `kubectl`
- Access live cluster state
- Modify Kubernetes resources
- Perform auto-remediation
- Execute tools
- Search the internet
- Use embeddings or vector databases
- Use LangChain
- Use MCP (Model Context Protocol)

All of the above are deferred to **later, explicit phases**.

---

## High-level architecture

```

┌──────────┐
│   CLI    │
│ (Python) │
└────┬─────┘
│ HTTP
▼
┌────────────────────┐
│ FastAPI Server     │
│                    │
│ - session memory   │
│ - input parsing    │
│ - evidence guard   │
│ - internal RAG     │
└────┬───────────────┘
│
│ single LLM call
▼
┌────────────────────┐
│ AWS Bedrock        │
│ (Claude)           │
└────────────────────┘

```

Internal documentation is **never authoritative** and is not treated as evidence.

---

## Data flow (Phase 2)

### End-to-end request flow

```

User input
↓
CLI
↓
FastAPI /ask
↓
Input classification (text / logs / yaml)
↓
Conversation assembly (last N messages)
↓
Single LLM call (Claude)
↓
┌─────────────────────────────────────────┐
│ Model outputs:                          │
│ - reasoning                             │
│ - failure class (MANDATORY)             │
│ - evidence status (MANDATORY)           │
└─────────────────────────────────────────┘
↓
Failure class extraction (server-side)
↓
Internal doc retrieval (keyword-based)
↓
Internal refs appended (reference-only)
↓
Evidence enforcement (strip summary if needed)
↓
Response returned to CLI

````

---

## Conversation model

Each LLM call includes **only**:

1. **System prompt**
   - Kubernetes-first reasoning
   - Failure class requirement
   - Evidence discipline rules

2. **Short-term memory**
   - Last ~6 messages for the session

3. **Current user input**
   - Wrapped with `<logs>` or `<yaml>` if detected

There is **no hidden state**, background reasoning, or tool execution.

---

## Input handling

User input may be:

- Plain text questions
- Logs / errors
- YAML manifests
- Copied CLI output

The server classifies input as:

- `text`
- `logs`
- `yaml`

Logs and YAML are wrapped internally:

```text
<logs>...</logs>
<yaml>...</yaml>
````

This preserves raw evidence while signaling structure to the model.

---

## Kubernetes-first reasoning

The agent always reasons using Kubernetes-native signals first:

* CrashLoopBackOff vs OOMKilled
* ImagePullBackOff vs config errors
* Scheduling vs capacity issues
* Readiness vs liveness probe failures

The agent:

* Classifies the failure type first
* Avoids guessing
* Requests the **minimum next evidence**
* Always asks for data using **explicit kubectl commands**

---

## Failure class (Phase 2 core concept)

Before deciding whether evidence is sufficient, the model must emit a **failure class**.

Examples (non-exhaustive):

* CrashLoopBackOff
* OOMKilled
* ImagePullBackOff
* CreateContainerConfigError
* ProbeFailure
* SchedulingFailure
* Unknown

The response **must include exactly one line**:

```text
Failure class: <value>
```

The failure class:

* Is **not a root cause**
* Is **not a conclusion**
* Is used only to **drive internal reference lookup**

---

## Internal RAG (Phase 2)

Phase 2 introduces **Internal RAG** as **optional, additive context**.

### What Internal RAG is

* Keyword-based lookup over internal docs
* Deterministic and auditable
* Triggered only after failure class identification
* Reference-only (never authoritative)

### What Internal RAG is NOT

* Not embeddings
* Not semantic search
* Not a second LLM call
* Not evidence
* Not a source of truth

---

## Internal RAG safety rules (non-negotiable)

* User-provided logs, YAML, and statements always win
* Internal docs **must not** upgrade evidence sufficiency
* Internal docs **must not** override user evidence
* Internal docs **must not** introduce conclusions
* If internal docs conflict with user evidence → ignore internal docs
* All internal references must show **exact source names**

---

## Internal docs format (MVP)

Internal docs live locally:

```
internal_docs/
├── crashloop.md
├── oomkilled.md
├── imagepull.md
```

Each doc should:

* Be Markdown
* Contain short bullet points (`- ...`)
* Describe observed patterns, not prescriptions
* Avoid absolute language

Example:

```md
# CrashLoopBackOff

- Application exits immediately due to missing env vars
- Invalid entrypoint or command
- Config file missing at startup
```

---

## How internal references appear in responses

```text
Internal experience (reference only):
<internal_experience_refs>
- Source: crashloop.md
  - Application exits immediately due to missing env vars
  - Invalid entrypoint or command
</internal_experience_refs>
```

---

## Evidence sufficiency rule (core invariant)

Before summarizing or proposing a solution, the model must decide:

> “Do I have enough evidence to conclude?”

It must end every response with **exactly one**:

```text
Evidence status: INSUFFICIENT
```

or

```text
Evidence status: SUFFICIENT
```

### If evidence is INSUFFICIENT

* No summary
* No likely solution
* Explain what’s missing
* Provide exact kubectl commands

### If evidence is SUFFICIENT

* Findings tied directly to evidence
* Probabilistic summary allowed
* Fix + verification steps provided

The **server enforces this** by stripping summaries when needed.

---

## Sessions and memory

### Session

* Identified by UUID
* Stored on CLI side in `.eks_agent_session`
* Represents one continuous conversation

### Memory

* In-memory (RAM)
* Keyed by `session_id`
* Last ~6 messages only
* Cleared on server restart

This is **working memory**, not long-term knowledge.

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

## Current phase

### Phase 2 (this repository)

* One LLM call per request
* Failure-class-driven internal RAG
* Keyword retrieval only
* Reference-only internal docs
* No tools
* No embeddings
* No web search
* Strong evidence discipline

Future phases will be **explicit, gated, and opt-in**.

---

## Design philosophy

`eks-agent` behaves like a **senior on-call engineer**, not a chatbot:

* Evidence before conclusions
* Clear uncertainty
* Deterministic behavior
* No hidden actions
* Internal knowledge is context, not authority

```

---

If you want next, we can **lock Phase-2 fully** by adding:

- an *Internal Docs Authoring Guide*
- pytest tests that enforce:
  - source must be shown
  - RAG never upgrades evidence
- or a clean **Phase-3 (tool-based) README extension**