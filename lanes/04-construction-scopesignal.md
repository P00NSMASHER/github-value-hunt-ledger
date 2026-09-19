# Construction / ScopeSignal

## Hunter instructions
Before searching, read this file plus ../MASTER.md, ../REJECTED.md, and ../COMBINATIONS.md.

Search public GitHub repositories for unusually valuable functioning software, data pipelines, algorithms, workflows, datasets, integrations, or product infrastructure relevant to this lane. Include obscure, abandoned, low-star, and no-license repositories in discovery. Respect license/copyright for reuse.

Do not collect, reproduce, preserve, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Skip/quarantine those items and continue searching for legitimate technical or commercial value.

## Finding template
### Repository name
- Repository:
- Commit / revision:
- Date discovered:
- What it contains:
- Why it matters:
- Commercial possibilities:
- Build-time savings:
- Evidence inspected:
- License / rights:
- Reuse classification:
- Scores:
  - Technical value:
  - Commercial value:
  - Rarity:
  - Completeness:
  - Build-time saved:
  - Data advantage:
  - High-ticket potential:
- Next action:

## Findings
### Fajendagba/Construction-Change-Order-Engine
- Repository: https://github.com/Fajendagba/Construction-Change-Order-Engine
- Commit / revision: 60f5ab99bfb97647039e6cec280c246a10f8a856
- Date discovered: 2026-09-19
- What it contains: Laravel/PostgreSQL construction change-order API organized around domain-driven design, explicit change-order state transitions, project budget line items, audit metadata, events, queues, realtime updates, and strict static-analysis/testing conventions.
- Why it matters: The source includes concrete construction-specific workflow logic instead of generic CRUD. ChangeOrderService implements creation and state transitions; BudgetRecalculationService applies approved changes to cost-code and project totals.
- Commercial possibilities: Architecture reference for ScopeSignal/change-order detection: detected scope changes can flow into a defensible proposed-change state machine, review process, cost-code impact, audit trail, and budget update.
- Build-time savings: High as a clean-room architecture reference for domain states, approval flow, events, and budget propagation.
- Evidence inspected: README.md; app/Domain/ChangeOrder/Services/ChangeOrderService.php; app/Domain/ProjectBudget/Services/BudgetRecalculationService.php.
- License / rights: No repository license detected.
- Reuse classification: Inspect / learn / clean-room implementation only unless permission is established.
- Scores:
  - Technical value: High
  - Commercial value: High as ScopeSignal reference architecture
  - Rarity: Medium-High
  - Completeness: Medium-High
  - Build-time saved: High for architecture/design
  - Data advantage: Low
  - High-ticket potential: High if paired with document/change detection
- Next action: Clean-room the state model and budget-impact concepts, then search for permissively licensed RFI/submittal/document-diff components that supply the upstream detection signal.

### cneuralnetwork/ScopeSignal
- Repository: https://github.com/cneuralnetwork/ScopeSignal
- Commit / revision: d470659a009e9944fd6c4a7969a903dfc28c443e
- Date discovered: 2026-09-19
- What it contains: A functioning Next.js/TypeScript evidence-first scope-creep application with structured contract/conversation analysis, exact-quote evidence grounding, out-of-scope/review/in-scope classifications, estimated-hours/value calculations, change-order drafting, document extraction endpoints, PDF-related dependencies, local project data, Vitest tests, a grounding evaluation, and a Playwright demo-flow test. The analysis endpoint produces schema-constrained model output and then deterministically verifies that any cited contract quote actually exists in the contract; an ungrounded out-of-scope result is downgraded to human review with capped confidence.
- Why it matters: This is unusually close to the core ScopeSignal product thesis and is not a README-only prototype. Its strongest reusable pattern is the evidence gate: model-generated commercial conclusions cannot remain out-of-scope unless backed by a verbatim contract quote that survives deterministic verification. That pattern is directly useful for defensible construction change detection where unsupported AI conclusions would create commercial and legal risk.
- Commercial possibilities: Reuse the application shell and evidence-grounding architecture for a construction-specific ScopeSignal product: baseline prime contract/subcontract scope, ingest RFIs/submittals/emails/drawing revisions, identify candidate scope changes, require source evidence, route uncertain items to PM review, estimate time/cost impact, and draft a proposed change order with an auditable evidence package.
- Build-time savings: Estimated 6-10 weeks for product shell, schemas, evidence gating, analysis/drafting API structure, PDF/output plumbing, and test harness before construction-specific extensions.
- Evidence inspected: Repository metadata and MIT license; commit history; root tree; package.json build/lint/typecheck/Vitest/Playwright scripts; src/lib/domain.ts schemas, exact-quote grounding policy, recovery-value calculation, and conversation parser; src/app/api/analyze/route.ts structured analysis prompt and deterministic grounding pass; API directory containing analyze/document-extract/draft/health; tests/domain.test.ts; tests/evals/grounding.eval.test.ts; tests/e2e/demo-flow.spec.ts.
- License / rights: MIT repository license verified. External model/service dependencies and their terms still need ordinary production review, but the repository code itself is permissively licensed.
- Reuse classification: Directly reusable under MIT terms.
- Scores:
  - Technical value: 8/10
  - Commercial value: 9/10
  - Rarity: 8/10
  - Completeness: 8/10
  - Build-time saved: 8/10
  - Data advantage: 5/10
  - High-ticket potential: 9/10
