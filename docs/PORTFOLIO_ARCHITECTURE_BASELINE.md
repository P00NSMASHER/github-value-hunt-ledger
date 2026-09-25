# Portfolio Brain — Step 0 architecture baseline

Architecture version: `0.1.0`. Scope: reconnaissance and integration decisions only.
Canonical continuation state: [`../PORTFOLIO_BUILD_STATE.json`](../PORTFOLIO_BUILD_STATE.json).
Exact source identities, changed paths, queue observations and test receipts:
[`PORTFOLIO_STEP0_EVIDENCE.json`](PORTFOLIO_STEP0_EVIDENCE.json).

## 1. Handoff and evidence rules

The completed ten-step parallel prework is retained unchanged at
`portfolio_prework/`, inherited from `portfolio-parallel-prep` commit
`bd169dba2539de9e9fa9338c063b60f453d903de`. Both supplied attachments match
that commit. All ten artifact blob identities in the evidence bundle were
recomputed successfully. Its 12 project IDs, aliases, autonomy matrix, hard
gates, 47-workflow inventory, 367-test-path inventory and 14 dependency manifests
remain the historical baseline. Master steps 0–25 have a separate cursor;
the prework's completed steps 1–10 do not mean master steps 1–10 are complete.

Only REPO-001 and REPO-003 were refreshed. The five other repositories retain
their prework observation dates; they are cached, not certified current today.
Source code establishes implemented mechanisms. Synthetic test success establishes
the tested contract. Neither establishes production operation, independent human
identity, customer outcomes, commercial value or a complete autonomous cycle.
The supplied bundle's historical PASS labels remain historical evidence.

| Repository ID | Pinned source for this baseline | Treatment |
|---|---|---|
| REPO-001 | `b7e4a7505f0406b0a80716eab9c09d81df8a2ecb` | Delta from `b47f95caa658a9b12536cc9946d81d51f944c6ac`: 42 commits, 33 paths |
| REPO-002 | `8ebe583f6dae6a832bae2f4987c6919db41eaf5e` | Cached StarBlox evidence |
| REPO-003 | `a15c7c2214a065707123e9b8ab8ac51a42240345` | Delta from `2b78aed7695374b35ad207c43bec9d61486d056a`: 49 commits, 17 paths |
| REPO-004 | `579730f1abb595579de199277a95a8c89f733d0f` | Cached surveillance research evidence |
| REPO-005 | `7c9a8fc4dd9fa12275d336beb8eb10732718666a` | Cached PermitPlate application evidence |
| REPO-006 | `c64fe06a22c3826c9ad3a7b85a4f911a6e589c19` | Integration blocked pending visibility/access review |
| REPO-007 | `3b5867c422cbf9da08d02f1b9c6e7c8afa5b42ba` | Cached CaptureBrief evidence |

## 2. Portfolio identity and implementation map

`portfolio_prework/PROJECT_ID_REGISTRY.json` remains canonical for identity.
Registry status describes the portfolio record, not deployment verification.

| Project | Existing implementation / evidence | Portfolio Brain boundary |
|---|---|---|
| PRJ-000 Portfolio Brain | Reserved identity; this baseline | Dedicated future repository; portfolio contracts, adapters and orchestration |
| PRJ-001 RecoveryWorks | REPO-001 `recoveryworks/`: RecoveryOS proof, reconciliation, ingestion, custody, durable ledger, Scan 360 and 18 recovery divisions | Consume authorized aggregate evidence; retain settlement and claim authority in the project |
| PRJ-002 Freight Recovery | REPO-001 `freight/`: commercial workflow, audit evidence, authorization, pilot and settlement gates | Child of PRJ-001; distinguish a calculated claim from independently evidenced cash |
| PRJ-003 PermitPlate | REPO-005 `pipeline/`, `operations/`; REPO-006 operational state | Observe permitted application receipts first; REPO-006 adapter disabled |
| PRJ-004 CaptureBrief | REPO-007 `capturebrief_core/`: source policy, decision trace, reference/authority resolution, delivery and outcomes | Preserve public/non-sensitive source and human delivery boundaries |
| PRJ-005 StarBlox | REPO-002 learning/QA, artwork, avatar/market/home/Buddy systems; `docs/AI_DEVELOPMENT_FACTORY.md` | Reuse content certification and bounded factory concepts; verify runtime/mirror authority before later integration |
| PRJ-006 ABVM | REPO-003 parent PWA, school-pack refresh, device checkoffs | Source freshness and parent-facing delivery; current UI delta described below |
| PRJ-007 Market Surveillance | REPO-004 point-in-time data, blind evaluation, model/graph research and evidence | Research only; external/live action prohibited by inherited matrix |
| PRJ-008 Hunter | REPO-001 `intelligence/`, `production/`, `tools/ti_*`, `hunters/`, scouts | Existing discovery, learning, claim/lease, repair and promotion path |
| PRJ-009 AI Business OS | REPO-001 `ai_business_os/` and versioned database definition | Canonical reusable governance, truth, memory, graph, factory and operator infrastructure |
| PRJ-010 Browser Gateway | Registered in prework as in development | Implementation/deployment not established by this delta; obtain exact source evidence before adapter work |
| PRJ-011 Evidence Data Ledgers | REPO-001 `production/{fmc_tariff,hospital_mrf,tic_mrf,urdb}_ledger/` | Source-bound data evidence; domain applicability still needs proof |

