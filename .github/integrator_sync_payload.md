MARKER: <!-- INTEGRATOR-R13-2026-09-20T1900-0400 -->

=== SUBSTITUTE CAPABILITIES.md ===
### CAP-009 — Schedule verification and conservative repair
- Ability/maturity: **VALIDATED COMPONENT** — verify deterministic constraints, explain violations and produce minimum-disruption repairs under hard locks.
- Evidence: joschiservice/RosterSpec CP-SAT/golden/oracle/load tests.
- Limitation/next test: labor/domain rules remain external; compare one closed period against incumbent repair behavior.
--- NEW ---
### CAP-009 — Schedule verification, temporal rule authority and conservative repair
- Ability/maturity: **VALIDATED COMPONENT / historical-rule acceptance test pending** — verify deterministic schedule constraints, preserve manual hard locks, explain violations and produce minimum-disruption repairs while selecting the rule revision that was effective for the shift/event date and knowable/approved at the evaluation cutoff.
- Evidence: `joschiservice/RosterSpec` supplies deterministic hard-lock verification/repair. `Payroll-Engine/PayrollEngine@2ddb5c770b0a955936562355a1021f06e922886a` + `PayrollEngine.Backend@ecd049ee43a64c130981301192a0f8ab36eed1ed` add a reusable temporal authority substrate: runtime SQL filters by both created/knowledge cutoff and `ValidFrom`, picks the latest eligible version, executable fixtures cover effective-date boundaries, and timesheet validation loads rule state at the actual work date. `JayySap/ShiftGaurd@acef23ab97b216c25f58f136443c899fe623c615` is retained as a negative oracle for hard-coded compliance numbers, incomplete rule semantics and warning-without-block behavior.
- Required receipt: source identity, rule/version/hash, effective interval, known/approved timestamp, jurisdiction/worker/agreement/exemption scope, explicit outcome type (`BLOCK|PREMIUM_PAY|REVIEW|ALLOW`), schedule hash, verifier/solver revision, verdict and repair delta.
- Critical boundary: solver feasibility is not legal/domain authority. Static settings, labels such as “labor law,” and a warning flag do not prove currentness, semantic completeness or enforcement. Official/customer-owned rule content and legal applicability remain external authority.
- Next test: freeze a source-backed rule bundle and require deterministic historical PASS/FAIL/REVIEW plus minimum-disruption repair across mid-period rule changes, retroactive corrections, collective-agreement overrides, emergency exceptions, premium-pay alternatives, stale cached rules, unknown scope and DST/timezone boundaries without consulting mutable current settings.

