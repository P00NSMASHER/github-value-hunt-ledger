# AI Business OS

This directory is the incremental implementation of the nine-part AI Business OS upgrade.

## Step 1 — Persistent agent runtime

Status: implemented and merged.

Durable worker identity, goals, heartbeats, stale-worker recovery, hash-chained events, snapshots,
rollback-safe restoration, delegation lineage, and restart persistence.

## Step 2 — Independent Auditor brain

Status: implemented and merged.

Hard Manager → Executor → Auditor completion contracts. Executors submit evidence but cannot approve
themselves; required acceptance criteria must independently pass before VERIFYING → COMPLETE.

## Step 3 — Verifier-gated self-improvement

Status: implemented and merged.

Agents may propose better skills and policies, but candidates stay inactive until frozen disjoint
development/held-out evaluation, independent verification, zero-regression checks, multi-agent
canary evidence, and explicit curator promotion all pass.

## Step 4 — Value-weighted memory

Status: implemented and merged.

Only independently verified outcomes influence learned value. Duplicate event credit is blocked,
cross-memory attribution is conserved, objective leakage is prevented, recency is modeled, and
confidence grows gradually with evidence.

## Step 5 — Provenance-preserving knowledge graph

Status: implemented and merged.

Typed evidence chains connect repositories, data, capabilities, technologies, products, businesses,
customers, experiments, verified outcomes, and memories while preserving provenance and temporal
relationship history.

## Step 6 — Runtime governance/control plane

Status: implemented and merged.

A fail-closed authority layer sits between agent intent and real tool execution: typed action
classes, explicit permissions, allowlists/denylists, rolling budgets, exact-request human approvals,
replay protection, per-agent/global kill switches, and SHA-256 audit receipts.

## Step 7 — Governed autonomous software factory

Status: implemented and merged.

Approved engineering goals become restart-safe software work with isolated attempt workspaces,
retries, exact independent-audit binding, machine-enforced Step-6 PR/merge authorization, mandatory
human-approved production merge, and goal completion only after governed merge.

## Step 8 — Persistent Evidence / Truth Engine

Status: implemented and merged.

Consequential claims are resolved through explicit proof obligations, typed evidence, authority,
freshness, source independence, contradiction preservation, exact truth receipts, next-best-evidence
planning, contradiction-aware adjudication, stale-receipt invalidation, and Step-6-governed evidence
acquisition.

## Step 9 — Evidence-first portfolio capital allocator

Status: implemented on this branch.

The final upgrade turns the system's evidence into transparent resource-prioritization support:

- initiatives may bind to Step-5 BUSINESS / PRODUCT identities;
- policies are human-controlled, versioned, immutable, and content-addressed;
- metric-specific source rules distinguish realized cash, contracted pipeline, qualified pipeline,
  operational effort, and softer market/strategy signals;
- fake or weak realized-cash evidence fails closed;
- future-dated and stale evidence is rejected;
- a fixed core metric schema prevents cherry-picked evidence coverage;
- snapshot-date skew is bounded before initiatives may be compared;
- monetary magnitude is converted into a dimensionless economic index before mixing with effort,
  timing, and evidence signals;
- every ranking exposes realized net cash, economic value, economic index, signal bonus, effort
  penalty, evidence coverage, raw score, and final decision-support score;
- low-evidence initiatives become OBSERVE_ONLY instead of receiving false precision;
- negative economics can surface PAUSE_REVIEW;
- allocation plans support AI units, engineering hours, human hours, and cash;
- concentration caps prevent one initiative from consuming an unlimited portfolio share;
- cash allocation remains integer-exact in cents;
- newer business data or a newer allocation policy invalidates authorization of an old plan;
- all real resource allocations pass through Step-6 governance;
- cash allocation is MONEY_MOVEMENT and therefore remains behind mandatory human approval;
- kill switches override allocation authority;
- exact plan/ranking/resource hashes prevent approval replay or substitution;
- the allocator proposes decisions but never directly moves money or commits resources.

## Full stack

```
persistent workers
      ↓
independent acceptance
      ↓
verifier-gated learning
      ↓
value-weighted memory
      ↓
provenance knowledge graph
      ↓
runtime governance
      ↓
autonomous software factory
      ↓
truth / proof engine
      ↓
portfolio capital allocator
      ↓
measured outcomes
      └──────────────→ memory + graph + learning loop
```

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### System design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Graph connectivity is not proof. Operational power is granted per action under explicit policy,
budget, approval, and kill-switch controls. Software automation may prepare and verify work, but
production authority remains separate. Model confidence is never proof. Portfolio scores are
decision support, not predictions or guaranteed returns. Consequential action remains governed.
