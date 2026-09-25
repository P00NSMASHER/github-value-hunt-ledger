# Portfolio Intelligence System — Architecture Baseline

**Step:** 0 — Full architecture reconnaissance  
**Date:** 2026-09-25  
**Control branch:** `P00NSMASHER/github-value-hunt-ledger@portfolio-brain/step-0-architecture-baseline`  
**Base commit:** `1ea7fff759ff592734d15e4170a9a393bc87ee4f`

## 1. Scope and method

This is the durable reconnaissance baseline for the future `P00NSMASHER/portfolio-brain` control repository.

The pass was intentionally architecture-focused rather than a blind reread of every source file:

1. enumerate every repository visible to the connected P00NSMASHER GitHub account;
2. pin the exact current `main` commit for every repository;
3. recursively inventory each pinned tree once;
4. inspect architecture-critical contracts, workflows, ledgers, learning code, governance boundaries, evidence systems, source-of-truth declarations, and representative project-local implementations;
5. inspect current-head GitHub Actions evidence where it materially changes the baseline;
6. search the main control/research repository for existing equivalents of the requested universal event system, model router, uncertainty engine, repository-delta adapters, and persistent scheduler;
7. classify existing components as **reuse**, **adapt**, **project-local**, **legacy**, or **missing**.

No product repository was modified during reconnaissance.\n\nDuring final verification, `trading-platform/main` advanced by one commit. Only that delta was inspected: the two CI workflows were pinned to Ubuntu 24.04 and pip 26.2.1 and the release-drift allowlist hashes were updated accordingly. No surveillance/research architecture changed, so no repeat tree scan was performed.

### Evidence standard for this baseline

- **Observed** means directly present in a pinned repository tree/file or current GitHub metadata/action result.
- **Verified current-head CI** means an Actions run at the exact pinned commit completed successfully.
- **Unknown** means the inspection did not establish the fact; absence of evidence is not converted into failure.
- Architectural recommendations below are design decisions for Portfolio Brain, not claims about already-deployed capability.

## 2. Repository inventory pinned for Step 0

| Repository | Pinned `main` commit | Primary observed role | Current-head execution evidence |
|---|---|---|---|
| `P00NSMASHER/github-value-hunt-ledger` | `1ea7fff759ff592734d15e4170a9a393bc87ee4f` | Hunter, Technology Intelligence, AI Business OS, RecoveryWorks/RecoveryOS, Freight, experiments, shared control research | Repository Release Gate and AI Business OS Canonical CI both passed at exact head |
| `P00NSMASHER/StarBlox` | `36f2084eac013853a612892c19646dedab97c204` | StarBlox product, learning systems, economy/art/runtime, Roblox/AI development factory | StarBlox CI passed at exact head |
| `P00NSMASHER/abvmschoolstarworld` | `a15c7c2214a065707123e9b8ab8ac51a42240345` | ABVM Grade 2 Parent Companion and teacher-page refresh | App QA, Pages deployment, and operational-health workflows passed at exact head |
| `P00NSMASHER/trading-platform` | `f9be7d5537d38bef24a5b0f99022c5d5885988d1` | Historical market-surveillance research only | No Actions run was present at the final exact head; the one-commit delta was inspected and only pins CI runner/pip inputs plus matching release-drift hashes |
| `P00NSMASHER/permitplate-nyc` | `7c9a8fc4dd9fa12275d336beb8eb10732718666a` | Permit intelligence, source observation, detection/opportunity ledgers | Deterministic regression, launch readiness, source health, and current graph have passing evidence; scheduled detection/scoring jobs currently fail at known steps |
| `P00NSMASHER/permitplate-state` | `c64fe06a22c3826c9ad3a7b85a4f911a6e589c19` | PermitPlate durable operational state | Repository contract says private; GitHub metadata currently reports **public** visibility — critical boundary mismatch |
| `P00NSMASHER/capturebrief` | `3b5867c422cbf9da08d02f1b9c6e7c8afa5b42ba` | CaptureBrief public-source pursuit QA, decision evidence, outcome/watch systems | Product Core passed at exact head; scheduled ABVM school-pack refreshes also pass |
| `P00NSMASHER/-character-studio-private` | `d3e541c89549904f310c0cdbd3f623808a0dfa35` | Auxiliary synthetic-adult character/image tool | No workflow was present in the exact tree; package scripts reference test/check paths absent from that tree |