=== SUBSTITUTE CAPABILITIES.md ===
### CAP-015 — Prospective, leakage-resistant prediction evidence
- Ability/maturity: **VALIDATED COMPONENT / live calibration parity pending** — separate historical development from immutable prospective decisions so later outcomes cannot rewrite prior calls.
- Evidence: grid-crunch, queue_attrition and USECPO outcome-evaluator design. Mendeley dataset DOI `10.17632/r4csg2h2ps.1` now supplies an exact external witness-package receipt: version 1, one 12,980,662-byte package represented by two byte-identical aliases, outer SHA-256 `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`.
- Evaluator contract: USECPO event-correlated rows must be whole-event blocked by literal `event id`; STANDARD/8H/24H are sensitivity variants, not independent validators; preserve EAGLE-I+DOE-417 ancestry, geography quality and restoration imputation; prefer 2019–2023 for first high-confidence benchmark. Duplicate package aliases count as one external witness.
- Limitation/next test: the Mendeley **outer package** hash is not the embedded USECPO source hash. Extract the public package manifest, read the exact USECPO source URL/release/size/SHA row, compare it with direct first-party OEDI bytes or a first-party published digest, and keep `UNKNOWN/MISMATCH` hard-fail semantics. Byte-level v2 headers/timezone/sentinels/thresholds/event-id namespace also remain to be confirmed from the official artifact.
--- NEW ---
### CAP-015 — Prospective, leakage-resistant prediction and evaluator-grain evidence
- Ability/maturity: **VALIDATED COMPONENT / live calibration parity pending** — separate historical development from immutable prospective decisions so later outcomes cannot rewrite prior calls, while binding the evaluator to stable event identity and the correct additive outcome grain.
- Evidence: grid-crunch, queue_attrition, USECPO outcome-evaluator design and `Jaskeeratr/grid-reliability-analytics@24e59a7318db3560b6547ff9b79416119abf6ecb` as a strong secondary evaluator-QA component. The downstream audit lands the literal 2014–2023 `eaglei_outages_with_events` files, independently reproduces 526,165 raw rows, finds 663 bare `event_id` strings but 2,953 events under a fuller natural key, and shows exact-row duplication plus event↔spell fan-out can inflate naive additive customer-hours from 2.529B at unique-spell grain to 21.479B on the flat rows (~8.49×). Mendeley DOI `10.17632/r4csg2h2ps.1` remains an external witness-package receipt, not first-party byte identity.
- Evaluator contract: bare `event_id` is **not** globally unique across 2014–2023. Use a release-bound composite identity at minimum `(source_year,event_id)` and preferably preserve `(event_id,event_began,event_restored,raw_event_type,source_year/file)`. Build a unique county-outage-spell fact grain `(fips,start_time,end_time)` and a distinct many-to-many spell↔event bridge; calculate additive outage burden once per unique spell. Whole-event blocking must use composite identity. STANDARD/8H/24H remain sensitivity variants, not independent validators.
- Critical invariant: a correct source hash proves byte identity, not semantic evaluator correctness. Exact-row dedupe alone is insufficient when one county spell maps to multiple events, and downstream timezone-naive parsing is not first-party timezone authority.
- Limitation/next test: first-party OEDI ZIP digest/bytes remain unresolved in the current evidence chain. Verify the current first-party artifact against the external expected digest, byte-inspect source schema/time/null semantics, then freeze the composite-event + unique-spell evaluator manifest before running policy scores.

=== SUBSTITUTE CAPABILITIES.md ===
### CAP-018 — Provider-to-bank settlement ambiguity and payout-proof state machine
- Ability/maturity: **VALIDATED COMPONENT / provider-to-bank benchmark pending** — move payout/refund intent through provider state into independent bank/payroll observation and later counter-events without unsafe retries or false finality.
- Evidence: Spree/OpenPartner, Modern Treasury bank-derived transaction/return lineage, ACHInterbank Exact/Ambiguous/NotFound oracle, moov/ach returns and `NotAbdelrahmanelsayed/paymob_integration@8999a679...` reversal-safe provider recovery. `nzebrian/eruofood-ai@9c191ece...` strengthens historical payable authority and internal re-open semantics: immutable capture-derived earning/rate authority -> reserved settlement -> non-retryable UNKNOWN -> compensating reversal -> original accrual available for re-settlement. `Layr-Labs/d-inference@1451a4c...` supplies an external automatic payout/transfer counter-event comparator and explicit cash-location semantics.
- Paymob strengthens the provider-side invariant: timeout/5xx stays Pending; lost webhook can be repaired by provider inquiry; a refund request marker is persisted before the one-shot side effect; only confirmed signed/independently fetched child refund evidence posts the compensating ledger entry; inconsistent cumulative totals route to review.
- Limitation: hosted provider/bank connectivity and source coverage remain external; trace/reference alone is not unique economic identity; `provider paid/refunded` is not bank finality. EruoFood does not yet prove that a post-success external bank/provider return automatically invokes its authority-preserving re-open path.
- Next test: EXP-003/010 matrix covering unknown provider result, duplicate/ambiguous bank mapping, cumulative refund without child proof, stale/unavailable feed, bank-posted-then-returned and exact one-use reversal; include a fixture where a late externally observed counter-event reopens the exact original historical payable without current-rate drift.
--- NEW ---
### CAP-018 — Provider-to-bank settlement ambiguity, terminal readback and payout-proof state machine
- Ability/maturity: **VALIDATED COMPONENT / provider-to-bank benchmark pending** — move payout/refund intent through provider state into independent provider/bank/payroll observation and later counter-events without unsafe retries, terminal-state blindness or false finality.
- Evidence: Spree/OpenPartner, Modern Treasury bank-derived transaction/return lineage, ACHInterbank Exact/Ambiguous/NotFound oracle, moov/ach returns, Paymob recovery, EruoFood historical payable authority/re-open semantics, and `tonytonycoder11/stripe-connect-reckon@deb30aabfed84c7b0b2e5ae28c92cc9f85f79193` as a read-only terminal-state provider sensor. The latter lists Stripe Connect payouts independently of local payout status and can flag a provider-side `payout.failed` or missing processed event even when the vertical application already believes the payout is terminal.
- Critical invariant: “reconcile” is not enough; inspect which rows the job observes after local success. Webhook replay, direct provider-object readback, bank/cash observation and the local historical payable are separate evidence planes. A provider failure/reversal also needs economic classification: `BANK_RETURN_STILL_OWED` may reopen the original earning, while `REFUND/CLAWBACK_NOT_OWED` must not create a duplicate repayment.
- Limitation: finite provider/event lookback creates an explicit finality horizon; provider object truth is still not beneficiary-bank finality; `stripe-connect-reckon` is deliberately read-only and does not map findings back to historical payable authority.
- Next test: local payout = COMPLETED, suppress reversal webhook, later provider state = failed, independent scanner rediscovers the contradiction by exact payout identity, remediation remains blocked until still-owed vs clawback is classified, and only the still-owed branch reopens the exact original earning under its original rate authority before independent bank/payroll observation.

