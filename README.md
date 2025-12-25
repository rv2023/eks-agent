# eks-agent

eks-agent is a **simple, conversational Kubernetes / EKS troubleshooting assistant**.

It is intentionally built in small phases to prioritize:
- correctness
- debuggability
- learning
- safe evolution

This repository currently implements **Phase 1.5**.

---

## What eks-agent does (today)

- Provides an interactive CLI
- Maintains a continuous chat session
- Sends user questions to a backend server
- Calls AWS Bedrock (Claude)
- Returns human-readable troubleshooting guidance
- Remembers the last few messages in a conversation

High-level flow:

CLI → FastAPI server → AWS Bedrock (Claude) → CLI

---

## What eks-agent does NOT do (by design)

This is important.

eks-agent currently does **not**:

- Run `kubectl`
- Access live cluster state
- Modify Kubernetes resources
- Perform auto-remediation
- Use RAG / vector databases
- Use LangChain
- Use MCP (Model Context Protocol)

These features are intentionally deferred to later phases.

---

## Architecture overview

### CLI
- Written in Python
- Runs interactively
- Sends user input to the server
- Reuses a session ID across runs

### Server
- FastAPI application
- Long-running process
- Maintains short-term memory in RAM
- Calls AWS Bedrock
- Builds prompt context explicitly

---

## Conversation model

A single request to the LLM includes:

1. System prompt (rules and behavior)
2. Last N messages from memory (working context)
3. Current user question

This keeps context:
- small
- predictable
- safe

---

## Sessions and memory

### Session
- Identified by a UUID
- Stored on the CLI side in `.eks_agent_session`
- Represents **one conversation**

### Memory
- Stored on the server
- Keyed by `session_id`
- Keeps only the last 6 messages per session
- Cleared when the server restarts

Memory is **short-term working memory**, not long-term knowledge.

---

## Requirements

- Python 3.10 or newer
- AWS credentials with Bedrock access
- AWS Bedrock enabled in your account

No virtualenv is required.

---

## Running the system

### Start the server
```bash
uvicorn eks_agent.server:app --host 127.0.0.1 --port 8080