The first seven repositories match the portfolio list supplied for reconnaissance. The private character-studio repository was additionally discovered and retained as an auxiliary project because it contains active model-provider integration and may later need cost/governance observation.

## 3. Existing portfolio-control substrate

### 3.1 AI Business OS — canonical reusable foundation

The strongest general control-plane implementation already exists under `github-value-hunt-ledger/ai_business_os/`.

The repository explicitly marks `ai_business_os/` as canonical and `business_os/` as frozen legacy reference. This resolves one otherwise dangerous duplicate-implementation ambiguity: new portfolio work must **not** revive `business_os/`.

Observed reusable capabilities in canonical AI Business OS:

- persistent worker identity, goals, heartbeats, stale-worker reclamation, snapshots, delegation lineage, and hash-chained events;
- independent Manager → Executor → Auditor completion contracts;
- verifier-gated self-improvement with disjoint development/held-out sets, independent verifier, canary evidence, and explicit curator promotion;
- value-weighted memory driven only by independently verified outcomes;
- provenance-preserving typed knowledge graph;
- runtime governance with action classes, allow/deny policy, exact approvals, rolling budgets, replay protection, and kill switches;
- governed autonomous software factory using isolated attempts, independent audit, branch/PR handoff, and separate production-merge authorization;
- evidence/truth engine with proof obligations, freshness, admissibility, independence, contradiction handling, and content-addressed truth receipts;
- reversible entity canonicalization;
- evidence-first capital allocation with component evidence exposed rather than hidden behind one opaque score;
- a narrow private runtime/CEO Command Center backed by private state and a named-operation gateway.

**Reuse decision:** Portfolio Brain should treat this package as the principal donor/reference implementation for Truth Engine, Value Memory, canonicalization, governance, persistent-worker contracts, software-factory gates, verification, and allocator semantics. Step 1 should not copy it wholesale into a monorepo. Later steps should port or wrap exact capabilities with provenance and tests.

### 3.2 Existing evidence semantics

The current Truth Engine already distinguishes higher-order claim verdicts and proof-obligation states:

- claim verdicts: `PROVEN`, `CONTESTED`, `NOT_PROVEN`, `UNKNOWN`;
- obligation states include `SATISFIED`, `MISSING`, `STALE`, `INADMISSIBLE`, `INSUFFICIENT_SUPPORT`, `INSUFFICIENT_INDEPENDENCE`, `CONFLICTED`, `CONTRADICTED`.

The new Portfolio Brain requires a lower-level universal evidence-state vocabulary:

`OBSERVED | VERIFIED | INFERRED | UNKNOWN | CONTRADICTED | STALE | INVALID`.

**Architecture decision:** do not replace the existing Truth Engine vocabulary. Step 3/5 should add a normalized evidence-state layer beneath/alongside native claim verdicts and preserve a reversible mapping to project-native semantics. Repeated assertions must never cause `INFERRED -> VERIFIED`.

### 3.3 Existing Value Memory

AI Business OS Value Memory already enforces several requirements that should remain invariant portfolio-wide:

- memory is content-addressed/versioned;
- observers cannot verify their own outcomes;
- unverified/rejected outcomes contribute zero learned value;
- duplicate event credit is blocked;
- credit is conserved across attributions;
- objective-specific learning cannot silently leak to unrelated objectives;
- global transfer is discounted;
- recent verified outcomes weigh more than stale outcomes;
- negative verified outcomes reduce retrieval priority;
- value-weighting is advisory and cannot bypass verification/governance.

This is already close to the required long-term portfolio memory model.

### 3.4 Existing Knowledge Graph

AI Business OS currently supports:

`REPO, DATA, CAPABILITY, TECHNOLOGY, PRODUCT, BUSINESS, CUSTOMER, EXPERIMENT, OUTCOME, MEMORY`

with relationships including:

`IMPLEMENTS, ENABLES, OWNS, SERVES, TESTED_BY, PRODUCED, ATTRIBUTED_TO, INFORMED_BY, DEPENDS_ON, COMBINES_WITH`.

Every consequential node/edge is evidence-bearing and historical relationship changes use supersession.

The requested Portfolio Brain ontology is materially larger. Missing or not first-class in the canonical graph are at least:

- `OWNER_OBJECTIVE`
- `MODEL`
- `AGENT`
- `SKILL`
- `SEARCH`
- `FINDING`
- `CHANGE`
- `BUG`
- `MARKET`
- `OPPORTUNITY`
- `REVENUE`
- `COST`
- `EVIDENCE`

and requested relations such as:

- `DISCOVERED_BY`
- `CREATED`
- `STRENGTHENS`
- `WEAKENS`
- `FAILED`
- `IMPROVED`
- `INVALIDATES`
- `REUSED_BY`
- `GENERATED_VALUE_FOR`
- `SUPERSEDES`
- `CONTRADICTS`

**Reuse decision:** extend the canonical semantics and provenance rules; do not create a disconnected second graph.

### 3.5 Existing software factory and self-improvement

The AI Business OS software factory already encodes the correct safety shape:

`QUEUED -> isolated RUNNING attempt -> independent VERIFYING -> READY_FOR_PR -> governed PR -> separately governed production merge`.

Important invariants already exist:

- implementation and audit identities are separated;
- every retry receives a fresh workspace/attempt branch;
- evidence binds repository, branch, commit, tests, artifacts, and audit;
- PR creation and production merge require different authorization;
- production merge remains human-controlled;
- governance kill switches remain authoritative.

The self-improvement contract separately requires:

`candidate -> frozen dev/held-out -> independent scoring -> zero hard regression -> canary -> GLOBAL_ELIGIBLE -> explicit curator promotion`.

This substantially matches the desired repair/self-upgrade path and should be generalized rather than reinvented.

### 3.6 Existing governance

Current AI Business OS action classes are:

- `READ`
- `INTERNAL_WRITE`
- `EXTERNAL_WRITE`
- `PRODUCTION_CHANGE`
- `MONEY_MOVEMENT`
- `DESTRUCTIVE`
- `POLICY_CHANGE`

The new portfolio autonomy classes are:

- `OBSERVE`
- `EXPERIMENT`
- `MODIFY`
- `ACT`

**Architecture decision:** Portfolio Brain should use autonomy class as the high-level capability envelope, then map each operation to the existing lower-level governance action class. Example: `MODIFY` may create an isolated branch (`INTERNAL_WRITE`) but cannot imply production merge (`PRODUCTION_CHANGE`).

A known production-hardening gap remains in the existing governance contract: `HUMAN` identity is currently a trusted caller assertion at the module boundary and must be bound to an authenticated identity/session before consequential production use.

## 4. Hunter / Technology Intelligence baseline

Hunter is already much more than a repository list.

### 4.1 Existing autonomous execution

`.github/workflows/public-repo-hunter.yml` is self-triggering through GitHub schedules. It routes 14 Hunter workers plus an Integrator in staggered cycles, runs deterministic scout tests, performs public-repository scouting, updates durable queue/digest state, and serializes its writer.

This proves an important end-state requirement is already feasible: ordinary Hunter work can run without opening ChatGPT.

### 4.2 Existing empirical learning

The Technology Intelligence layer already records and learns from:

- exact search runs;
- query families;
- broader search objectives;
- strategies;
- materially different search moves;
- candidate/deep-inspection/retention denominators;
- candidate rejection/negative knowledge;
- duplicate-inspection avoidance;
- capability creation;
- experiment changes;
- downstream outcomes;
- realized revenue/customer value when actually observed;
- observed engineering compression where measured.

The canonical loop is already:

`SEARCH STRATEGY -> SEARCH RUN -> REPOSITORY/DATA -> CAPABILITY -> OPPORTUNITY -> EXPERIMENT -> OUTCOME -> STRATEGY METRICS -> SEARCH ALLOCATION`.

