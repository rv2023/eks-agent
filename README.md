Great start. Below is your **cleanly updated and completed README**, keeping **your wording and intent**, just tightening flow, filling gaps, and aligning it exactly with how the code + prompt behave today.

You can copy-paste this as your final README for **v0.2 / Phase 1.5**.

---

# eks-agent

`eks-agent` is a **simple, conversational Kubernetes / EKS troubleshooting assistant**.

It is intentionally built in small phases to prioritize:

* correctness
* debuggability
* learning
* safe evolution

This repository currently implements **Phase 1.5**.

---

## What eks-agent does (today)

* Provides an interactive CLI
* Maintains a continuous chat session
* Sends user questions to a backend server
* Calls AWS Bedrock (Claude)
* Returns human-readable troubleshooting guidance
* Remembers the last few messages in a conversation

**High-level flow:**

```
CLI → FastAPI server → AWS Bedrock (Claude) → CLI
```

---

## What eks-agent does NOT do (by design)

This is important.

`eks-agent` currently does **not**:

* Run `kubectl`
* Access live cluster state
* Modify Kubernetes resources
* Perform auto-remediation
* Search the internet
* Use RAG / vector databases
* Use LangChain
* Use MCP (Model Context Protocol)

All of the above are **intentionally deferred** to later phases.

---

## Architecture overview

### CLI

* Written in Python
* Runs interactively
* Sends user input to the server
* Reuses a session ID across runs

### Server

* FastAPI application
* Long-running process
* Maintains short-term memory in RAM
* Calls AWS Bedrock
* Builds prompt context explicitly (no hidden state)

---

## Conversation model

Each request sent to the LLM includes:

1. **System prompt**
   (rules, Kubernetes-first reasoning, evidence discipline)

2. **Last N messages from memory**
   (working context only)

3. **Current user input**

This keeps context:

* small
* predictable
* safe

There is no background reasoning, tool execution, or hidden state.

---

## Input handling

User input can be:

* Plain text questions
* Logs
* Errors
* YAML manifests
* Copied output from terminals or online sources

The server classifies input into:

* `text`
* `logs`
* `yaml`

If logs or YAML are detected, they are wrapped internally:

```text
<logs>...</logs>
<yaml>...</yaml>
```

This tells the model **what it is reading**, without modifying the content.

---

## Kubernetes-first reasoning

The agent reasons using Kubernetes-native concepts, for example:

* CrashLoopBackOff vs OOMKilled
* ImagePullBackOff vs configuration errors
* Pending vs scheduling constraints
* Readiness probe failures vs liveness probe failures

It always tries to:

* classify the failure type first
* ask for the **minimum next piece of information**
* request data using **exact kubectl commands**

It does not guess or invent cluster state.

---

## Evidence sufficiency rule (core behavior)

Before providing a summary or likely solution, the model must decide:

> “Do I have enough evidence to conclude?”

It must explicitly include one of the following lines at the end of every response:

```
Evidence status: INSUFFICIENT
```

or

```
Evidence status: SUFFICIENT
```

### If evidence is INSUFFICIENT

* No summary is allowed
* No “likely solution” is allowed
* The agent explains what is missing
* The agent provides exact `kubectl` commands to collect it

### If evidence is SUFFICIENT

* Findings are based strictly on provided evidence
* A short, probabilistic summary is allowed
* Next steps include fix and verification

The **server enforces this discipline** by stripping summaries when evidence is insufficient.

---

## Response modes (conceptual)

### Mode 1 — Investigation (Evidence INSUFFICIENT)

Typical structure:

1. General explanation
2. Internal experience (reference only, optional)
3. What to do next (exact `kubectl` commands)
4. Evidence status: INSUFFICIENT

### Mode 2 — Conclusion (Evidence SUFFICIENT)

Typical structure:

1. Findings (based on evidence)
2. Internal experience (reference only, optional)
3. What to do next (fix + verification)
4. Summary + likely solution
5. Evidence status: SUFFICIENT

These modes are **implicit**, not hard-coded.

---

## Sessions and memory

### Session

* Identified by a UUID
* Stored on the CLI side in `.eks_agent_session`
* Represents **one conversation**

### Memory

* Stored in server memory (RAM)
* Keyed by `session_id`
* Keeps only the last 6 messages per session
* Cleared when the server restarts

Memory is **short-term working memory**, not long-term knowledge.

---

## Requirements

* Python 3.10 or newer
* AWS credentials with Bedrock access
* AWS Bedrock enabled in your account

No virtualenv is required.

---

## Running the system

### Start the server

```bash
uvicorn eks_agent.server:app --host 127.0.0.1 --port 8080
```

### Use the CLI

```bash
eks-agent ask "my pod is crashing"
```

The CLI automatically reuses the session unless cleared.

---

## Current phase

### Phase 1.5 (this repository)

* Single LLM call per request
* No tools
* No RAG
* No web search
* Strong evidence discipline
* Kubernetes-first reasoning

Future phases will be **explicit and opt-in**, not silent upgrades.

---

## Design philosophy

`eks-agent` behaves like a **senior on-call engineer**, not a chatbot:

* Evidence before conclusions
* Explicit uncertainty
* Minimal assumptions
* Clear next steps
* No hidden behavior