- Next action: Replace the creative-services domain with construction entities and evidence types, especially contract scope items, RFIs, submittals, drawing/spec revisions, cost codes, schedule impact, and proposed-change states; keep the exact-quote grounding gate intact.

### aec-platform/qto
- Repository: https://github.com/aec-platform/qto
- Commit / revision: 82c1001658b2310c576c7fc39d721695e4382f2f
- Date discovered: 2026-09-19
- What it contains: A functioning Python IFC quantity-takeoff engine with a CLI, reports, fixtures/golden files, and substantive tests for extraction, mappings, rules, reporting, and CLI behavior. The extractor walks real IFC relationships, normalizes quantities to SI units, inherits type and instance properties, resolves site/building/storey placement, materials and classifications, tracks assemblies/parts, and explicitly suppresses double counting when parent and child elements both appear in an IFC model. Classification/cost-code mapping is pluggable rather than hard-wired into extraction.
- Why it matters: ScopeSignal becomes materially more valuable when a detected scope change can be translated into measurable physical quantity deltas instead of only text evidence. This engine supplies a reusable path from IFC models to normalized element/quantity records that can be diffed across model revisions and attached to change-order evidence.
- Commercial possibilities: Build an IFC revision-impact module: run the old and new model through QTO, match stable GlobalIds/elements, calculate added/removed/changed quantities by cost code/material/storey, and feed those deltas into ScopeSignal so a PM can see both the documentary trigger and the measurable scope impact. A secondary product is standalone model-revision quantity delta reporting for estimators, subcontractors, and change-management teams.
- Build-time savings: Estimated 1-3 months versus building IFC relationship traversal, quantity extraction, unit normalization, assembly suppression, mapping, report structure, and regression tests from scratch.
- Evidence inspected: Repository metadata showing 1 star/0 forks and MIT license; exact latest commit; root LICENSE/pyproject/qto/tests/tools structure; tests/test_cli.py, test_extract.py, test_mappings.py, test_report.py, test_rules.py plus fixtures/golden data; qto/extract.py implementation of Element/Quantity models, IFC relationship indexes, SI normalization, spatial/material/classification resolution, and anti-double-counting logic.
- License / rights: Repository code is MIT with LICENSE present. Before redistribution, independently review the rights of the ifc-spf dependency and any contributed classification mapping data/standards; names or mapping structures tied to third-party construction classification standards may have separate terms even though this repository's code is MIT.
- Reuse classification: Directly reusable under MIT terms for repository code, subject to dependency/mapping-data rights review.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 8/10
  - Completeness: 8/10
  - Build-time saved: 8/10
  - Data advantage: 7/10
  - High-ticket potential: 9/10
- Next action: Prototype a two-version IFC delta using GlobalId plus quantity names, then connect changed quantities to contract scope/cost codes and the ScopeSignal evidence ledger; audit ifc-spf and mapping-data rights before shipping.