=== APPEND COMPONENTS.md ===
## Integrator component delta — 2026-09-20 19:00 ET
- **`Payroll-Engine/PayrollEngine@2ddb5c770b0a955936562355a1021f06e922886a` + `PayrollEngine.Backend@ecd049ee43a64c130981301192a0f8ab36eed1ed` — 26/30:** temporal labor/domain rule authority substrate. Runtime SQL selects by both knowledge cutoff and effective date; fixtures exercise version boundaries. Use to feed RosterSpec-style deterministic verification, not as universal legal authority.
- **`Jaskeeratr/grid-reliability-analytics@24e59a7318db3560b6547ff9b79416119abf6ecb` — 28/30 evaluator-QA component:** exposes cross-year `event_id` reuse and the additive-grain error in flat USECPO rows; retain as strong secondary evidence, not first-party dataset authority.
- **`tonytonycoder11/stripe-connect-reckon@deb30aabfed84c7b0b2e5ae28c92cc9f85f79193` — 25/30 WATCH/strong component:** terminal-state Stripe Connect readback and event-gap sensor independent of local payout state. Detection only; economic reopen/classification remains external.
- **`intuit/QuickBooks-V3-Java-SDK@c4d5dfad23ffebf0302356876d0dc389708513a9` — 26/30:** QBO caller-controlled `requestid` reaches provider writes, but the SDK clears it after URI construction and auto-generates a new one when absent. Durable effect identity must live outside SDK/process lifecycle. `simstudioai/sim@a2c9756113a13debfa1c6b5b1503700fae9007d9` is a useful adapter reference because VendorCredit creation accepts optional request ID and disables blind automatic retry.
- **`manuvarkey/cmbautomiser@fea18e164c63dad4526ac59d7a51cfec7cafb860` — 21/30 WATCH/negative oracle:** exact measurement-item→bill references and ordinary duplicate-selection locks coexist with edit/delete paths that can recompute or erase historical bill support. This is a strong immutable-evidence falsifier, not a money-authority engine.
- **`awksedgreep/caretaker@08b309dd927f7f2c26d4aa42fec4533dceeb7cf1` — 22/30 WATCH/negative-control endpoint:** encodes USP `allow_partial`/`required` fields but its Set handler does not consume them and its generic state store can create unknown paths. Use in the three-way USP transaction-integrity fixture; source-predicted outcome remains unexecuted.