Learning is intentionally conservative: unknown denominators remain unknown, retrospective records do not train the same way as prospective runs, and minimum sample gates precede strategy claims.

### 4.3 Existing repair learning

Hunter already has a deterministic repair pipeline:

- learning-failure capture;
- `NEEDS_REPRODUCTION` versus `READY_FOR_REPAIR`;
- exact regression-test requirement;
- content-addressed candidate diff;
- separate mutate-development and promotion-test evidence;
- held-out/adversarial/adjacent-domain gates;
- canary;
- separate global review.

Automatic global promotion remains disabled.

### 4.4 Hunter gap relative to Portfolio Brain

What is missing is not “Hunter exists.” The missing layer is **portfolio-driven objective generation and outcome closure**.

Today Hunter has its own queues, priorities, experiments, and adaptation. Portfolio Brain still needs to supply:

- capability gaps from every registered project;
- current project bottlenecks;
- highest-value uncertainties;
- portfolio resource constraints;
- outcome/value feedback from non-Hunter projects;
- a universal event envelope;
- a shared negative-knowledge interface;
- a durable causal link from discovery -> reuse/experiment -> measured downstream outcome.

## 5. RecoveryWorks / RecoveryOS / Freight baseline

`github-value-hunt-ledger/recoveryworks/` is a mature domain architecture, not a speculative concept.

RecoveryOS already separates:

1. branch-specific ingestion;
2. effective-dated authority;
3. deterministic money calculation;
4. evidence;
5. recovery ledger;
6. human authorization;
7. externally evidenced outcomes.

The universal domain model is:

`Client -> Counterparty -> Transaction -> Governing Rule -> Expected Amount -> Actual Amount -> Variance -> Evidence -> Recovery Case -> Outcome`.

All 18 registered recovery divisions have operational Scan 360 ingestion paths in the inspected portfolio status:

- Freight
- Payer
- Utility
- AP
- Duty
- SaaS
- Telecom
- Rebate
- Lease
- Construction
- Tax
- Insurance
- Cloud
- Merchant Fee
- Parcel
- Procurement
- Warranty/Credit
- Payroll/Benefit Billing

For seven-figure findings, RecoveryOS already requires a strong hostile-examination package including point-in-time authority, source authentication, reproducible calculation manifest, dual review, independent adverse-evidence challenge, deadline assessment, frozen proof bundle, client authorization, exact outbound artifact identity, and final proof sealing.

**Portfolio reuse decision:** RecoveryOS evidence/custody patterns are valuable evidence primitives, but its financial-domain state machine remains project-local. Portfolio Brain should ingest its verified events/outcomes rather than absorb its business logic.

Freight also contains its own Hunter bridge, outcome adapter, audit/settlement workflows, evidence manifests, readiness gates, and commercial-learning artifacts. This confirms that cross-system bridges already exist in ad hoc form; the goal is to replace ad hoc integration with a universal event/adapter contract.

## 6. Product and research systems

### 6.1 StarBlox

Observed architecture includes:

- deterministic source-grounded learning content;
- adaptive Quest logic;
- explicit mastery/reward protections;
- durable player-state mechanisms;
- immutable/versioned question and bundle contracts;
- implementation provenance;
- replay/determinism contracts;
- offline question factory and QA;
- a provider-neutral Roblox/Studio AI development factory with planner/coder/reviewer roles, bounded mutation, testing, rollback, logs, playtests, input simulation, and visual review;
- project CI passing at current GitHub head.

Important source-of-truth nuance: StarBlox documentation says the Replit application is the canonical runtime and GitHub `main` is a portable mirror. The inspected release-status document itself references an older GitHub head than current `main`, so Portfolio Brain must not equate “latest GitHub commit” with “verified deployed runtime.”

**Adapter requirement:** StarBlox needs explicit source-of-truth fields for code mirror, runtime authority, deployed revision, content revision, and rendered-runtime evidence.

**Safety boundary:** child-facing changes remain consequential. Portfolio Brain may observe, test, and prepare isolated candidates but must not autonomously promote consequential child-facing experiments.

### 6.2 ABVM Grade 2 Parent Companion