The full prework inventory retains ScopeSignal, commission/payout assurance,
Recovery Proof SLA, AP Leakage Assurance, Money-State Integrity and other commercial
concepts/experiments. Do not invent new top-level IDs or represent concepts as
validated businesses. Step 2 may give narrower entities stable IDs while preserving
existing project identities and aliases. Future projects enter through registration.

## 3. REPO-001 delta: reuse decisions

The paths below are relative to REPO-001 at its pinned source above. Added Python
modules and their tests were retrieved in full and inspected; queue state was reduced to
non-sensitive metadata. Every changed path is retained in the evidence receipt.

| Existing capability | Observed behavior | Reuse and remaining boundary |
|---|---|---|
| `ai_business_os/ceo_command_center.py` | Deterministic objective routing, hashed proposals, dashboard, explicit-human PENDING goal creation and exact intent approval decision | Reuse as operator surface. Keyword routing is an advisory classification, never execution authorization |
| `ai_business_os/portfolio_planning.py` | Stable work IDs and plan hash; RESEARCH/BUILD/VERIFY routing from initiative gaps; Hunter only for explicit public technical source types | Reuse planning packets. BUILD is planning only; add decision-value experiment prioritization later |
| `ai_business_os/production_bridge.py` | Injected executor, fixed SELECT surfaces, schema fingerprint guard, business/approval/planning reads | Reuse for private observation with independently enforced least-privilege credentials; SQL text checks alone are not a privilege boundary |
| `ai_business_os/runtime_service.py`, `Dockerfile.runtime` | HTTP operator routes, gateway adapter, 30-second health probe, read-only startup smoke, optional bootstrap objective activation | Reuse private runtime seam. Liveness probing does not execute queued work or prove 24/7 learning; bootstrap stays disabled for portfolio observation |
| `supabase/functions/ai-business-os-runtime-gateway/index.ts` | Named operations; server-side database access; token authentication; PENDING goal and approval-decision writes as well as reads | Do not share its write-capable credential with observers or autonomous workers. Authenticate human identity outside model/body assertions; verify deployment/RBAC separately |
| `tools/public_repo_scout.py` | Revision/root caches, persisted queue-pair suppression, bounded retries and rate-limit waits, API metrics | Reuse cheap candidate intake. Root reads currently use branch refs; future evidence enrichment must bind bytes to exact commits |
| `.github/workflows/public-repo-hunter.yml` | Scheduled/manual scouts; corrected conditional git staging; shared main-writer concurrency | Existing self-triggering discovery source. Its write permission is not Portfolio Brain authority; observe receipts, preserve existing ownership |
| `intelligence/scout_queue/HUNTER-*.json` | Fourteen version-2 queue snapshots, `PRE_VERIFICATION_DISCOVERY_ONLY` | Intake candidates through existing runbook/claims/verifier. Counts and triage scores are activity, not capability or value proof |

The queues contain 222 candidate rows before cross-queue deduplication. Their
generated timestamps and API metrics are source assertions retained with blob
identities, not independently certified workflow executions. No candidate project
was executed during this reconnaissance. No matching Actions run was returned
for the exact REPO-001 source head when queried; local focused test results are
recorded separately rather than labeling current-head CI green.