=== APPEND KNOWLEDGE_GRAPH.md ===
## Integrator graph delta — 2026-09-20 19:00 ET
- `PayrollEngine temporal regulation selection` -> **STRENGTHENS CAP-009** -> `source-backed effective/known-at rule bundle` -> `RosterSpec hard-lock verify/repair` -> **EXP-008 workforce-rule acceptance**.
- `Jaskeeratr/grid-reliability-analytics@24e59a7...` -> **CHALLENGES prior bare event_id grouping assumption** -> strengthens **CAP-015** -> sharpens **EXP-012** with composite event identity + unique county-spell grain.
- `stripe-connect-reckon@deb30aab...` -> independent terminal provider observation -> strengthens **CAP-018** -> **EXP-010** lost-post-success-webhook fixture; reason-aware historical payable reopen remains a separate edge.
- `QuickBooks-V3-Java-SDK@c4d5df...` -> provider mutation identity exists but SDK resets it -> strengthens **CAP-016 / EXP-002** provider-adapter acceptance; durable request identity must be restored explicitly after restart.
- `cmbautomiser@fea18e1...` -> exact evidence reference + mutable-history failure -> **NEGATIVE_CONTROL EXP-005**; one-time selection is not historical immutability.
- `caretaker@08b309d...` + `ac-client@132c20a...` + `BroadbandForum/obuspa@59028be...` -> three-way USP Set semantic matrix -> **CAP-014 / EXP-008**; neutral runtime fixture required before conformance claims.
- SAM first-party historical resource observation for `N6600126Q6264` -> **CAP-011** separates action membership, semantic artifact identity and byte availability; verified membership may coexist with inferred filename and unavailable bytes.
- Freight Pilot Charter trust review -> **CHALLENGES EXP-001 launch gate** and **CAP-007 admission semantics**: strict JSON types + authority-bound launch-decision receipt are prerequisites to treating `KICKOFF_AUTHORIZED` as trusted.

=== APPEND COMBINATIONS.md ===
## Combination delta — 2026-09-20 19:00 ET

### Workforce historical-rule acceptance stack
`official/customer-owned rule source -> versioned rule snapshot (effective-at + known/approved-at + source/version/hash + scope) -> executable outcome semantics (BLOCK|PREMIUM_PAY|REVIEW|ALLOW) -> RosterSpec hard-lock verification/repair -> receipt with schedule hash + rule bundle hash + solver/verifier revision`.
A solver can be mathematically correct while the rule bundle is stale, semantically incomplete or non-authoritative; currentness and enforcement remain separate proof planes.

### Payout finality sentinel + authority-preserving remediation
`event-time earning authority -> local payout success -> independent terminal provider scan -> exact provider contradiction/event gap -> economic reason classification -> compensating ledger -> conditional reopen of original obligation -> independent bank/payroll observation`.
Provider readback solves terminal-state blindness but does not decide whether money is still owed; generic “reversal” labels are not enough.

### AP safe-writeback provider identity chain
`exact reverse capacity -> durable logical effect ID -> provider-specific idempotency identity persisted before dispatch -> SDK context reconstructed with the same identity -> ambiguous result = UNKNOWN -> authoritative business-record readback -> APPLIED / proven NOT_APPLIED / UNKNOWN -> proof receipt`.
A provider may support safe duplicate suppression while an SDK default silently generates a fresh identity after restart.

### Grid evaluator semantic-proof chain
`first-party dataset bytes/digest -> raw source provenance -> composite event identity -> unique county outage-spell fact grain -> many-to-many spell↔event bridge -> whole-event blocked split -> additive outcome once per spell -> immutable evaluator receipt`.
Hash integrity and dedupe are both necessary but neither proves the aggregation grain is economically/scientifically correct.

