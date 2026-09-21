# Pair 1 — EXPERIMENT persistent state

## Validated reusable lessons
- Bidirectional money/evidence invariant tracing is now supported on tasks 01, 02 and 04: trace operational observations/terms forward into approved money, then trace corrections, partial failures and external acknowledgements backward into evidence/state. It exposed stale evidence, non-atomic payable creation and review-to-TMS bypass/replay. Preserve explicit IMPLEMENTED/TESTED/RUN/UNVERIFIED labels. Eligible for central SEARCH_SKILLS promotion; not promoted during this bounded pair-file run.
- Nested authority/version audit is now supported on two distinct tasks (03 and 04): after verifying the outer selector/gate, follow every referenced price/evidence/unit/correction dependency through final commit. Task 03 exposed mutable matrix history, incomplete replay identity and FX relabeling; task 04 exposed ignored classifier confidence, prompt-only conflict handling, untyped corrections and replayable approval. Eligible for central promotion; not promoted in this bounded pair-file run.

## Failed search patterns
- High-conjunction repository metadata searches failed on tasks 01 and 02 even when the candidate existed. Broad web/TMS searches returned either no matches or shallow CRUD/document candidates. Prefer distinctive source/schema signatures; retain metadata search as cheap negative evidence, not the primary route.

## Useful terminology / signatures
- Physical/billing: consumed event ledger, departure_lower, appointment_clock_at, priced_pending_review, evidence_sha256, supplemental draft, stranded charges.
- Operating/money plane: carrier cost event, assignment_version, variance_tolerance_minor, invoice match, journal_batch_id, settlement status, EDI 210, executed adjustment, system-owned detention charge.
- Document/review: gate_decision, review_reasons, field assessment, grounded evidence, arithmetic mismatch, classifier confidence, typed correction, approval idempotency, decision key, stale-processing lease.

## Candidate search skills awaiting second-task confirmation
- None. Nested authority/version audit achieved second-task confirmation on task 04 and moved to validated lessons. Bidirectional invariant tracing remains validated. Central promotion remains pending.

## Task 01 checkpoint — 2026-09-21

- Completed: 01. Result committed in cce5ac3159253147de91d9c5b8fbbf88a5af61d8. Next lowest unfinished assigned task: 02. Process only one task per run.
- Candidate: kodekinetics79/opstrax-enterprise-build @ fec2ba1432d6f8b4ba4c48be3d58e7e096819045. WATCH, 21/30; independent verifier agreed. Public code/test/schema/history inspection; repository tests not executed (dotnet absent, PostgreSQL unconfigured). No answer key/private-catalog discovery used.
- Evidence-backed local lesson: capability-conjunction code search found executable detention billing where domain metadata queries found nothing. This is one task, not proof of broad search superiority.
- Evidence-backed local lesson: trace both physical-observation bounds → priced interval and mutable input → frozen evidence → approved charge. First outside observation is an exit upper bound; immutable prior evidence can be stale after repricing.
- Failed patterns observed on this task: repository metadata query "detention geofence" and organization metadata query "logistics" returned zero; two broad GitHub web queries yielded no useful incremental candidate. Retry only with distinctive code signatures or a new reason; do not generalize to all metadata/web discovery.
- Useful signatures: consumed event ledger, departure_lower, appointment_clock_at, priced_pending_review, evidence_sha256, supplemental draft, stranded charges.
- Incorrect assumptions rejected: tests present = tests passed; frozen hash = current evidence; logged/enqueued = delivered notice; invoice pro-rata collection = settled line-level recovery.
- Candidate skill awaiting second-task confirmation: "Bidirectional money/evidence invariant tracing." Locate a rare capability conjunction; pin revision; follow observations to monetary decision; then follow permitted corrections back through immutable evidence and approval. Inspect uniqueness/conflict handling, authority origin, uncertainty semantics and tests, and obtain independent red-team review. Supported here by two independently confirmed source-level consistency gaps. Generalization remains unproven.
- Skill promotion gate: task evidence set {01}; no SEARCH_SKILLS.md update. Require useful confirmation on a distinct benchmark task or Integrator approval.
- Unresolved candidate test: do sparse-ping and appointment-reprice regression cases preserve conservative charges and an evidence packet matching the approved calculation? This is follow-up work, not permission to consume another benchmark task in this run.

