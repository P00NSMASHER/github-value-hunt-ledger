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

The sixth upgrade inserts a fail-closed authority layer between agent intent and real tool execution:
typed action classes, explicit permissions, allowlists/denylists, rolling budgets, exact-request
human approvals, replay protection, per-agent/global kill switches, and SHA-256 audit receipts.

## Step 7 — Governed autonomous software factory

Status: implemented on this branch.

The seventh upgrade turns approved engineering goals into restart-safe software work:

- each work item is bound to an existing Step-2 acceptance contract;
- only the contract-bound executor can claim the work;
- every attempt gets a unique isolated workspace and attempt branch;
- implementation workers use leases and stale RUNNING attempts can be reclaimed after restart;
- executor leases stop governing the job once independent audit begins;
- submissions bind repository, issue, workspace, branch, attempt, commit, tests, and artifacts;
- READY_FOR_PR requires an independent APPROVED audit of the exact current submission;
- rejected audits retry in fresh workspaces until the retry limit, then fail closed to BLOCKED;
- PR creation requires an exact persisted Step-6 EXTERNAL_WRITE authorization;
- the PR authorization must match work item, repository, branch, base, title, submission hash, and
  audit hash;
- governance authorizations are single-use at the factory boundary;
- merge requires a separate Step-6 PRODUCTION_CHANGE authorization bound to exact PR, head SHA,
  merge method, and audit hash;
- production merge therefore remains behind mandatory human approval and active kill switches;
- the engineering goal becomes COMPLETE only after the governed merge is recorded;
- lifecycle transitions are retained as content-addressed audit events.

The first seven upgrades establish:

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
   ↓
governed autonomous software delivery
```

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Graph connectivity is not proof. Operational power is granted per action under explicit policy,
budget, approval, and kill-switch controls. Software automation may prepare and verify work, but
production authority remains a separate governed decision.