=== APPEND EXPERIMENTS.md ===
## Integrator experiment delta — 2026-09-20 19:00 ET
- **EXP-001 Freight:** before customer-data kickoff, add strict type negatives for every Pilot Charter acknowledgment (`"false"`, numbers, null, containers), scalar-string carrier/mode scope, and a self-consistent fabricated READY decision. `KICKOFF_AUTHORIZED` is trusted only when the Charter transitively binds a current launch-gate receipt containing readiness/component/rights/deployment-environment evidence digests, request flags, gate revision and verdict. After that internal gate, the commercial blocker remains one explicitly authorized frozen buyer population reaching attributable credit/refund/remittance.
- **EXP-002 AP writeback:** add QBO crash/restart acceptance. Persist semantic effect ID + exact QBO `requestid` before dispatch; kill/lose response; reconstruct SDK context; explicitly restore the same request ID; reconcile the exact VendorCredit. Negative branch omits restoration and proves a new SDK-generated ID must never be treated as the same operation. Retention horizon and negative-readback authority remain unresolved.
- **EXP-005 ScopeSignal:** add post-acceptance mutation cases: billed measurement edited in place, billed measurement deleted, structural renumber/path rewrite, visible `Billed` flag while edit/delete remains reachable, and exact-item selection lock with no immutable evidence version. Accepted money must retain the original evidence version; correction requires an explicit amendment/counter-event.
- **EXP-008 Protocol/Workforce:** add the `USP-SET-TRIANGLE` runtime corpus and a separate CAP-009 historical-rule bundle corpus. For USP, one neutral controller sends `allow_partial=false` with one valid + one required invalid parameter and measures wire result, model state, persistent state, live state and restart state across OB-USP/ac-client/Caretaker. For workforce rules, freeze effective/known-at rule bundles and test mid-period changes, overrides, alternatives, stale cache and DST.
- **EXP-010 Payout finality:** add local COMPLETED + suppressed webhook + later provider failed fixture using independent terminal scanning, then require reason-aware still-owed-vs-clawback classification before historical earning reopen.
- **EXP-012 Grid:** bare `event_id` is forbidden as a cross-year split key. Require first-party byte/digest verification, composite event key, unique `(fips,start_time,end_time)` spell table, distinct spell↔event bridge and additive burden once per unique spell before any policy score is accepted.

=== APPEND REJECTED.md ===
## Negative knowledge delta — 2026-09-20 19:00 ET
- **Hard-coded compliance number + jurisdiction label != rule authority.** Require source/version/currentness, effective/known-at time, scope and explicit outcome semantics; warnings that still publish are not hard constraints.
- **Bare USECPO `event_id` != global event identity.** Cross-year reuse is observed; a flat event-correlated row set is not a safe additive fact table and exact-row dedupe does not eliminate event↔spell fan-out.
- **Reconciliation job != terminal readback.** If the query selects only pending/processing/submitted rows, the system is blind after local success. Webhook replay and direct provider object scans are separate evidence planes.
- **Provider idempotency != durable application identity.** SDKs may auto-generate/reset request identifiers between calls; a money operation must persist its provider key before dispatch and restore it after restart. `SyncToken`/record versioning is not create-request dedupe.
- **One-time bill selection != immutable historical evidence.** If the selected measurement can later be edited/deleted and the accepted bill silently recomputes, the original proof chain is not historical.
- **Schema/protobuf field present != mutation semantics enforced.** Trace `allow_partial`/`required`/atomicity fields into handler use, staging/transaction behavior, rollback and post-state before crediting them.
- **SAM resource membership != semantic filename/content identity != byte availability.** Preserve all three states separately; HTTP 400 is not proof of permanent deletion without source semantics.
- **Python type hints/self-hash != authorization.** Unvalidated truthy strings can defeat boolean acknowledgment gates, scalar-string coercion can corrupt scope shape, and a recomputed self-hash does not prove upstream decision provenance/currentness.

