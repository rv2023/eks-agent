Good catch — tiers are **conceptually different from phases**, and it’s important the README makes that explicit.

Below is a **clean, copy-paste section** you can **append directly** to your README (or insert after “Architecture Overview”).
It explains **tiers**, how they map to phases, and what **final outcomes** the system guarantees.

---

## 🧩 Evidence Tiers (What the Agent Trusts)

The agent uses **strict evidence tiers** to control trust and prevent hallucination.
Tiers define **what information is allowed**, not *when* it is used.

### Tier 1 — Safety Rules (Non-Negotiable)

**Status:** ✅ Always enforced

**What it is**

* Hard constraints baked into the system
* Not data, not prompts, not evidence

**Rules**

* Never guess
* Never invent facts
* Fail closed
* Read-only only
* Deterministic behavior
* No side effects

**Where enforced**

* Everywhere (Phases 2–4)

---

### Tier 2 — Verified Evidence (Trusted Facts)

**Status:** ✅ Implemented

**What it is**

* Ground truth from tools and APIs
* Immutable once ingested

**Examples**

* `kubectl get pods`
* `kubectl describe pod`
* `kubectl logs`
* Kubernetes events
* AWS API responses (read-only)

**Properties**

* Collected only via allowlisted commands
* Stored immutably in `EvidenceStore`
* Scoped by session
* Audited

**Who can use it**

* Phase 2 (to decide what’s missing)
* Phase 3 (to reason)
* Phase 4 (to verify)

👉 **Only Tier-2 evidence is considered factual.**

---

### Tier 3 — Optional Context (Untrusted / Advisory)

**Status:** ❌ Not implemented (by design)

**What it could be**

* Documentation
* Runbooks
* Architecture diagrams
* Historical incidents

**Why it’s not implemented**

* Tier-3 data can mislead diagnostics
* Easy to accidentally override real evidence
* Requires careful isolation

**Future rule**

* Tier-3 may *inform* but never *override* Tier-2
* Never used for proof
* Never cited as evidence

---

## 🔗 How Tiers Map to Phases

| Phase            | Tier(s) Allowed            | Purpose            |
| ---------------- | -------------------------- | ------------------ |
| Phase 1          | Tier 1                     | Enforce safety     |
| Phase 2          | Tier 2                     | Collect facts      |
| Phase 3          | Tier 2                     | Reason about facts |
| Phase 4          | Tier 2                     | Verify facts       |
| Phase 5 (future) | Tier 2 (+ optional Tier 3) | Suggest fixes      |
| Phase 6          | None                       | Human executes     |
| Phase 7          | Tier 2 (offline)           | Learn patterns     |

🚫 **No phase ever treats Tier-3 as truth.**

---

## 🎯 Final Outcomes (What the System Guarantees)

The system has **only three possible terminal outcomes**.

### 1️⃣ Need More Evidence

**Returned by:** Phase 2 or Phase 4

```json
{
  "mode": "need_evidence",
  "commands": [...]
}
```

**Meaning**

* Facts are insufficient
* The agent refuses to reason further
* Only read-only commands are allowed

---

### 2️⃣ Verification Complete (Diagnostic Closure)

**Returned by:** Phase 4

```json
{
  "mode": "verification_complete"
}
```

**Meaning**

* All reasonable hypotheses are verified or eliminated
* No further safe evidence exists
* Automated investigation stops

👉 This is the **intended final state** of the agent.

---

### 3️⃣ Circuit Breaker Triggered

**Returned by:** Phase 2 / Phase 4 guards

```json
{
  "error": "Too many verification loops"
}
```

**Meaning**

* Investigation is looping or stalled
* System fails closed
* Human intervention required

---

## 🧠 What the Agent Will *Never* Output

The agent will **never**:

* Claim certainty without evidence
* Apply fixes
* Execute write actions
* Continue indefinitely
* Override missing data
* “Be helpful” at the cost of correctness

---

## 🧭 Mental Model (Tiers + Phases Together)

> **Tiers decide what can be trusted**
> **Phases decide what can be done**

Or more simply:

> *Facts come before thoughts.
> Proof comes before action.
> Stopping is a success condition.*

---

## ✅ End State Summary

By the time Phase 4 returns `verification_complete`:

* All conclusions are evidence-backed
* No unsafe action paths exist
* Full audit trail is preserved
* The system is safe to use in production
* Human operators take over intentionally

---

Below is a **clean, copy-paste-ready section** you can add to your README under a heading like
**“Comparison vs Typical LLM Agents”**.

It is written to be clear, blunt, and architecture-focused (no marketing fluff).

---

## 🔍 Comparison: This Agent vs Typical LLM Agents

Most “LLM agents” are optimized for **helpfulness**.
This agent is optimized for **correctness, safety, and auditability**.

That difference drives everything in the design.

---

## ⚖️ High-Level Comparison

