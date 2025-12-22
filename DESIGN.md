Below is a **complete design document** you can share with reviewers (engineering, security, SRE, architecture).
It is written to **defend the design**, not just describe it.

You can copy-paste this as `DESIGN.md` or attach it to a review.

---

# Design Document

## Safe, Evidence-Based Kubernetes / EKS Troubleshooting Agent

---

## 1. Purpose

This document explains the **architecture, safety model, and design decisions** behind the EKS troubleshooting agent.

The goal is to answer three reviewer questions clearly:

1. **What does this system do?**
2. **Why is it safe for production?**
3. **How is it different from typical LLM agents?**

---

## 2. Problem Statement

Operating Kubernetes in production requires:

* Accurate diagnosis
* Strong safety guarantees
* Clear auditability
* Human accountability

Most AI agents today:

* Guess based on text
* Mix reasoning and execution
* Allow LLMs to choose tools or actions
* Are unsafe in regulated or production environments

**This system intentionally avoids those failure modes.**

---

## 3. Non-Goals (Explicit)

This system does **not** aim to:

* Auto-remediate production issues
* Execute commands autonomously
* Replace human operators
* Act without verified evidence
* Learn online or modify itself at runtime

These are conscious design exclusions.

---

## 4. High-Level Architecture

The system is built as a **strict, phased pipeline**:

```
User Question
   ↓
Phase 1 — Safety Rules (code)
   ↓
Phase 2 — Evidence Collection (code)
   ↓
Phase 3 — Reasoning (LLM, boxed)
   ↓
Phase 4 — Verification Planner (code)
   ↓
Phase 5 — Explanation (LLM, boxed)
   ↓
STOP (Human acts outside system)
```

Each phase has **non-overlapping responsibilities**.

---

## 5. Phase Breakdown

### Phase 1 — Safety Rules (Code)

**Purpose**

* Enforce non-negotiable constraints

**Key rules**

* No guessing
* No action without evidence
* No production changes
* Fail closed

**Rationale**
Safety must be enforced in code, not delegated to a probabilistic model.

---

### Phase 2 — Evidence Collection (Code)

**Purpose**

* Ensure all reasoning is grounded in facts

**Behavior**

* Detects missing evidence
* Requests exact, read-only commands
* Uses only allowed tooling (kubectl, AWS APIs)

**Properties**

* Deterministic
* Auditable
* No LLM involvement

---

### Phase 3 — Reasoning (LLM, Boxed)

**Purpose**

* Interpret evidence like a senior SRE

**Inputs**

* Tier-2 verified evidence only

**Outputs**

* Hypotheses
* Confidence
* Optional next checks (descriptive)

**Explicit restrictions**

* Cannot run tools
* Cannot generate commands
* Cannot modify state
* Cannot loop

**Rationale**
LLMs are good at interpretation, not control.

---

### Phase 4 — Verification Planner (Code)

**Purpose**

* Prevent unsafe or unnecessary follow-ups

**Behavior**

* Converts LLM suggestions into:

  * Deterministic
  * Read-only
  * Allow-listed checks
* Deduplicates evidence
* Enforces circuit breakers
* Refuses unsafe requests

**Why this phase exists**
Without Phase 4, the LLM would implicitly control execution.
Phase 4 keeps **all power in code**.

---

### Phase 5 — Explanation (LLM, Boxed)

**Purpose**

* Produce a clear, human-readable explanation

**Outputs**

* Summary
* Root cause
* Evidence used
* Confidence
* Suggested human actions (plain English)

**Restrictions**

* No commands
* No follow-up questions
* No execution

**Rationale**
This is a communication task, not a control task.

---

## 6. Evidence and Tier Model

### Tier 1 — Safety Rules

* Hardcoded invariants
* Cannot be bypassed

### Tier 2 — Verified Evidence

* kubectl output
* AWS API responses
* Logs, events, descriptions

Only Tier-2 data is allowed into reasoning.

### Tier 3 — Documentation (Future)

* Optional reference material
* Not used for reasoning today

---

## 7. Why Phase 4 Is Critical

A common reviewer question:

> “Why not let the LLM decide what to check next?”

**Answer:**

* LLMs are probabilistic
* Production systems must be deterministic
* Safety must be auditable

Phase 4 ensures:

* The LLM never selects tools
* The LLM never escalates itself
* The system always knows when to stop

---

## 8. Auditability

Every phase emits structured audit logs:

* Inputs
* Decisions
* Outputs
* Evidence references

This enables:

* Incident reviews
* Compliance audits
* Postmortems
* Security reviews

---

## 9. Comparison vs Typical LLM Agents

| Aspect               | Typical LLM Agent | This System      |
| -------------------- | ----------------- | ---------------- |
| Tool choice          | LLM decides       | Code decides     |
| Execution            | Automatic         | Never            |
| Safety               | Prompt-based      | Enforced in code |
| Auditability         | Weak              | Strong           |
| Production readiness | Low               | High             |

---

## 10. Failure Modes and Mitigations

| Failure           | Mitigation                      |
| ----------------- | ------------------------------- |
| Missing evidence  | Phase 2 refusal                 |
| LLM hallucination | Phase 4 validation              |
| Infinite loops    | Circuit breaker                 |
| LLM outage        | Deterministic fallback possible |
| Unsafe suggestion | Rejected in code                |

---

## 11. Security Model

* Read-only tooling only
* Allow-list enforced
* No shell execution
* No write permissions
* No credentials exposed to LLM
* No side effects

---

## 12. Why Phase 6 Is Skipped

Phase 6 (execution) is intentionally out of scope.

Reason:

* Humans must own production changes
* Accountability cannot be delegated to AI
* This keeps the system safe and reviewable

The system stops after explanation.

---

## 13. Extensibility (Future)

Planned but not implemented:

* Offline learning (post-incident analysis)
* Additional evidence sources
* Better test coverage

Explicitly not planned:

* Autonomous remediation
* Self-healing loops
* Unbounded agents

---

## 14. Final Design Principle

> **The LLM is a consultant, not an operator.
> Code enforces safety. Humans own decisions.**

This principle guided every design choice.

---

## 15. Reviewer Summary (TL;DR)

* This is **not** an autonomous AI agent
* It is a **controlled diagnostic system**
* LLM usage is limited, boxed, and auditable
* No production changes are ever made
* Humans remain fully in control