### Mirdula18/CADMorph
- Repository: https://github.com/Mirdula18/CADMorph
- Commit / revision: 0444d4f0b9fc72b216f146763ee00f5b822ef0a9
- Date discovered: 2026-09-19
- What it contains: A substantial Python/backend-plus-frontend CAD/PDF change-detection system rather than a demo-only README. The backend includes drawing-entity models, graph construction from spatial adjacency, a PyTorch Siamese encoder and matching/training code, cascade/IoU matching, explicit added/removed/modified delta models, deterministic controls, PDF markup generation, API/pipeline code, and a synthetic drawing-pair generator. Its test tree includes unit, determinism, ground-truth, and integration suites; integration tests cover input rejection, job logging, markup traceability, performance, report-PDF generation, and self-contained execution.
- Why it matters: Drawing revisions are a high-value source of hidden construction scope creep. The architecture shows a concrete path for entity-level comparison of drawing versions, grounded markup, and traceable deltas rather than relying only on pixel-level image difference. Coupled with contract scope and quantity/cost evidence, this could detect changes that otherwise become uncompensated work.
- Commercial possibilities: Clean-room a drawing-revision intelligence module for ScopeSignal: compare revision A/B, identify and mark added/removed/modified drawing entities, attach each candidate delta to sheet/location/source evidence, then map high-confidence changes into quantity/cost/schedule review and proposed-change workflow. Likely buyers include specialty subcontractors, GCs, estimators, and claims/change-management teams with meaningful change-order exposure.
- Build-time savings: The code itself is not reusable because no license was found, but the inspected architecture can save an estimated 2-4 months of product/design exploration by identifying useful pipeline stages, matching strategies, traceability requirements, synthetic-test generation, and benchmark categories for an independent implementation.
- Evidence inspected: Repository metadata showing 0 stars/0 forks and no detected license; exact latest commit; root tree with backend/frontend/specs/tools and no LICENSE; backend src/models/tests structure; source search confirming graph/build.py, match/model.py Siamese encoder, match/train.py, match/cascade.py, deltas/models.py, report/markup.py, pipeline.py, determinism.py and synthetic generation modules; integration test inventory including markup traceability, performance, report-PDF, and self-contained tests.
- License / rights: No repository license detected at the inspected revision. Source code and repo-owned creative content are therefore not recommended for copying, redistribution, incorporation, or relicensing without permission. Only ideas, interfaces, observed workflows, and independently reimplemented methods should be used.
- Reuse classification: Inspect / learn / clean-room implementation only unless permission is established.
- Scores:
  - Technical value: 9/10
  - Commercial value: 10/10
  - Rarity: 9/10
  - Completeness: 8/10
  - Build-time saved: 7/10
  - Data advantage: 8/10
  - High-ticket potential: 10/10
- Next action: Write a clean-room drawing-diff specification and benchmark using lawfully obtained sample revisions; preserve only high-level behavioral requirements, not source code. The strongest product combination is CADMorph-style drawing deltas -> qto quantity deltas -> evidence-grounded ScopeSignal review -> change-order state/budget workflow.

### wllmtrng/p6flow
- Repository: https://github.com/wllmtrng/p6flow
- Commit / revision: 637c12ec610aefda957b3964f993804176d2c9bd
- Date discovered: 2026-09-19
- What it contains: A functioning Python/DuckDB Primavera P6 XER ingestion and normalization library that emits typed, Snowflake-loadable Parquet tables plus a manifest. The code includes a streaming/tokenizer layer, typed DDL generation, schema inference and validation, calendar/UDF logic, topological loading by foreign-key dependencies, per-table output, CLI/batch scripts, schema-drift tooling, a synthetic XER fixture, and substantial tests. Its robustness suite locks in fixes for real-world exporter quirks such as encoding/BOM problems, empty table blocks, reserved/duplicate column names, trailing cells, literal nulls, and byte-faithful row provenance. Optional warehouse columns preserve source XER name, SHA-256, publish/export timestamps, and the original `%R` record text for auditability.
- Why it matters: ScopeSignal currently has strong contract, drawing and quantity evidence, but schedule impact is still a major missing commercial dimension. P6 XER is a common handoff format for construction schedules; this gives a ready-made schedule-data spine that can normalize baseline and update exports into queryable tables with source provenance. The most valuable downstream use is not merely schedule viewing but evidence-backed revision comparison: detect changes in activities, relationships, WBS, calendars, float and dates, then tie those schedule deltas to RFIs, drawing changes, daily records and proposed change orders.
- Commercial possibilities: Add a schedule-impact module to ScopeSignal. Ingest baseline/current XER exports, version every normalized table, diff TASK/TASKPRED/PROJWBS/CALENDAR and related records, surface materially changed activities/logic, and attach them to the same evidence ledger used for contract/drawing/quantity scope changes. A higher-ticket claims product can build human-reviewed time-impact/EOT evidence packages from those dated schedule states rather than trying to make unsupported legal conclusions automatically.
- Build-time savings: Estimated 1-2 months for robust XER parsing, typed normalization, provenance and warehouse output; potentially 2-4 months when the avoided edge-case/regression work is included.
- Evidence inspected: Repository metadata showing 0 stars/1 fork and LGPL-3.0; exact latest commit and tree; README architecture; src/p6flow/loader.py typed DuckDB loader and dependency ordering; src/p6flow/tokenizer.py/schema.py/output.py/calendar.py/UDF modules in the source tree; tests/test_robustness.py, test_calendar.py, test_inference.py, test_load.py, test_udf.py and test_validate.py; CI/publish workflow and synthetic fixture. The robustness tests explicitly preserve source SHA-256 and raw XER rows and cover multiple real-world parser failures.
- License / rights: GNU LGPL-3.0 verified in the repository. Reuse is conditional rather than permissive: comply with LGPL requirements, especially for modified library code and conveyed combined works. The generated schema is described as being code-generated from an Oracle EPPM database schema, so the rights/provenance of generated schema metadata should be reviewed separately before redistributing that artifact commercially.
- Reuse classification: Copyleft / conditional reuse under LGPL-3.0; safe architecture/data-interface inspiration for a clean-room implementation if a permissive-only stack is preferred.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 8/10
  - Build-time saved: 8/10
  - Data advantage: 7/10
  - High-ticket potential: 10/10
