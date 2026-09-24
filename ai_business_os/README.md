# AI Business OS

This directory is the incremental implementation of the nine-part AI Business OS upgrade.

## Step 1 — Persistent agent runtime

Status: implemented and merged.

The first upgrade adds durable worker identity, goals, heartbeats, stale-worker recovery,
hash-chained events, snapshots, rollback-safe restoration, delegation lineage, and restart
persistence.

## Step 2 — Independent Auditor brain

Status: implemented and merged.

The second upgrade adds a hard Manager → Executor → Auditor completion contract. Executors submit
evidence but cannot approve themselves; required acceptance criteria must independently pass before
the runtime permits VERIFYING → COMPLETE.

## Step 3 — Verifier-gated self-improvement

Status: implemented and merged.

The third upgrade allows agents to propose better skills and policies while keeping every candidate
inactive until it passes frozen disjoint development/held-out evaluation, independent verification,
zero-regression checks, multi-agent canary evidence, and explicit curator promotion.

## Step 4 — Value-weighted memory

Status: implemented and merged.

The fourth upgrade teaches the system which remembered tactics actually produce useful results.
Only independently verified outcomes influence learned value; duplicate event credit is blocked,
cross-memory attribution is conserved, objective leakage is prevented, recency is modeled, and
confidence grows gradually with evidence.

## Step 5 — Provenance-preserving knowledge graph

Status: implemented on this branch.

The fifth upgrade connects isolated facts into typed evidence chains:

- typed nodes cover repositories, data, capabilities, technologies, products, businesses,
  customers, experiments, outcomes, and memories;
- typed edge contracts prevent semantically invalid relationships;
- every node carries provenance and every edge carries evidence;
- verified outcomes require an explicit stable business/event identity;
- forecasts and estimates cannot silently become outcome facts;
- aliases resolve to canonical identities without destructive merging;
- ambiguous identity resolution fails closed;
- active duplicate relationships are blocked;
- relationship changes use temporal supersession rather than history deletion;
- historical graph queries can reconstruct prior relationship states;
- evidence-bearing paths expose a hash over the exact provenance chain;
- outcome lineage can trace a verified result back through experiments, products, capabilities,
  repositories, and other upstream evidence;
- nodes with active relationships cannot be silently retired.

The first five upgrades establish:

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
```

They still do **not** grant unrestricted production, email, payment, destructive, or other
consequential permissions. Runtime governance remains a later upgrade.

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Past success is a retrieval prior, not proof that a tactic is correct in a new situation. A graph
edge records an evidence-backed relationship; connectivity alone never upgrades a claim into truth.
Every increase in agent autonomy must preserve those boundaries rather than bypass them.