## Task 02 checkpoint — 2026-09-21

- Completed: 02. Result committed in c9b63c12fde054248c3356e21fce04d867b89fc4. Next lowest unfinished assigned task: 03. Process only one task per run.
- Candidate: emoss08/Trenova @ 0ce45c2047619689bf3f829f10c1e5e93b26e057. STRONG, 24/30; independent verifier agreed with material caveats. Public source/schema/test/history/actions inspected; repository not executed locally.
- Capability evidence: dispatch/rating; carrier cost accrual; EDI 210 invoice persistence and variance matching; settlement generation/approval/posting; AP/cash journals and carrier ledger; detention-to-additional-charge-to-invoice path; transactional customer invoice dispute lifecycle.
- Calibration boundary: complete connected codebase, not production-ready. README says pre-release/not suitable for production; exact-SHA client CI failed, nearby Go unit/integration/codegen jobs failed; MarkPaid records manual disbursement/accounting but does not execute bank payment.
- Red-team result: AcceptWithVariance creates a pending adjustment cost event before separately updating the invoice match to Resolved. Without a shared transaction, a second-write failure can leave a payable adjustment eligible for settlement while reconciliation remains unresolved. Happy-path test exists; rollback test does not.
- Additional failure seam: some accrual observer failures are logged while the parent transition proceeds; durable repair/reconciliation was not established.
- Discovery result: distinctive code signatures found the complete candidate; high-conjunction metadata returned zero and broad TMS search produced shallow comparisons. Comparator triage: neozhu/tms, andiyzeiri/claude-trucking-tms, itsupportfc/FMS and sean00880/SouthernHaulers did not show the same verified conjunction in scoped searches.
- Reusable confirmed procedure: locate rare state/schema conjunctions; pin revision; prove one end-to-end money path in source/schema/tests; inspect history/CI; then failure-inject mentally at every cross-repository/service write and distinguish recording an external action from executing/confirming it. Evidence set {01, 02}.
- No SEARCH_SKILLS.md write in this run. A future owner may promote the validated method without waiting for another task; preserve the task-01/task-02 evidence and failure modes.
- Unresolved candidate test: transactionally couple variance adjustment creation with match resolution, then run injected second-write failure plus concurrent settlement-generation tests. Also establish a durable missed-accrual repair path.

## Task 03 checkpoint — 2026-09-21

- Completed: 03. Result committed in d24682b31139e6cb58a011c9796793ee2e375653. Next lowest unfinished assigned task: 04. Process only one task per run.
- Candidate: emoss08/Trenova @ e6eb6a5034ceeaca43ea5ab1882951f61853d072. WATCH, 23/30; independent verifier agreed. Public source/schema/test/history/checks inspected; repository tests not executed locally.
- Capability evidence: effective-dated customer/carrier agreements and lane rules; mode/service/equipment and operational applicability; deterministic total ordering; formula, weight-break and multi-axis matrix pricing; minima/maxima/discounts/rounding/dated FX; persisted input/candidate/component traces; explicit contract simulation and amendments.
- Calibration boundary: a detailed trace proves what the engine did, not that it preserved the correct unit or historical source. FX lookup failure returns the unconverted numeric amount while downstream exposes billing currency. Exact pin is pre-release and red in public checks.
- Reverse-path result: ordinary shipment recalculation uses FormulaOnly=true and can keep a previously seated rule/matrix result after shipment facts change unless explicit contract rerating occurs.
- Nested versioning gap: matrix cell replacement transactionally deletes the old grid and inserts the new grid; cells lack effective windows/history. A past-as-of rerate can therefore apply a later matrix sheet despite effective dates on the outer rule. Quote trace retains the old value but the resolver cannot reconstruct deleted cells.
- Replay-identity gap: ContextHash omits SellTotal although carrier percent-of-sell pricing consumes it and cannot enumerate arbitrary custom-formula inputs. Equal context hash and engine version are not sufficient evidence of equal result.
- Additional negative knowledge: mode lookup intentionally fails open to unscoped rules; overlapping tariffs resolve deterministically instead of raising an exception; candidate retrieval caps at 200; the Per Pallet template uses totalPieces; a NOT VALID exact-one method constraint leaves legacy unmapped rules possible.
- Discovery result: metadata searches were again weak; code conjunctions and scoped schema/source comparison found the qualifying engine. Comparators Project-RateEngine, Kareya-Silo, Fleet360 and hala-commercial-engine exposed fragments but not the same verified conjunction.
- Prior-lesson impact: the validated task-01/task-02 bidirectional invariant directly caused inspection of FX failure, ordinary recalculation and matrix replacement after the forward rating path appeared complete. This is retained-lesson reuse on a distinct task.
- Candidate skill awaiting second-task confirmation: nested price-source authority audit. Verify the effective-dated outer selector, then independently version/check referenced matrices, formula variables, FX rates and output units. Evidence set {03}; do not promote yet.
- No SEARCH_SKILLS.md write. The nested-authority lesson requires a second distinct task or Integrator approval.
- Unresolved candidate tests: fail an EUR→USD lookup and assert no USD-labeled unconverted charge can be applied; edit lane/weight/service and assert explicit re-resolution; replace a matrix, then rerate a shipment at the prior as-of date and require the original cell/value; include SellTotal in replay identity.

