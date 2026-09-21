# Pair 1 — EXPERIMENT persistent state

## Validated reusable lessons
- Bidirectional money/evidence invariant tracing is now supported on two distinct tasks (01 and 02): trace operational observations/terms forward into approved money, then trace corrections, partial failures and external acknowledgements backward into evidence/state. This exposed stale charge evidence after repricing in task 01 and a non-atomic invoice-variance adjustment in task 02. Preserve explicit IMPLEMENTED/TESTED/RUN/UNVERIFIED labels. Eligible for central SEARCH_SKILLS promotion; not promoted during this bounded pair-file run.

## Failed search patterns
- High-conjunction repository metadata searches failed on tasks 01 and 02 even when the candidate existed. Broad web/TMS searches returned either no matches or shallow CRUD/document candidates. Prefer distinctive source/schema signatures; retain metadata search as cheap negative evidence, not the primary route.

## Useful terminology / signatures
- Physical/billing: consumed event ledger, departure_lower, appointment_clock_at, priced_pending_review, evidence_sha256, supplemental draft, stranded charges.
- Operating/money plane: carrier cost event, assignment_version, variance_tolerance_minor, invoice match, journal_batch_id, settlement status, EDI 210, executed adjustment, system-owned detention charge.

## Candidate search skills awaiting second-task confirmation
None. The task-01 invariant-tracing candidate achieved second-task confirmation on task 02 and moved to validated lessons. Central promotion remains pending.

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