| Dimension             | Typical LLM Agent | This EKS Agent        |
| --------------------- | ----------------- | --------------------- |
| Primary goal          | Be helpful        | Be correct            |
| Evidence handling     | Implicit / mixed  | Explicit Tier-2 only  |
| Tool usage            | LLM decides       | Deterministic planner |
| Read/write separation | Often mixed       | Strictly read-only    |
| Guessing on gaps      | Common            | Impossible            |
| Stopping condition    | Rare              | Explicit (Phase 4)    |
| Auditability          | Low               | Full, append-only     |
| Production safety     | Weak              | Strong                |
| Regulated readiness   | ❌                 | ✅                     |

---

## 🧠 Reasoning vs Execution

### Typical LLM Agent

* The model reasons **and** decides actions
* Tools are often called directly from the LLM
* Prompts mix:

  * reasoning
  * tool selection
  * execution
* Hard to explain *why* something happened

**Result:**
Fast demos, unsafe systems.

---

### This Agent

* Reasoning and execution are **physically separated**
* LLM:

  * cannot execute tools
  * cannot invent evidence
* Tools:

  * are never selected by the LLM
  * are rendered deterministically by code

**Result:**
Slower, but safe and explainable.

---

## 🧾 Evidence Discipline

### Typical LLM Agent

* Treats:

  * logs
  * user text
  * docs
  * guesses
    as roughly equal inputs
* Hallucinations are hard to detect
* “Sounds right” responses slip through

---

### This Agent

* Explicit evidence tiers:

  * **Tier 1:** Safety rules
  * **Tier 2:** Verified tool output (only truth)
  * **Tier 3:** Optional context (never proof)
* Phase 3 refuses to reason without Tier-2 evidence
* Phase 4 refuses unstructured checks

**Result:**
No hallucinated facts can enter the system.

---

## 🔁 Control Flow

### Typical LLM Agent

```
User → LLM → Tool → LLM → Tool → ...
```

* No hard stop
* Easy to loop forever
* No clear “done” state

---

### This Agent

```
Phase 2 → Phase 3 → Phase 4
     ↑         ↓         ↓
     └─────────┴─────────┘
```

* Explicit loop boundaries
* Circuit breakers
* Deterministic stop condition

**Result:**
The agent knows when to stop.

---

## 🛑 Stopping Is a Feature

### Typical LLM Agent

* Optimized to always respond
* Will keep suggesting ideas even when stuck
* Confidence increases as evidence decreases

---

### This Agent

* Stopping is a **success condition**
* Phase 4 can explicitly return:

  * `verification_complete`
* If no safe progress is possible:

  * agent stops
  * human takes over

**Result:**
No false certainty.

---

## 🔐 Production & Compliance Readiness

### Typical LLM Agent

* Hard to audit
* Hard to reproduce decisions
* Unsafe in regulated environments
* Blurred responsibility boundaries

---

### This Agent

* Every step is audited
* Every decision is reproducible
* No hidden execution
* Clear human execution boundary

**Result:**
Usable in environments with:

* SOC2 expectations
* Change-management requirements
* Incident post-mortems
* Regulated production clusters

---

## 🧠 Mental Model Difference

**Typical LLM Agent**

> “Here’s what I think you should do.”

**This Agent**

> “Here is what we know, what we don’t know, and how to safely prove it.”

---

## 🚦 Why This Design Is Intentionally Conservative

This agent trades:

* speed
* creativity
* autonomy

for:

* correctness
* safety
* trust

That tradeoff is **intentional**.

---

## ✅ Summary

| Question                   | Typical LLM Agent | This Agent |
| -------------------------- | ----------------- | ---------- |
| Can it hallucinate?        | Yes               | No         |
| Can it mutate prod?        | Often             | Never      |
| Can you audit it?          | Hard              | Easy       |
| Does it know when to stop? | No                | Yes        |
| Is it safe by default?     | No                | Yes        |

---

## 🧠 Final Thought

> **Most LLM agents try to replace operators.
> This agent is designed to protect them.**

That difference is the architecture.

---

                ┌────────────────────────┐
User Question ─▶│        /ask API        │
                └────────────┬───────────┘
                             │
               ┌─────────────▼─────────────┐
               │ Phase 1 — Safety Rules     │
               │ • Never guess              │
               │ • No changes               │
               │ • Evidence required        │
               └─────────────┬─────────────┘
                             │
               ┌─────────────▼─────────────┐
               │ Phase 2 — Evidence         │
               │ (Code only)                │
               │ • Read-only commands       │
               │ • kubectl / AWS APIs       │
               │ • Deterministic            │
               └─────────────┬─────────────┘
                             │
               ┌─────────────▼─────────────┐
               │ Phase 3 — Reasoning        │
               │ (LLM, boxed)               │
               │ • Uses evidence only       │
               │ • Produces hypotheses      │
               │ • No tools                 │
               └─────────────┬─────────────┘
                             │
               ┌─────────────▼─────────────┐
               │ Phase 4 — Verification     │
               │ (Code only)                │
               │ • Validates next checks    │
               │ • Read-only only           │
               │ • Stops loops              │
               └─────────────┬─────────────┘
                             │
               ┌─────────────▼─────────────┐
               │ Phase 5 — Explanation      │
               │ (LLM, boxed)               │
               │ • Human-readable summary   │
               │ • Suggested actions        │
               │ • No execution             │
               └─────────────┬─────────────┘
                             │
                          STOP
                   (Human decides next)