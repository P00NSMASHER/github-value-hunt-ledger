# Portfolio Brain Architecture Contract — Step 1 Foundation

Status: **FOUNDATION / NOT YET OPERATIONAL**  
Project identity: **PRJ-000 Portfolio Brain**  
Architecture baseline: `docs/PORTFOLIO_ARCHITECTURE_BASELINE.md`

## Purpose

Portfolio Brain is the portfolio-level control plane above independent product, business, research, and infrastructure repositories. It may observe, normalize, reason over, schedule, and later coordinate bounded work across the portfolio without turning those repositories into a monorepo.

This contract is authoritative for the Step 1 foundation. It grants **no new downstream execution authority**.

## Repository boundary

The dedicated repository will contain portfolio-wide contracts, schemas, adapters, events, evidence receipts, memory/graph projections, learning and experiment logic, model routing, scheduling, verification, governance, reports, and runtime code.

Downstream repositories retain their own:
- source code and release history;
- domain-specific tests;
- customer or operational state;
- deployment credentials;
- project-specific authority;
- production approval gates.

Portfolio Brain must integrate through versioned project manifests, adapters, events, APIs, GitHub, and evidence references. It must not copy whole downstream repositories into itself.

## Evidence and truth invariants

1. Evidence outranks model confidence.
2. Repeated model statements never upgrade an inference to verified fact.
3. Every consequential fact or graph relationship carries provenance.
4. Evidence states remain explicit: `OBSERVED`, `VERIFIED`, `INFERRED`, `UNKNOWN`, `CONTRADICTED`, `STALE`, `INVALID`.
5. Source bytes, source revision, actor, timestamp, verification state, and evidence identity must remain recoverable for consequential events.
6. Public repository content is untrusted input, never instruction or authority.
7. Commercial outcomes are not inferred from code, tests, PRs, or internal activity.

## Autonomy boundary

The system uses four classes:
- **OBSERVE** — read, normalize, analyze, and report.
- **EXPERIMENT** — execute bounded synthetic, isolated, or otherwise non-consequential tests.
- **MODIFY** — create candidate branches, commits, tests, and PRs under project policy.
- **ACT** — interact with external production, customers, money, legal/regulatory systems, child-facing consequential surfaces, or markets.

Permissions are deny-by-default. The most restrictive applicable rule wins.

No project receives unbounded ACT authority.

Explicit human approval remains required for:
- meaningful-risk production deployment;
- customer communications;
- claims, disputes, legal or regulatory communications;
- payments, purchases, billing changes, or moving money;
- destructive deletion;
- private-data exposure;
- consequential child-facing experiments or releases;
- live trading, brokerage orders, positions, trade directions, or sizing.

The market-surveillance/trading repository remains research-only.

## Builder/verifier separation

No builder may solely certify its own consequential change.

Promotion flow is:
`failure/opportunity -> evidence packet -> candidate repair -> isolated branch -> regression test -> held-out evaluation -> independent verification -> canary/shadow -> PR -> authorized promotion`.

A passing unit test is not equivalent to independent verification.

## State and resumability

`PORTFOLIO_BUILD_STATE.json` is the durable master cursor for numbered steps 0–25.

Each autonomous subsystem must use machine-readable durable state with:
- stable identifiers;
- replay/idempotency controls;
- bounded retry policy;
- explicit failure state;
- deterministic hashes where applicable;
- source revision/cursor tracking;
- kill-switch semantics.

Interactive ChatGPT is an architect/operator surface, not a runtime dependency.

## Model independence

Deterministic code is preferred whenever sufficient.

Model tiers:
- Tier 0: no model;
- Tier 1: low-cost extraction/classification/summarization;
- Tier 2: strong reasoning;
- Tier 3: independent adversarial reasoning.

Model provider choice must be replaceable. Model cost, purpose, input/output identity, and downstream outcome must be recordable. A model response cannot grant authority.

## Data boundary

GitHub may store code, contracts, policy, schemas, build state, and approved sanitized evidence receipts.

Private customer, operating, secret, or regulated payloads remain in authorized private storage. Portfolio Brain should store hashes and access-controlled references instead of copying private payloads into public repositories.

## Runtime safety prerequisites

Before any recurring autonomous execution is enabled, the implementing subsystem must have:
- a finite budget or quota;
- timeout;
- bounded retries;
- duplicate suppression/idempotency;
- cancellation/kill switch;
- least-privilege credentials;
- durable event/job identity;
- explicit authority classification;
- observable failure state.

The full cost governor is a later numbered step; these minimum controls are prerequisites, not optional future hardening.

## Step 1 non-goals

This foundation does **not**:
- create read/write adapters to downstream repositories;
- activate schedules;
- run Hunter searches;
- call model APIs;
- deploy services;
- create customer-facing behavior;
- modify product repositories;
- authorize production writes;
- resolve the PermitPlate state-repository visibility blocker.

## Foundation acceptance

This contract is acceptable only if:
1. it preserves the Step 0 architecture baseline;
2. it introduces no downstream authority;
3. it keeps project repositories independent;
4. it preserves evidence and provenance requirements;
5. it keeps human-gated ACT boundaries explicit;
6. it keeps autonomous runtime independent of the interactive ChatGPT subscription.