=== APPEND SEARCH_QUEUE.md ===
## Integrator queue delta — 2026-09-20 19:00 ET
1. **P0 Freight pilot gate + external validation:** first harden the Pilot Charter so `KICKOFF_AUTHORIZED` requires strict JSON types and a current authority-bound launch-decision receipt; then stop internal freight discovery and run one explicitly authorized frozen buyer population to actual settlement evidence.
2. **P1 Grid EXP-012 correctness:** obtain/hash the current first-party OEDI artifact; if byte identity is established, freeze composite event identity + unique county-spell grain + event bridge before any historical scoring. Do not run the old bare-`event_id` evaluator.
3. **P1 AP EXP-002 provider semantics:** establish authoritative QBO `requestid` retention/expiry and a conservative VendorCredit negative-readback contract; run the process-restart same-request-ID fixture. Do not hunt generic idempotency libraries.
4. **P1 Payout EXP-010:** join terminal provider scanning to one vertical historical earning/payable by exact payout ID and classify still-owed vs clawback before reopen/re-pay. Do not count generic pending-state polling as finality assurance.
5. **P1 ScopeSignal EXP-005:** execute immutable-evidence mutation corpus before another RA-bill search. Require accepted bill -> immutable measurement version edge and explicit correction/counter-event.
6. **P1 CAP-009 workforce authority:** combine PayrollEngine-style effective/knowledge-time selection with RosterSpec verification/repair on a frozen historical rule bundle. Do not treat static compliance settings as authority.
7. **P2 Protocol pre-FAT:** execute the existing USP/SECS differential fixtures with neutral measurement before discovering a fourth implementation. Caretaker is a negative-control endpoint until runtime evidence exists.
8. **P2 CaptureBrief EXP-006:** keep `VERIFIED_ACTION_MEMBERSHIP / semantic_identity / byte_state` separate; move to the next frozen solicitation family rather than repeatedly guessing routes for the same unavailable historical object.

=== APPEND TECHNOLOGY_RADAR.md ===
## Integrator radar note — 2026-09-20 19:00 ET
No numerical emergence score changed. Four qualitative signals strengthened:
- **Temporal authority is becoming a reusable application primitive:** effective-at and known-at rule selection belongs beside solver correctness in workforce/payroll/compliance systems.
- **Evaluator semantics are part of proof:** artifact hashes do not prevent false scores caused by unstable identity or wrong additive grain.
- **Financial finality is multi-observer and revocable:** local terminal state, provider object state, provider event history, bank/cash location and economic entitlement are distinct planes.
- **Trusted transitions need typed authority receipts, not self-hashes:** runtime type validation and upstream-verdict provenance are now explicit negative controls for proof-carrying operational software.
These are architecture/evidence signals only; no adoption or revenue acceleration is inferred.

=== APPEND OPPORTUNITIES.md ===
## Portfolio movement — 2026-09-20 19:00 ET
- **#1 Freight Recovery remains rank-1 but its launch gate is temporarily non-green.** The machine-checkable Pilot Charter has a strict-type/provenance defect at `KICKOFF_AUTHORIZED`; fix and adversarially test that boundary before customer-data kickoff. The external commercial blocker remains an authorized frozen buyer population and realized settlement evidence.
- **Grid Resilience Calibration strengthens technically, rank unchanged.** The evaluator-grain audit materially reduces false-score risk but first-party byte identity and independent/out-of-time evaluation still gate commercialization claims.
- **Payout Finality / Commission Assurance strengthens technically.** Terminal provider scanning makes a read-only Payout Finality Sentinel more credible, but reason-aware historical entitlement mapping and independent bank/payroll outcome are still required.
- **Workforce Schedule Rule-Version Acceptance Test becomes a clearer bounded wedge.** Temporal rule-version selection plus deterministic repair can expose schedules that were valid under configured settings but not provably valid under the correct effective/known-at authority; jurisdictional rule substance remains external.
- No opportunity rank is increased from repository evidence alone. No new realized customer value or revenue is recorded in this integration.
