# Pair 1 — EXPERIMENT results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

---

TASK: 01 — Geofence/appointment evidence to detention billing
CONDITION: EXPERIMENT
STARTING HYPOTHESIS: A rare conjunction of geofence, appointment, detention and approval in code will reveal an executable observation → rule → review → charge chain more effectively than TMS labels. A production-shaped candidate must preserve physical observation bounds and keep approved money consistent with its evidence, including after corrections.
DISCOVERY METHODS:
- Direct repository-domain query: detention geofence (zero metadata matches).
- Public web-domain queries: site:github.com detention geofence billing approval; site:github.com logistics "appointment" "physical" "detention" (no useful incremental results).
- Code-level capability conjunction: "detention" "geofence" "approval"; then scoped comparator query detention appointment approval test across IH35-TMS and Trenova.
- Organization graph: kodekinetics79 + logistics (zero metadata matches; description was absent).
- Reused SEARCH_SKILLS capability-conjunction/claim-tracing and acceptance-path/invariant-consistency procedures. Did not use the private ledger to seed answers or read BENCHMARK_GOLD.md.
CANDIDATE: Opstrax Enterprise — detention recovery subsystem
CANONICAL URL: https://github.com/kodekinetics79/opstrax-enterprise-build
EXACT REVISION: fec2ba1432d6f8b4ba4c48be3d58e7e096819045; independently resolved commit dated 2026-09-16T04:04:35Z, "Handle queued Render deploy responses (#268)". Deliberately evaluated this pinned revision, not every subsequent main change.
VERDICT: WATCH
A-F SCORE: A 3 / B 4 / C 4 / D 4 / E 3 / F 3 = 21/30. Substantial domain implementation; incomplete physical/evidence invariants prevent STRONG. F reflects integration/operational uncertainty, not a penalty solely for missing public license.
EVIDENCE INSPECTED:
- Code inspector: [DetentionService.cs](https://github.com/kodekinetics79/opstrax-enterprise-build/blob/fec2ba1432d6f8b4ba4c48be3d58e7e096819045/backend-dotnet/Services/DetentionService.cs), [GeofenceEvaluator.cs](https://github.com/kodekinetics79/opstrax-enterprise-build/blob/fec2ba1432d6f8b4ba4c48be3d58e7e096819045/backend-dotnet/Services/GeofenceEvaluator.cs), [DetentionReviewService.cs](https://github.com/kodekinetics79/opstrax-enterprise-build/blob/fec2ba1432d6f8b4ba4c48be3d58e7e096819045/backend-dotnet/Services/DetentionReviewService.cs), and [notification handler](https://github.com/kodekinetics79/opstrax-enterprise-build/blob/fec2ba1432d6f8b4ba4c48be3d58e7e096819045/backend-dotnet/Services/DetentionWarningNotificationHandler.cs).
- Schema: [detention recovery migration](https://github.com/kodekinetics79/opstrax-enterprise-build/blob/fec2ba1432d6f8b4ba4c48be3d58e7e096819045/database/migrations/2026_07_22_stage47_detention_recovery.sql); independent verifier additionally inspected DetentionSchemaService.cs and uniqueness controls.
- Tests source-inspected: DetentionPricingPostgresTests.cs, DetentionDetectionPostgresTests.cs, DetentionApprovalPostgresTests.cs, GeofenceEvaluatorPostgresTests.cs under backend-dotnet.Tests at the same revision. Assertions cover appointment anchoring, downward increments, missing appointment, bounce merging, repeated detection/approval, notice logging and direct-ingest event timestamps.
- History: substantive detention commits c189296038e666d93ec350222f4a8ce8313ecc92, 4d34a385734d1722ac63b06e4a5a9bb154204c84, 230cafb586b1d7abee2ad64d86bb58b776cf274f (2026-07-22), and dcbb21dcbbf9c092ea0399d1459319ee788e6f22 (2026-09-16). History supports implementation activity, not deployment or realized recoveries.
- Commercial/ecosystem pass: public metadata showed zero stars, absent description and no detected repository-wide license. Tree contained mobile/LICENSE, which does not establish rights for the whole project. Apply user's separate repository-code authorization; third-party data, services and assets remain separately scoped.
- Comparator triage: IH35-TMS geofence timing specification at ec8680d3eab1c0e86f58feb1e712940bb9e14d50 describes source tags, timing and approval, but this was document-only inspection. Trenova and HeartF-Logistics surfaced in code search; neither received a full competing-system assessment.
- Independent RED-TEAM/VERIFIER: separate agent benchmark01_verifier inspected public pinned source without benchmark answer access and returned WATCH. It independently confirmed the stale-evidence and physical-bound concerns below. Code/commercial/ecosystem passes were role-separated analysis; the verifier was a separate agent.
CLAIMS VERIFIED:
- IMPLEMENTED: detection → attribution → appointment clock → effective-dated rule selection → pricing → review → charge. Missing appointment/terms block pricing; later-of appointment/arrival anchors the clock; increments round down.
- IMPLEMENTED: consumed-event ledger, bounce handling and guarded approval/unique per-dwell charge prevent specified repeat-processing cases; approval and charge creation share a transaction.
- IMPLEMENTED: late-arrival, missing shipper reference and expired claim-window overrides; unassigned jobs blocked. Supplemental draft invoicing for locked/issued original invoices and stranded-charge reporting exist.
- IMPLEMENTED: frozen canonical JSON evidence and SHA-256; real SMTP delivery adapter, with logged/sent/failed distinctions. Logged notification and SMTP acceptance are not proof of contractual recipient receipt.
- SOURCE-INSPECTED COUNTEREVIDENCE: normal CloseDwells assigns the first outside observation to departure_lower/billed_to_at. That observation bounds actual exit from above, not below. Polling EvaluateAsync omits position event-time/freshness and emits NOW; direct-ingest projection does preserve event time.
- SOURCE-INSPECTED COUNTEREVIDENCE: SetAppointmentAsync permits changing a priced pending/late dwell and resetting it for pricing; BuildEvidenceAsync retains existing immutable evidence via ON CONFLICT DO NOTHING; ApproveAsync retrieves that existing hash. Revised money can therefore remain attached to an older appointment/computation packet. Runtime regression not executed.
- Independent arithmetic check only: with arrival/appointment 09:00, last inside 11:50, first outside 12:10, 120 free minutes, 15-minute increments and $60/hour, the conservative last-inside bound prices $45 versus $60 using first outside. This is a synthetic bound illustration, not candidate execution or proof of an actual customer overcharge.
CLAIMS NOT VERIFIED:
- Repository integration tests were NOT executed: dotnet was absent and PostgreSQL was not configured. Test assertions are source evidence, not a passing run. Exact-SHA CI/deployment, actual recoveries, endpoint-wide approval enforcement and complete invoice/GL reconciliation remain unverified.
- Strict shortest-provable-dwell semantics are not established. Gap/timeout geometry is circle-based despite polygon support; missing-position and stale-position handling have limitations. Job/appointment attribution is inferred from assignment overlap/proximity/planned time, not independently authenticated appointment authority.
- Evidence contains breadcrumb count, not a complete coordinate/device/source-event provenance packet. Notification send-before-status and failure/configuration behavior do not establish exactly-once delivery or robust retries.
- Funnel collected amounts are invoice-level pro-rata estimates, not demonstrated line-level settled cash. No emerging-category acceleration, patent advantage or production adoption established from this single implementation.
STRONGEST OBJECTION: The component intended to prove recoverable dollars does not yet preserve two central invariants: conservative physical time bounds and current charge-to-evidence consistency. Good schemas, hashes and a review queue do not resolve these semantic gaps.
COMMERCIAL WEDGE: Fleet/broker operations teams preparing disputed detention claims: operator-reviewed arrival/appointment reconstruction, exception queue and auditable claim preparation. Money path is reduced review labor and better-supported recovery requests, not automatic recognition of detected amounts as cash. A narrow adapted pilot might take 4–8 weeks conditional on lawful telemetry/appointment access and integrations; this is an estimate, not observed revenue. Reusable schema, event ledger, pricing and billing seams compress implementation work; trusted customer-specific data and verified exception handling would be the defensible layer.
SEARCH EFFORT: 6 literal discovery queries across 4 attempted modes (repository metadata, web-domain, code-level, organization graph); 1 full source/test/schema/history deep inspection plus an independent review of that candidate; 1 document-only comparator. Four freight-domain repositories surfaced in code search; an unrelated lexical collision was discarded. No artificial candidate-count target.
FALSE-PROMOTION RISK: High if tests-present, immutable hashes, "notified", or "collected" are mistaken for executed correctness, evidence freshness, delivery or recovered cash. WATCH retained; no MASTER or SEARCH_SKILLS promotion.
LESSON: One-task evidence supports capability conjunction as a productive candidate-finding route, not yet a generally validated improvement. Trace observation bounds into pricing and corrections into evidence/approval as separate invariants; inspect immutable-write conflict behavior when inputs can change. Metadata-only queries missed this zero-star/no-description candidate. Useful signatures: consumed event ledger, departure_lower, appointment_clock_at, priced_pending_review, evidence_sha256, supplemental draft. No lesson promoted centrally.
COMPLETED_AT: 2026-09-21T02:11:30Z

VALUE HANDOFF:
- CAPABILITY DELTA: implemented reviewed detention-to-charge component, qualified by physical-bound and repricing/evidence gaps.
- GRAPH EDGE: potential physical-events → deterministic pricing → evidence → reviewed charge edge; no CAP/OPP/EXP IDs asserted because central ledger discovery was excluded for benchmark blindness.
- RADAR SIGNAL: one independent low-attention implementation; insufficient evidence of category acceleration.
- EXPERIMENT IMPACT: next evaluation should execute isolated sparse-ping, appointment-reprice/evidence, missing-position/polygon, and notice-failure regression tests before claiming recoverability.
- COMMERCIAL IMPACT: begin with assisted claim preparation; unattended billing would overstate demonstrated readiness.
- NEGATIVE KNOWLEDGE: immutable evidence is not necessarily current evidence; a first outside ping is not a conservative departure lower bound; enqueue counts and pro-rata collections are not economic outcomes.