- Next action: Benchmark two lawfully obtained XER revisions from the same project and prove a traceable schedule-delta report. Do not call it delay causation or entitlement automatically; attach changed activities/logic to the existing ScopeSignal evidence graph for human review.

### EffortEdutech/contract-diary-platform
- Repository: https://github.com/EffortEdutech/contract-diary-platform
- Commit / revision: 6d3a9ad292e702100d133095bb03362ab38638dc
- Date discovered: 2026-09-19
- What it contains: A substantial MIT-licensed React/Supabase construction contract administration application with 0 stars/0 forks. The source tree contains BOQ import/edit/reporting, programme versions and CSV import, daily work diaries, offline diary/photo capture and sync, weather observations, delay-event suggestions for EOT review, document/version registers, contract authority/locking, member/RBAC flows, progress-claim CRUD/workflow, claim items linked to BOQ items, cumulative quantity/retention calculations, paid/approved/rejected states, and PDF/report builders. The database/schema history contains explicit delay-event, diary-to-BOQ, programme, BOQ, claim and document relationships. The code is much larger than a README/demo, although automated test coverage appears light relative to its surface area.
- Why it matters: This fills the field-evidence gap in the current ScopeSignal stack. Drawing/model deltas and contract analysis become more defensible when connected to contemporaneous site records: diary entries, photos, weather/work stoppage observations, BOQ quantities, programme activities, claim history and document versions. Its claim service also demonstrates a working BOQ-linked cumulative progress-claim workflow rather than generic invoice CRUD.
- Commercial possibilities: Reuse selected MIT components and data-model ideas to build a 'site evidence -> change/claim' layer for ScopeSignal: mobile/offline daily records, photos and weather observations link to schedule/BOQ items; material stoppages create review candidates; ScopeSignal then combines that record with contract clauses, drawing/IFC deltas and P6 schedule changes to draft a human-reviewed change/EOT evidence packet. This is particularly valuable for subcontractors and GCs that lose entitlement because field evidence is fragmented.
- Build-time savings: Estimated 2-4 months for offline diary/photo capture, BOQ/programme linking, claims workflow, report/PDF plumbing and Supabase-backed role/data patterns, assuming selective reuse rather than wholesale adoption.
- Evidence inspected: Repository metadata showing MIT, 0 stars/0 forks and a deployed homepage; exact latest commit/tree; verified LICENSE; database and dated schema inventory; frontend package/source tree; frontend/src/services/claimService.js with BOQ-linked items, cumulative quantities, draft/submitted/approved/rejected/paid workflow and summaries; frontend/src/components/diary/DelayEventSuggestion.js with explicit work-stoppage thresholds and affected-activity aggregation; offline storage/sync, photo, weather, programme, BOQ, report and PDF modules visible in the tree; limited test files noted in the source tree.
- License / rights: MIT repository license verified. Jurisdiction-specific legal/business assumptions must not be transplanted blindly: for example the claim service hard-codes a 5% retention default described as being 'as per CIPAA.' Treat such defaults as product-specific configuration requiring local legal/contract validation. External Supabase/other dependency terms still need normal production review.
- Reuse classification: Directly reusable under MIT terms for repository code, with jurisdiction-specific rules replaced by configurable/validated contract rules.
- Scores:
  - Technical value: 8/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 7/10
  - Build-time saved: 9/10
  - Data advantage: 7/10
  - High-ticket potential: 9/10
- Next action: Extract only the field-evidence data model/workflows first—diary, photo, weather/stoppage, BOQ/programme links and claim state—not the whole application. Connect those records to p6flow schedule revisions and ScopeSignal's deterministic contract-evidence gate, then validate the end-to-end packet on a synthetic construction change scenario.
