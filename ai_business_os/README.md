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

Status: implemented on this branch.

The third upgrade lets agents propose better skills/policies without letting them self-authorize
those changes:

- the current champion remains active while candidates are tested;
- proposer, verifier, and curator are separate identities;
- candidate and baseline artifacts are content-addressed by SHA-256;
- development and held-out evaluation manifests are frozen and disjoint;
- only frozen tasks can be scored, and results are immutable;
- incomplete evaluation fails closed;
- hard regressions quarantine the candidate;
- candidates must improve on development tasks and clear a minimum held-out improvement delta;
- VERIFIED candidates still remain inactive;
- three independent canary agents with zero regressions are required for GLOBAL_ELIGIBLE;
- only the skill's designated curator can explicitly promote a candidate globally;
- promotion is rejected if the champion changed after evaluation;
- known prior champion versions can be explicitly rolled back with evidence.

The first three upgrades therefore establish a chain of:

```
durable work
   ↓
independent completion verification
   ↓
measured learning
   ↓
independently verified promotion
```

They still do **not** grant unrestricted production, email, payment, destructive, or other
consequential permissions. Runtime governance is a later upgrade.

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Every increase in agent autonomy must preserve those boundaries rather than bypass them.
