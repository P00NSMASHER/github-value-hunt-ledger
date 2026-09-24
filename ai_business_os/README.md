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

Status: implemented and merged.

The seventh upgrade turns approved engineering goals into restart-safe software work with isolated
attempt workspaces, retries, exact independent-audit binding, machine-enforced Step-6 PR/merge
authorization, mandatory human-approved production merge, and goal completion only after the
governed merge is recorded.

## Step 8 — Persistent Evidence / Truth Engine

Status: implemented on this branch.

The eighth upgrade makes proof structure explicit and persistent:

- claims are content-addressed and bound to explicit proof obligations;
- each obligation defines allowed authorities and may require freshness, multiple sources, and
  independent source groups;
- every evidence item binds a source reference and SHA-256 source identity;
- evidence is classified as usable, stale, or inadmissible rather than collapsed into one bucket;
- future-dated evidence cannot prove an earlier claim;
- wrong-authority or explicitly inadmissible evidence remains visible but cannot satisfy an obligation;
- contradictory admissible evidence is preserved and produces CONTESTED rather than being averaged away;
- required proof can resolve to PROVEN, CONTESTED, NOT_PROVEN, or UNKNOWN;
- UNKNOWN means no relevant evidence exists, not that the claim is false;
- every truth receipt binds the exact claim hash, evaluation time, findings, and evidence-set hash;
- next-best-evidence planning uses deterministic counterfactual proof gain, not invented success probabilities;
- hypothetical planning evidence is never inserted into the real evidence ledger;
- duplicate source-independence groups are not treated as independent corroboration;
- next-evidence recommendations are invalidated when the real evidence set changes;
- evidence acquisition requests pass through the Step-6 governance layer before any external action;
- this engine recommends and authorizes evidence acquisition but never bypasses tool permissions or executes external systems itself.

The first eight upgrades establish:

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
   ↓
explicit proof obligations and truth-state reasoning
```

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Graph connectivity is not proof. Operational power is granted per action under explicit policy,
budget, approval, and kill-switch controls. Software automation may prepare and verify work, but
production authority remains separate. A model's confidence is never proof; consequential claims
must resolve through explicit evidence obligations.
