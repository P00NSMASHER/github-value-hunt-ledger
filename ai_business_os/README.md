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

Status: implemented on this branch.

The sixth upgrade inserts a fail-closed authority layer between agent intent and real tool execution:

- actions are classified as READ, INTERNAL_WRITE, EXTERNAL_WRITE, PRODUCTION_CHANGE,
  MONEY_MOVEMENT, DESTRUCTIVE, or POLICY_CHANGE;
- agents with no governance policy fail closed;
- policies are versioned and content-addressed;
- policies can set class permissions, action allowlists, and explicit action denylists;
- rolling limits can cap action counts, abstract cost units, and money movement;
- external writes require human approval by default;
- production changes, money movement, destructive actions, and governance-policy changes can never
  bypass human approval;
- approval tickets bind to one exact immutable intent hash and expire;
- approvals and authorized requests are single-use, preventing replay;
- budgets and kill switches are rechecked immediately before final authorization;
- global and per-agent kill switches override normal permissions;
- every ALLOW, DENY, and REQUIRE_APPROVAL decision emits a SHA-256-bound audit receipt;
- this layer authorizes actions but does not itself execute tools.

The first six upgrades establish:

```
durable work
   ↓
independent completion verification
   ↓
controlled self-improvement
   ↓
evidence-weighted organizational memory
   ↓
provenance-preserving relationship reasoning
   ↓
bounded operational authority
```

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Graph connectivity is not proof. Operational power is granted per action under explicit policy,
budget, approval, and kill-switch controls. HUMAN identity in this reference layer must be bound to
an authenticated identity/session by the production integration rather than accepted from arbitrary
user-supplied strings.