The ABVM repository already has an autonomous source-refresh pipeline:

- scheduled teacher-page fetches;
- retry and Google-sign-in detection;
- expected-heading validation;
- fail-closed content sufficiency checks;
- last-good state preservation;
- change-only commits;
- QA;
- Pages deployment;
- post-deploy freshness verification;
- separate scheduled health monitor.

This is a strong example of deterministic observation before AI.

**Portfolio reuse decision:** preserve the project-local extractor and convert validated refresh/change/failure results into universal portfolio events rather than moving school parsing into Portfolio Brain.

### 6.3 Trading research

The trading repository explicitly defines itself as historical market-surveillance research, not a trading system.

It already contains strong research controls:

- point-in-time data rules;
- matched controls;
- temporal holdout isolation;
- blind external validation;
- immutable case evidence;
- historical/live-forensics graph separation;
- fail-closed evaluation-release controller;
- champion immutability;
- research-only output policy.

The evaluation controller authorizes only bounded **offline historical surveillance evaluation** and does not auto-promote or execute trades.

**Hard portfolio boundary:** Portfolio Brain may ingest lawful data, schedule offline research, detect drift, create research branches, and generate reports. It must never translate research output into brokerage/trade authority.

### 6.4 PermitPlate NYC

PermitPlate already has:

- source registry with authority and freshness windows;
- current evidence graph;
- SHA-256-bound detection ledger;
- monotonic observation rules;
- material-change/review receipts;
- opportunity ledger with append/idempotency/conflict checks;
- source-health, graph, detection, scoring, launch, and delivery workflows;
- explicit separation between operational readiness and commercial proof.

Current operational evidence is mixed:

- source-health schedule: passing;
- current-graph schedule: passing;
- deterministic regression: passing;
- launch readiness push check: passing;
- scheduled detection-ledger: repeatedly failing at **Build scored opportunity packages for customer-eligible detections**;
- scheduled scoring-readiness: repeatedly failing at **Run no-send scoring promotion canary**.

Job logs were not available through the connected GitHub surface, so the exact root cause remains **UNKNOWN** and must not be guessed.

A separate critical boundary issue is described in Section 9.

### 6.5 CaptureBrief

CaptureBrief has strong evidence infrastructure:

- exact public-source and version identity;
- exact passage/locator evidence;
- rule edition and applicability separation;
- human review;
- append-preserving decision history;
- source/rule change watch;
- targeted reopening only for dependent assumptions;
- commercial outcome ledger;
- fail-closed buyer bundle construction and independent verification;
- explicit “external send not authorized” boundary;
- product regression suite and cross-platform lifecycle tests.

Its own product documentation correctly identifies the next evidence need as real buyer/public-pursuit outcome evidence rather than another round of feature construction.

**Portfolio reuse decision:** the source/version/watch and outcome-ledger patterns are strong project-local donors for the universal evidence/event design.

### 6.6 Auxiliary character studio

The discovered private character-studio repository contains a direct model-provider integration and a synthetic-adult eligibility registry.

Architecture observations:

- provider call is server-side;
- API key is environment-bound;
- rate limiting exists;
- responses are no-store;
- character registry requires fictional/synthetic adult 21+;
- there is no workflow in the exact repository tree;
- `package.json` references `scripts/static-check.mjs` and `tests/*.test.mjs`, but those paths were not present in the exact tree.

This repository should be registered as an auxiliary product/tool in Step 2 if still active, but it is not a foundation component.

## 7. Autonomous trigger map

| System | Trigger today | Durable autonomous behavior | Portfolio gap |
|---|---|---|---|
| AI Business OS CI | push / pull request | canonical regression verification | no portfolio observation schedule |
| Technology Intelligence | push / pull request | rebuilds intelligence and can persist generated state | reacts to TI changes, not all projects |
| Public Repo Hunter | scheduled + manual | autonomous scouts + integrator, writes queue/digest | not yet driven by universal portfolio gaps/uncertainties |
| ABVM | scheduled + push/manual | source refresh, validation, commit, deploy, health verification | events are not normalized into shared portfolio bus |
| PermitPlate | scheduled + push/manual | source observation, graph, detection/scoring/readiness | two scheduled execution paths currently failing |
| CaptureBrief | push / PR + scheduled ABVM helper | robust product CI; ABVM pack refresh into Pages branch | contains cross-project ABVM coupling |
| StarBlox | CI push/PR behavior | deterministic project validation | no universal portfolio event adapter; runtime truth also lives in Replit |
| Trading research | PR CI + manual synthetic CI | bounded offline validation | no scheduled portfolio-controlled research loop |
| Character studio | none observed | server runtime only | no CI/health/cost telemetry in inspected tree |