The scout still ranks metadata signals such as popularity, recency and root names.
It does not implement the requested downstream-value objective. Its corpus string
dedupe and replaceable per-worker queue are insufficient as the universal negative
knowledge ledger. Retain the existing TI immutable intake, exact revision/capability
identity, experiment linkage and outcome attribution when connecting it later.

## 4. REPO-003 delta: corrected architecture understanding

The delta changes the runtime as well as its appearance. `pages/app.js` now uses
direct `localStorage` checkoffs and a study-pack-only fetch path; the former imports
of storage, installation, calendar/event and school-model modules are removed.
The app no longer calls the earlier annual-calendar merge/IndexedDB helpers.
The service worker still caches those module files and the annual calendar, and
offers a network-error cache fallback. Cached files do not establish active runtime
integration or the former validated last-good data semantics. A legacy `./game/`
link also reappears in source; this does not establish a restored deployed game.

`package.json` keeps floating `latest` dependencies. `qa:static` is narrowed to
the app syntax check and revised validator; `qa:e2e` now selects only
`tests/gold-standard.spec.mjs`. The other retained browser suites are not invoked
by that command. `qa:unit` remains defined but absent from the cached unchanged
QA workflow invocation. The new validator checks restored UI markers and selected
assets, while several older data/persistence/style validations have been removed.

GitHub reports successful QA at the exact source head in run `36103280547`, plus
deployment and health runs. That verifies the configured narrowed suite, not the
entire inherited test inventory. Record a coverage gap for future project work;
do not replace the authoritative test inventory with the smaller invoked set.

The two deltas add five test paths (four AI Business OS, one ABVM). An additive
view is therefore 372 test paths at the mixed pinned sources, while the preserved
snapshot remains 367. The 47 workflow paths and 14 discovered dependency-manifest
paths are unchanged. The new runtime container and pinned gateway npm import add
runtime dependencies outside that manifest count; deployment reproducibility
needs separate verification.

## 5. Canonical reuse, overlaps and missing integration

| Domain | Canonical existing foundation | Remaining portfolio work |
|---|---|---|
| Truth | `ai_business_os/truth_engine.py`: proof obligations, source authority, contradiction/freshness, receipts | Preserve native verdicts; explicitly map them to OBSERVED/VERIFIED/INFERRED/UNKNOWN/CONTRADICTED/STALE/INVALID without upgrading repeated assertions |
| Memory | `ai_business_os/value_memory.py`; Hunter `production/learning_engine.py` | Business verified-outcome memory and search-strategy learning remain distinct projections of shared evidence, with conserved attribution |
| Graph / identity | `ai_business_os/knowledge_graph.py`, `entity_canonicalization.py`; TI capability graph | Extend types/relations through adapters and reversible mappings; graph connectivity never supplies missing proof |
| Governance / verifier | `governance.py`, `verification.py`, production approval procedures | Translate four autonomy classes into exact action contracts; separate identities/credentials, evaluator evidence and authenticated human authority |
| Persistent roles / factory | `persistent_agents/runtime.py`, `software_factory.py`; StarBlox factory | Reuse durable lifecycle/leases and product-specific tests; supply bounded execution adapters and independent audit, not another competing task authority |
| Learning / repair | TI failure spool, `production/repair_queue.py`, skill-evaluation/promotion intake, `self_improvement.py` | Extend beyond search only after preserving frozen evaluation, benchmark, canary and approval gates |
| Allocation | `capital_allocator.py`, TI allocator and new `portfolio_planning.py` | Reconcile resource envelopes and work plans; retain components and evidence; add highest-value-uncertainty experiment selection |
| Events / runtime | AI Business OS hash-chain events, TI immutable spools, scout queues, new private HTTP runtime | Universal versioned envelope, source adapters, replay/idempotency, cursor persistence, scheduling, provider abstraction and bounded worker execution remain to be integrated |
| Operator / dashboard | New command center, runtime dashboard endpoint, existing reports | Extend coverage to all registered projects and uncertainty/outcome/cost data; avoid building a second approval queue |

