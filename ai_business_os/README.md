# AI Business OS

This directory is the incremental implementation of the nine-part AI Business OS upgrade.

## Step 1 — Persistent agent runtime

Status: implemented and merged.

The first upgrade adds a durable worker substrate with persistent identities, goals, heartbeats,
stale-worker recovery, append-only hash-chained events, snapshots, rollback-safe restoration,
delegation lineage, and process-restart persistence.

## Step 2 — Independent Auditor brain

Status: implemented and merged.

The second upgrade adds a hard Manager → Executor → Auditor completion contract. Executors submit
evidence but cannot approve themselves; required acceptance criteria must independently pass before
the runtime permits VERIFYING → COMPLETE.

## Step 3 — Verifier-gated self-improvement

Status: implemented and merged.

The third upgrade lets agents propose better skills and policies while keeping every candidate
inactive until it passes frozen disjoint development/held-out evaluation, independent verification,
zero-regression checks, multi-agent canary evidence, and explicit curator promotion.

## Step 4 — Value-weighted memory

Status: implemented on this branch.

The fourth upgrade teaches the system which remembered tactics actually produce useful outcomes:

- memory items are versioned and content-addressed;
- outcomes enter as evidence-bearing observations;
- observers cannot verify their own outcomes;
- UNVERIFIED and REJECTED observations contribute no learned value;
- verified rewards are bounded to [-1, 1];
- credit for one real-world event is conserved across all memories at a maximum total of 1.0;
- duplicate event credit for the same memory is blocked;
- objective-specific memories cannot silently generalize into unrelated domains;
- global memories may transfer with a deliberate discount;
- recent verified outcomes receive more weight than stale outcomes;
- confidence rises gradually with verified evidence and never jumps to certainty from one result;
- positive verified histories raise retrieval priority, negative histories lower it, and untested
  memories retain a neutral prior;
- retired memories leave the normal retrieval pool without deleting historical evidence.

The first four upgrades establish:

```
durable work
   ↓
independent completion verification
   ↓
controlled self-improvement
   ↓
evidence-weighted organizational memory
```

They still do **not** grant unrestricted production, email, payment, destructive, or other
consequential permissions. Runtime governance remains a later upgrade.

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Past success is a retrieval prior, not proof that a tactic is correct in a new situation. Every
increase in agent autonomy must preserve those boundaries rather than bypass them.