There is **no single universal observation runtime** that consumes all of these signals and advances one durable shared state.

## 8. Duplicate and overlapping implementations

### 8.1 Resolved duplicate: Business OS packages

- `business_os/` = frozen legacy reference.
- `ai_business_os/` = canonical active implementation.

Action: never fork the legacy package into Portfolio Brain. Preserve only provenance/compatibility references.

### 8.2 Multiple evidence/ledger implementations

Evidence and durable-state primitives exist independently in:

- AI Business OS Truth Engine / Value Memory / graph;
- RecoveryOS journals and proof bundles;
- Freight evidence/review/outcome systems;
- PermitPlate detection/opportunity ledgers;
- CaptureBrief decision evidence/outcome/watch;
- trading research case/graph/release evidence;
- StarBlox content/replay/implementation provenance.

These are not all “duplicates” to collapse. They encode valuable domain constraints.

Action: normalize through adapters into a universal event/evidence envelope while retaining project-native records as authoritative source evidence.

### 8.3 Two software-factory layers

- AI Business OS has a generic governed software-factory lifecycle.
- StarBlox has a domain-specific Roblox/Studio development factory.

Action: later Portfolio Brain software factory should orchestrate the StarBlox factory as a project adapter rather than replacing its Studio-specific safety/rollback logic.

### 8.4 ABVM source-refresh duplication/coupling

- `abvmschoolstarworld` directly validates teacher pages and publishes its own study pack.
- `capturebrief` also has a scheduled `Refresh ABVM school pack` workflow, fetching an AppDeploy bridge every four hours and writing an ABVM pack into its `gh-pages` branch.

Action: preserve current behavior during Step 0. Later replace this hidden cross-project coupling with one authoritative school-source event/pack contract and explicit consumer subscriptions.

## 9. Critical governance and operational findings

### P0 — PermitPlate state visibility contradicts its own security contract

`P00NSMASHER/permitplate-state` README states that the repository stores private durable operational ledgers and must remain private.

Current GitHub repository metadata, rechecked during Step 0, reports:

`visibility: public`.

This is a direct boundary contradiction. Step 0 intentionally did **not** change repository visibility because the instruction forbids product-repository modification.

**Required handling:** treat the repository as non-private until GitHub metadata proves otherwise. Do not allow Portfolio Brain to ingest sensitive/customer state from it while this mismatch exists.

### P1 — PermitPlate scheduled detection/scoring paths are degraded

The exact current source head has green source-health/current-graph/regression/readiness evidence, but the two recurring downstream jobs described above are failing. The failure points are known; root causes are not.

Portfolio Brain must model this as partial operational health, not “PermitPlate is healthy” or “PermitPlate is broken.”

### P1 — No authenticated human principal binding proven at the generic governance module boundary

The AI Business OS governance contract itself states that production must bind the `HUMAN` principal to an authenticated identity/session. Until that exists, Portfolio Brain must not treat a caller-provided human label as sufficient authorization for consequential external actions.

### P1 — Project source-of-truth can differ from GitHub

StarBlox currently declares Replit runtime authority while GitHub is a portable mirror. A repository adapter that watches only GitHub can therefore observe source changes without proving deployment/runtime parity.

### P2 — Auxiliary character studio lacks inspected CI integrity

No workflow exists in the exact tree and referenced test/check paths are absent. Registering it is safe; treating it as verified production infrastructure is not.

## 10. Missing portfolio-level infrastructure

The reconnaissance did **not** find a complete implementation of the following cross-portfolio components:

1. dedicated `portfolio-brain` repository/control plane;
2. universal project/objective/metric/autonomy registry;
3. universal event bus/event schema shared by all projects;
4. universal evidence-state normalization across project-native truth models;
5. read-only repository adapters with exact-commit delta caching;
6. one portfolio graph containing the full requested ontology;
7. continuous all-project observation runtime;
8. portfolio-driven autonomous Hunter objective generation;
9. generalized learning across engineering, product, customer, research, and cost outcomes;
10. highest-value-uncertainty / decision-value engine;
11. universal experiment specification/execution engine;
12. model-provider abstraction/router with deterministic/cheap/strong/adversarial tiers;
13. unified model-call cost/token/outcome telemetry;
14. persistent portfolio roles operating across projects;
15. allocator spanning every registered project and scarce resource class;
16. cross-repository software-factory orchestrator;
17. generalized repair/self-improvement orchestration across projects;
18. measurable cross-project capability-transfer evaluator;
19. general persistent portfolio work scheduler/queue;
20. unified AI/API/GitHub compute cost governor;
21. executive portfolio dashboard;
22. general 24/7 worker runtime/job queue beyond the existing narrow CEO runtime and GitHub schedules.

These gaps align closely with Steps 1–22 of the requested implementation plan; the plan should therefore reuse current substrate rather than expand scope.

## 11. Architecture decisions frozen by Step 0

### D0-01 — Dedicated control repository, no monorepo

Step 1 will create `P00NSMASHER/portfolio-brain`.

Project code stays in its own repository. Portfolio Brain stores registry, normalized events, adapters, graph/memory/learning/control logic, receipts, and portfolio reports.

### D0-02 — Event-first integration

Projects communicate through immutable normalized events plus evidence receipts. Portfolio Brain must preserve a pointer/hash to the native project record and never silently rewrite native history.

### D0-03 — Delta observation by exact source revision

Repository adapter state will record at least:

- repository identity;
- authoritative branch/source;
- last inspected commit;
- relevant artifact fingerprints;
- last successful observation;
- adapter version.

An unchanged source is not rescanned unless there is a different evidence question or contradiction.

### D0-04 — Deterministic before model

Hashes, schema validation, state transitions, freshness, budgets, deduplication, arithmetic, graph constraints, and routine aggregation remain deterministic.

Models are introduced only where semantic extraction/reasoning creates measurable value.

### D0-05 — Existing AI Business OS is a donor, not a second live control plane

Portfolio Brain will reuse/port/wrap canonical `ai_business_os` semantics with exact provenance. It will not activate a second competing set of portfolio policies inside `github-value-hunt-ledger`.

### D0-06 — Preserve project-native semantics

Universal normalization is additive. RecoveryOS, CaptureBrief, PermitPlate, trading research, StarBlox, and ABVM retain their own stricter domain rules.

### D0-07 — Read-only downstream boundary through Step 15

Steps 1–15 may observe, normalize, learn, plan, and run bounded local/synthetic experiments as specified, but no generic Portfolio Brain component receives uncontrolled downstream write authority.

Step 16 may create isolated branches/PR candidates under governance. Production/main promotion remains separately gated.

### D0-08 — Model independence

Interactive ChatGPT is not a runtime dependency. Future autonomous reasoning uses a provider abstraction capable of model APIs, local/self-hosted models, or deterministic no-model execution.

### D0-09 — Separate autonomy envelope from action class

High-level `OBSERVE / EXPERIMENT / MODIFY / ACT` permissions are mapped to lower-level governance action classes. `ACT` never becomes implicit from successful reasoning.

### D0-10 — Consequential authority remains human-bound

Production deployment with meaningful risk, customer communication, claims/disputes, legal/regulatory communication, payments/purchases/billing, money movement, destructive deletion, private-data exposure, consequential child-facing experiments, live trading, brokerage orders, and autonomous investment positions remain explicit-approval boundaries.

## 12. Proposed Portfolio Brain integration map

