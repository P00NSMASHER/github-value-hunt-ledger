# AI Business OS

This directory is the incremental implementation of the nine-part AI Business OS upgrade.

## Step 1 — Persistent agent runtime

Status: implemented and merged.

The first upgrade adds a durable worker substrate with:

- persistent agent identities and roles;
- durable goals with explicit state transitions;
- heartbeats and generation numbers for stale-worker recovery;
- append-only, hash-chained event history;
- snapshots and rollback-safe state restoration;
- parent/child agent relationships for delegated workers;
- process-restart persistence via SQLite;
- no dependency on an LLM provider or external service.

## Step 2 — Independent Auditor brain

Status: implemented on this branch.

The second upgrade adds a Manager → Executor → Auditor completion contract:

- manager, executor, and auditor must be distinct agent identities;
- acceptance criteria are frozen before execution;
- executors submit concrete evidence but cannot approve themselves;
- auditors record PASS / FAIL / UNKNOWN for every criterion;
- missing or UNKNOWN required checks fail closed;
- failed audits return work to ACTIVE for revision;
- exact audit reports receive SHA-256 identities;
- the persistent runtime refuses VERIFYING → COMPLETE without an approved independent audit;
- only the assigned manager can accept the approved result.

The runtime remains authority-light. These first two steps coordinate and verify work, but do **not**
yet grant production, email, payment, merge, destructive, or self-improvement promotion authority.

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Persistent memory is evidence, not authority. Completion is also not a self-asserted fact: the
executor's result must cross an independent evidence-backed audit boundary before it can become
COMPLETE. Later upgrades add value memory, governance, action permissions, and skill promotion
without weakening these two invariants.