`business_os/` is frozen legacy reference; `ai_business_os/` is canonical. Do not
revive the legacy implementation. The existing SQLite reference runtime and private
production schema also have distinct persistence roles. Require explicit schema
mapping and conformance tests before treating them as interchangeable. Hunter
planning, scout intake and production goals must reconcile through durable IDs;
they must not become three independent authorities for the same job.

## 6. Target architecture and authority

Portfolio Brain will be a dedicated control repository with small, versioned
contracts and adapters. Individual projects retain their code and domain state.
Prefer a pinned canonical package/API for reuse; avoid copying an uncontrolled
fork of AI Business OS. A later extraction requires compatibility tests and source
provenance, with ownership remaining explicit.

Observation receipts feed immutable event intake. Deterministic projections build
truth, memory and graph views. The planner plus uncertainty engine proposes bounded
experiments or hunts. Existing leases and governance mediate workers; a distinct
verifier evaluates frozen outputs before canary and promotion. Outcomes update
attribution and future scheduling. Model APIs are replaceable workers, never
the source of authority; Tier 0 deterministic processing is the default.

GitHub holds code, schemas, policies, approved sanitized receipts and build state.
Private operating/customer data remains in its authorized private store. Store
hashes and access-controlled evidence references in GitHub rather than copying
private payloads into public branches. Public repository text is untrusted data,
not instructions or authority. Candidate code executes only in bounded disposable
environments under the experiment contract.

All prework hard gates remain applicable. OBSERVE and bounded EXPERIMENT/MODIFY
do not grant ACT. Production deployment, customer/legal communications, claims,
payments/purchases/billing, destructive deletion, private disclosure and consequential
child-facing changes require explicit human authority. PRJ-007 live trading,
brokerage execution, autonomous positions, trade directions and sizing remain
prohibited. Builders cannot approve their own promotion. An imported workflow
credential or a body field saying HUMAN cannot confer owner authority.

The full cost governor is scheduled for Step 20, but minimum ceilings, bounded
retries, idempotency, timeout and kill-switch checks are prerequisites for any
earlier recurring execution. Step 8/9 readiness must include those controls. This
is an architectural dependency, not permission to skip steps or activate now.

## 7. Open gates and limits

1. **BLK-001:** REPO-006 visibility/access review remains open. No read adapter,
   event ingestion, mirroring or state integration is authorized for it here.
2. **Runtime integration:** deployment availability, effective database privileges,
   human identity binding and independent verifier credentials were not inspected
   live. Reuse requires private integration evidence; a token-protected endpoint
   and successful mock tests do not settle these questions.
3. **Autonomous cycle:** no observed end-to-end portfolio loop or provider/cost
   accounting. Preserve Hunter's existing restart, benchmark and promotion gates.
4. **ABVM coverage:** narrowed active validation and changed persistence/calendar
   behavior require explicit project-level regression evidence before reliance.
5. **Dependencies:** inherited floating/unlocked dependencies remain recorded;
   exact source commits alone do not make installed environments reproducible.
6. **Evidence gaps:** cached StarBlox runtime authority, Browser Gateway implementation
   and real commercial outcomes need specific evidence at their integration steps.
7. **Step 1 repository creation:** the connected GitHub tools available in this
   turn support branch/file/commit writes but expose no repository-creation action.
   Recheck available capabilities at Step 1; if still unavailable, prepare the
   complete foundation and request only the missing repository-creation action.

## 8. Verification and resume

Verification receipts in `PORTFOLIO_STEP0_EVIDENCE.json` bind tests to source hashes,
commands and scope. Existing prework tests, new baseline consistency tests, 32
focused AI Business OS tests and 8 scout tests run locally with synthetic inputs.
No live database, model calls, scout searches, customer actions or deployments are
part of these tests. ABVM uses its already completed exact-source CI receipt;
the browser suite was not rerun locally. Gateway code received static inspection,
not a live integration test. This baseline is not a system security certification.

Step 0 is committed on `portfolio-brain-step0-20260925` in the Hunter repository,
which hosts the preserved prework. This is an isolated architecture branch, not a
change to product main branches. On CONTINUE, read root `PORTFOLIO_BUILD_STATE.json`
first. It names Step 1 as the next pending step and points back to the immutable
prework. Create the dedicated Portfolio Brain foundation only in that next cycle;
carry the state/provenance forward without duplicating product repositories.