`OWNER_OBJECTIVE`
-> project registry
-> read-only adapters
-> normalized events/evidence
-> Truth Engine
-> universal graph + Value Memory
-> learning + uncertainty engine
-> experiment engine
-> Hunter/search
-> allocator/scheduler
-> bounded agents/software factory
-> independent verification
-> branch/PR/canary
-> real outcome event
-> memory/policy update

Project-local systems remain peers feeding this loop, not subdirectories copied into it.

## 13. Step 0 inspected architecture anchors

### github-value-hunt-ledger

- `ai_business_os/README.md`
- `ai_business_os/TRUTH_ENGINE_CONTRACT.md`
- `ai_business_os/VALUE_MEMORY_CONTRACT.md`
- `ai_business_os/KNOWLEDGE_GRAPH_CONTRACT.md`
- `ai_business_os/CAPITAL_ALLOCATOR_CONTRACT.md`
- `ai_business_os/SOFTWARE_FACTORY_CONTRACT.md`
- `ai_business_os/SELF_IMPROVEMENT_CONTRACT.md`
- `ai_business_os/GOVERNANCE_CONTRACT.md`
- `ai_business_os/RUNTIME_DEPLOYMENT_CONTRACT.md`
- `ai_business_os/persistent_agents/WORKER_CONTRACT.md`
- `business_os/README.md`
- `business_os/ARCHIVED_SOURCE_MANIFEST.json`
- `production/LEARNING_ENGINE.md`
- `intelligence/README.md`
- `recoveryworks/ARCHITECTURE.md`
- `recoveryworks/PORTFOLIO.md`
- `recoveryworks/README.md`
- `recoveryworks/HOSTILE_EXAMINATION_STANDARD.md`
- canonical Hunter/Technology Intelligence workflows and selected learning/repair search hits.

### StarBlox

- `README.md`
- `RELEASE_STATUS.md`
- `docs/ARCHITECTURE_CONTRACTS.md`
- `docs/AI_DEVELOPMENT_FACTORY.md`
- `docs/OFFLINE_QUESTION_FACTORY.md`
- `.github/workflows/ci.yml`
- exact-tree architecture inventory.

### ABVM

- `README.md`
- `scripts/refresh-teacher-pages.mjs`
- `.github/workflows/sync-study-pack.yml`
- `.github/workflows/refresh-health.yml`
- exact-tree architecture inventory.

### Trading research

- `README.md`
- `docs/evaluation_release_controller.md`
- `docs/cross_event_intelligence_graph.md`
- `.github/workflows/pr-ci.yml`
- `.github/workflows/synthetic-ci.yml`
- exact-tree architecture inventory.

### PermitPlate

- `README.md`
- `operations/source-registry.js`
- `pipeline/detection-ledger.js`
- `pipeline/opportunity-ledger.js`
- source-health/current-graph workflows;
- current scheduled job-step evidence;
- separate state-repository contract and GitHub visibility metadata.

### CaptureBrief

- `PRODUCT-CORE.md`
- `DECISION-EVIDENCE.md`
- `OUTCOME-LEDGER.md`
- `SOURCE-POLICY.md`
- `.github/workflows/product-core.yml`
- `.github/workflows/abvm-school-pack.yml`
- exact-tree architecture inventory.

### Auxiliary character studio

- `package.json`
- `lib/registry.js`
- `app/api/generate/route.js`
- `lib/prompt.js`
- exact-tree inventory.

## 14. Rescan policy

On future `CONTINUE` turns:

1. read `PORTFOLIO_BUILD_STATE.json` first;
2. compare each registered source's current authoritative revision with the stored `inspected_commit`;
3. do not reread unchanged trees/files unless a new step requires a specific contract not captured in this baseline;
4. if a repository changed, inspect the delta rather than repeat the full reconnaissance;
5. append new architectural decisions with provenance rather than silently revising historical conclusions.

## 15. Exact next step

**STEP 1 — Portfolio Brain foundation**

Create `P00NSMASHER/portfolio-brain` and only its foundation:

- architecture contract;
- authority/boundary contract;
- requested directory skeleton;
- project-registration mechanism;
- initial CI;
- import/copy the Step 0 baseline and durable build state with provenance;
- no autonomous writes to downstream projects.

Do not begin Step 2 during the same response cycle.
