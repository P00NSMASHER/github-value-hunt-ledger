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

Fail-closed operational authority using typed action classes, explicit permissions,
allowlists/denylists, rolling budgets, exact-request human approvals, replay protection,
per-agent/global kill switches, and SHA-256 audit receipts.

## Step 7 — Governed autonomous software factory

Status: implemented and merged.

Approved engineering work becomes restart-safe isolated implementation attempts, independent audits,
governance-bound PR creation, mandatory human-approved production merge, retries/reconciliation, and
goal completion only after the governed merge.

## Step 8 — Persistent Evidence / Truth Engine

Status: implemented and merged.

Consequential claims resolve through explicit proof obligations, typed source authority, freshness,
admissibility, independence, contradiction handling, content-addressed truth receipts, deterministic
next-best-evidence planning, stale-receipt invalidation, and Step-6-governed evidence acquisition.

## Step 9 — Reversible entity canonicalization

Status: implemented and full-regression verified.

The final upgrade gives the Business Brain a clean single view of duplicate real-world identities
without deleting source provenance:

- canonicalization applies to repositories, data sources, technologies, products, businesses, and
  customers;
- deterministic matching uses normalized names, aliases, description overlap, graph context, and
  authoritative hard identifiers;
- conflicting hard identifiers such as EIN/UEI/DUNS/repository IDs force KEEP_SEPARATE;
- matches resolve to AUTO_MERGE, REVIEW, or KEEP_SEPARATE;
- ambiguous REVIEW matches require explicit HUMAN review evidence;
- match evidence is bound to the exact source provenance hashes used during comparison;
- canonical field survivorship uses explicit positive source weights;
- all conflicting source values and losing values remain visible in the canonicalization ledger;
- source records are marked CANONICALIZED rather than deleted;
- original canonical keys, labels, and aliases resolve to the active canonical entity;
- new graph writes cannot silently continue attaching to inactive duplicate records;
- canonical relationship views collapse duplicate semantic edges while preserving every underlying
  evidence edge;
- merges are reversible when doing so will not orphan live canonical relationships;
- reversal restores source statuses and original alias bindings while retaining the derived entity
  as REVERSED historical evidence;
- canonical identity resolution is transitive across multi-stage merges;
- original leaf-source lineage remains visible after nested canonicalization;
- older merges cannot be reversed underneath a newer active merge;
- corporate mergers/acquisitions are not confused with duplicate identity when authoritative legal
  identifiers differ.


## Executive extension — Evidence-first portfolio capital allocator

Status: implemented on this branch.

This extension sits above the verified nine-upgrade foundation and turns operating evidence into
transparent resource-prioritization support without replacing the foundation's human/governance
boundaries:

- initiatives may bind to canonical Step-5/9 BUSINESS and PRODUCT identities;
- allocator policies are HUMAN-controlled, immutable, versioned, and content-addressed;
- metric-specific source rules distinguish realized cash, contracted pipeline, qualified pipeline,
  operational effort, and softer market/strategy signals;
- realized cash cannot be sourced from model estimates or generic CRM fields;
- future-dated and stale evidence is rejected;
- a fixed core metric schema prevents cherry-picked evidence coverage;
- snapshots must be temporally comparable before initiatives are ranked;
- monetary magnitude is converted to a dimensionless economic index before combination with effort,
  time-to-cash, and evidence signals;
- every ranking exposes its components instead of hiding them behind an opaque score;
- low-evidence initiatives become OBSERVE_ONLY rather than receiving false precision;
- negative economics can surface PAUSE_REVIEW;
- bounded plans support AI units, engineering hours, human hours, and exact cash cents;
- concentration caps prevent a single initiative from consuming an unlimited portfolio share;
- newer business data or a newer allocation policy invalidates old authorization;
- every real allocation passes through Step-6 governance;
- cash allocation is MONEY_MOVEMENT and therefore remains behind HUMAN approval;
- kill switches override allocation authority;
- exact plan/ranking/resource hashes prevent approval substitution or replay;
- the allocator proposes decisions but does not transfer funds or commit resources itself.

The allocator is decision support, not a success-probability model or guaranteed-return engine.

## Complete architecture

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
   ↓
clean, reversible canonical business identity
   ↓
evidence-first portfolio prioritization (executive extension)
```

### Run all AI Business OS tests

```bash
python -m unittest discover -s ai_business_os -p "test_*.py"
```

### Design rules

Memory is evidence, not authority. Completion is not self-asserted. Learning is not deployment.
Graph connectivity is not proof. Operational power is granted per action under explicit policy,
budget, approval, and kill-switch controls. Production authority remains separate from software
automation. Model confidence is never proof. Canonical identity is never permission to erase source
history.

Nine-upgrade foundation status: **9/9 implemented and full-regression verified.**

Executive capital-allocation extension: **implemented and regression-tested on this branch.**


## Canonical production boundary — Phase 1

- **Canonical implementation:** `ai_business_os/`
- **Legacy implementation:** `business_os/` is frozen by Git-blob manifest and is not an active development target.
- **Public repository:** source/tests/contracts plus sanitized migration source only.
- **Private operating state:** `ai_business_os_prod`.
- **Database definition:** `supabase/migrations/ai_business_os/`, with exact live migration statement hashes and a live schema fingerprint.
- **Canonical CI:** runs on pull requests and pushes to `main`, uses immutable GitHub Action SHAs, and executes the full `ai_business_os` regression suite.


## Production-use CEO Command Center operator

The production-use bridge adds a human-facing orchestration layer without weakening the existing
governance model:

- live command-center, portfolio, approval, and planning state is read from `ai_business_os_prod`;
- ordinary-language objectives become deterministic, content-addressed proposals;
- proposal creation is read-only;
- only the requesting HUMAN may activate the exact proposal hash;
- activation creates a PENDING internal goal and grants no external-write authority;
- likely external/prod/money/destructive intent is surfaced before execution;
- human approval decisions are bound to the live `request_key` + `intent_hash` and use the
  existing production `approval_decide` procedure;
- the command center never consumes approvals or executes the consequential action itself.

See `CEO_COMMAND_CENTER_CONTRACT.md`, `ceo_command_center.py`, and
`test_ceo_command_center.py`.


## Canonical rights/provenance boundary

Hunter, Freight, RecoveryWorks and AI Business OS now share one operational rights model:

- public license evidence, owner attestations and executed permissions are distinct evidence classes;
- every scope is resolved independently;
- generic assertions never auto-promote a component to runtime readiness;
- `ALLOWED_WITH_CONDITIONS` stays conditional;
- missing or denied required scopes fail closed;
- historical subsystem notes remain provenance, not operating authority.

Public mirror: `rights/RIGHTS_REGISTRY.json`.
Private operating registry: `ai_business_os_prod.rights_*`.


## Verified external outcomes → memory → allocation

The final repository-plan layer closes the real-world learning loop.

A new external outcome must bind an active initiative, exact evidence source, SHA-256, creator, and
an independent Finance/Auditor verifier. B2B commercial outcomes may mirror into the revenue loop;
they cannot enter verified value memory until revenue attribution totals exactly 1.0. Consumer/R&D
playtest outcomes are directly initiative-attributable after independent verification.

Verified outcomes can refresh only the affected portfolio pool. Outcome-derived allocator metrics
use the `VERIFIED_OUTCOME_LEDGER` source class. Repository activity, test counts, branch counts,
and architecture growth are never treated as external outcomes.

Current live state remains fail-closed: there are zero real verified external outcomes, so no
initiative has become allocation-ready merely because this mechanism was implemented.