## Task 04 checkpoint — 2026-09-21

- Completed: 04. Result committed in ad95565d69a40f208487b8535a4e67b05b448697. Next lowest unfinished assigned task: 05. Process only one task per run.
- Candidate: Shreyas2409/freight-intake @ 49ee48e383aea202cc5ddf15c500a5b39092d8b7. WATCH, 22/30; independent verifier agreed. Public source/schema/tests/history inspected; 28 offline tests independently passed and six paid-API tests skipped.
- Capability evidence: rate-confirmation Decimal schema; per-field value/confidence/evidence/page; exact-page substring grounding; required-field, MC/state/date/weight and line-haul+fuel+detention=total validators; explicit auto_commit/review/failed decisions; persisted review items; worker/job model; human correction and TMS boundary.
- Adversarial run: classification confidence 0.01 still auto-committed when extracted fields passed because classifier confidence is ignored after type selection.
- Adversarial run: a math-mismatch review accepted total_rate=NOT_A_NUMBER. Repeating the same approval returned success again and created a second TMS record. Corrections are not typed/revalidated; status is not checked/locked; no unique decision key exists.
- Ambiguity run: page text containing two coherent conflicting rate sets auto-committed when the chosen set was grounded and internally consistent. Deterministic code does not enumerate competing money candidates; conflict refusal depends on prompt compliance.
- Reliability gap: claimed jobs enter processing before extraction but have no lease/heartbeat/stale-processing reaper. Caught failures retry; worker death can strand state.
- Provenance/operational boundary: one unsigned root commit, no public test CI, no LICENSE, take-home status, synthetic fixtures, no auth/tenant/CSRF/upload/parser-sandbox/retention controls. Author-reported Postgres/live-API results were not upgraded to independently verified evidence.
- Discovery result: direct metadata was sparse; source/test conjunctions and fixture names found the exact capability. Scoped analogs had broader parsers or review infrastructure but not the same verified rate-confirmation arithmetic-to-review conjunction.
- Prior-lesson impact: bidirectional tracing forced review→TMS inspection; task-03 nested-authority audit forced checks of classifier confidence, competing evidence, correction types and approval identity. Both produced executable falsifiers.
- Validated reusable procedure: nested authority/version audit, evidence set {03, 04}. Verify the outer gate, then every referenced source/unit/version and every post-review correction/commit edge. A review queue is not a safety boundary unless correction and approval preserve the original invariants.
- No SEARCH_SKILLS.md write in this run. The lesson now meets the two-task evidence threshold and is eligible for later central promotion without another benchmark task.
- Unresolved candidate tests: require low classifier confidence to review; detect multiple coherent money sets; parse corrected fields through the typed schema; rerun all cross-field validators; record actor/diff/source hash; enforce a unique approval decision key under concurrent POST; reclaim expired processing leases.
