# SEARCH_QUEUE

Integrator-owned search and validation direction. Operator references updated 2026-09-21; domain directions retain their existing evidence basis. **Experiment bottlenecks, independent falsification, source authority and outcome evidence outrank repository count.** This file is current direction, not history; older overrides remain in Git history and hunter catalogs.

## Operating rules for all 14 workstreams
- Start with [`intelligence/WORKER_RUNBOOK.md`](intelligence/WORKER_RUNBOOK.md) for the current operator sequence. The [2026-09-21 strategy upgrade](intelligence/STRATEGY_UPGRADE_2026-09-21.md) describes the latest changes; it does not replace the frozen benchmark or domain stop conditions below.
- Check `intelligence/ROUTING_EXPLORATION.md` before interpreting a generated route. A V18 `explore_swap` route is an intentional low-regret matched assignment used to reduce routing-selection bias; do not manually move it back to the baseline slot merely because the baseline score was slightly higher.
- Treat `intelligence/ACTIVATION_RESPONSE_REPORT.md` as capacity-response evidence only. V17 may penalize future routing only after a worker was READY, received a primary activation, and accumulated sufficient resolved activation evidence. Never interpret UNKNOWN/OFFLINE/PAUSED presence, an unactivated READY event, a pending activation, or completion duration as poor worker performance.
- V16 generated claims are pull-based: publish fresh `READY` presence first, then use `intelligence/ACTIVATION_BOARD.md` / `activation_claim_packets.jsonl`. No activation means do not generated-claim. `UNKNOWN`, stale, paused or offline presence is capacity uncertainty—not evidence that a hunter is slow or poor-performing.
- Check `intelligence/DISPATCH_BACKPRESSURE.md` before claiming. Primary V15 tickets soft-stale after 75 minutes and hard-expire after 150 minutes. Never claim a hard-expired primary ticket; use `WORK_STEAL_QUEUE.md` only after expiry. Work-steal runs are measured separately and do not train V13 primary-routing quality.
- Before claiming routed work, use `intelligence/DISPATCH_BOARD.md` / `dispatch_claim_packets.jsonl`. A generated claim must carry the current `DISPATCH:` ticket exactly. Claiming a different slot is allowed only as an explicit `manual_override` with a reason, and that override must not train the generated-route learner.
- Review `intelligence/ROUTING_LEARNING_REPORT.md` before interpreting worker specialization. V13 trains only from completed MATCHED generated routes and remains observe-only until its evidence thresholds are met; manual reroutes and retrospective repairs do not train it.
- Check `intelligence/WORKER_ROUTING.md` before claiming work. If a worker has a generated V12 route, claim that routed slot; active V11 claims remain locked. Manual reroutes must be explicit and should be recorded as routing overrides rather than silently training the router.
- Claim work through `intelligence/EXECUTION_BOARD.md` / `execution_events/SLOT-XX.jsonl` before executing it. One worker may hold one live claim by default. Heartbeat before lease expiry. Write telemetry using the current `intelligence/SEARCH_RUN_TEMPLATE.json` and the runbook's exact claim/assignment provenance first, then append COMPLETE with that exact run ID; completion without matched telemetry is invalid.
- Review `intelligence/ALLOCATOR_LEARNING_REPORT.md` before coordinated cycles. V10 may move at most one slot among experiment/coverage/adjacency after sufficient attributed evidence; measurement, verification and wildcard remain protected. Manual overrides must be explicit and do not train the automatic portfolio learner. Use the report's current attributed counts, sufficiency gates and adaptation decision; no portfolio-capacity shift is justified while those gates remain unmet.
- Start each coordinated cycle from `intelligence/HUNT_PLAN.md`; preserve the V9 slot assignment/provenance unless an explicit higher-priority experiment need overrides it.
- Check coverage/saturation/adjacency/measurement reports, but quotas never override technical or commercial value.
- Deduplicate by repository + exact revision + capability.
- Verify source/tests/schema/history beyond README. Label IMPLEMENTED / TESTED / CLAIMED / EXPERIMENTAL / UNVERIFIED.
- Before important NO_FIND, run one recall-rescue pass without lowering the verification bar.
- PASS/VERIFIED must survive missing, stale, ambiguous, malformed, partial and source-unavailable states.
- Money/trust claims require authority origin, stable identity, governed transitions and independently observed outcome. UNKNOWN/REVIEW never creates realized dollars.
- Separate endpoint/subject behavior from the measurement harness/requester/evaluator; no candidate grades itself.
- A retained live/provider qualification is historical provenance unless it is bound to a machine-readable behavior subject/closure that still matches the deployed subject. Covered behavior expansion must withdraw qualification; provably out-of-closure changes may retain it. Do not demand rerunning live spend after every irrelevant commit, but do not inherit proof across unbounded scope expansion.
- Do not inspect or retain credentials, private/personal/confidential data, accidental secrets or unauthorized-access material.
- No padding. A no-new-finding run is preferable to another dominated repository.

## 1. Freight Recovery — P0 / EXP-001
**Bottleneck:** commercialization and deployment evidence, not another freight component.

**Do next:** clear the structured separate-environment launch gate, then obtain one explicitly authorized frozen buyer population and carry it through controlling authority -> independent expected charge -> blind incumbent comparison -> adjudication -> issued adjustment -> independently observed settlement -> unique allocation -> later reversal if any.

**Engineering checkpoint:** the known CSV pre-parser seam is materially hardened in `freight/input_guard.py`; v15.13 also adds a deterministic Engagement State Resolver over immutable Charter/Amendment chains. Treat these as internal technical controls, not external validation. Accepted-but-unreplaced amendments must resolve non-green (`SUSPENDED_PENDING_REPLACEMENT`); tampered/duplicate/dangling/cross-buyer/cyclic replacement state must fail closed.

**Stop:** generic freight audit/TMS/OCR/rating/EDI/reconciliation hunting. Resume external search only if the buyer population exposes one named capability/connector gap.

## 2. AP Leakage Assurance — P0 / EXP-002
**Bottleneck:** real ERP/provider negative authority after the synthetic reversible-authority contract passed.

The ERP-neutral ledger now passes 12/12 cases and 60/60 across five stability replays, covering source-health states, identity blockers, exact quantity/money conservation, counter-events, atomic reverse capacity, crash-after-target-commit recovery, UNKNOWN, replay expiry, explicit negative receipts, zombie fencing and bitemporal replay.

**Highest-value next action:** bind that passing reference to one real vendor-credit/reversal endpoint and require a phase-qualified `ProviderOutcomeReceipt`. Only an effect-scoped provider state proving that posting/apply never began may release capacity for a fresh mutation; generic Failed, NotFound, timeout or partial-processing states remain UNKNOWN.

**Stop:** generic OCR/RPA/three-way-match/anomaly tools and more synthetic ledger design until the external adapter is exercised.

## 3. Partner / Commission Payout Assurance — P0/P1 / EXP-003
**Bottleneck:** independent real provider/bank observation after the historical-authority fixture passed.

The synthetic corpus now passes 24/24 baseline classifications, kills all six unsafe mutants, avoids double-send in 200 two-writer races and passes 9/9 late-return cases. It reopens the exact original earning once, preserves historical settlement, repays at the original 10,000-cent authority after policy changes to 13,000, and keeps ambiguous/not-found/partial/unavailable/wrong-payout evidence non-mutating. Clawback-not-owed revokes settlement without reopening owed.

**Highest-value next action:** suppress the real reversal webhook after a completed payout, require independent provider/bank or payroll readback to discover the late return, then reproduce the exact-original-rate, exactly-once reopen. Synthetic success is not external finality evidence.

**Stop:** commission calculators, payout wrappers and fuzzy statement matchers.

## 4. ScopeSignal / Construction — P0/P1 / EXP-005
**Bottleneck:** independently approved measurement -> exact commercial line -> one-time bill consumption -> scoped provenance-bound counter-event -> independent cash.

Use PMIS for agreement-BOQ/rate/cumulative/certification authority; Nirman for approved-measurement transition; Site-Tracker-Pro as the green-CI negative control. Fast-Vben is a useful positive pattern for scoped source-effect uniqueness and one reversal per prior effect; OpenConstructionERP is a negative control where `transaction_ref`/idempotency can omit project scope.

**Mandatory adversaries:** sequential replay after commit; direct-table/API/RLS bypass; wrong contractor; wrong bill period; same-project/wrong-line evidence; evidence linked after approval; negative/NaN/Inf values; same human transaction reference in two projects; reversal idempotency key without project/tenant scope; duplicate source-version/effect; second reversal; wrong project/tenant; nonexistent prior event; exact prior ID without scope/FK integrity; internal `PAID/Reconciled` vs independent settlement.

**Stop:** generic pay-app/RA-bill CRUD, takeoff/diff and internal payment labels until this corpus runs.

## 5. Recovery Proof — P0/P1 / EXP-004
**Bottleneck:** one real exact-source **and exact-runtime** qualified recovery artifact.

Treat recovery coverage as four governed planes: **OBSERVATIONS -> IDENTITY AUTHORITY -> SCOPE -> PROOF**. Preserve raw observations; contradictory fresh hard identities remain non-merge states.

A five-case synthetic qualification-transfer fixture passed 5/5 and established a two-layer identity: behavior-bearing **source closure** plus **resolved execution closure** covering runner image/OS, exact action SHAs, toolchain/runtime versions, container digests and downloaded-tool hashes. Source equality alone cannot prove what executed.

Run the existing authority/admission, expected-subject, semantic, proof-sink, cleanup and broken-verifier negatives plus: exact revision without E2E receipt, older green replayed as current, harness failure vs subject failure, exact source with unresolved runtime, moved action tag, changed runner/toolchain, moved container tag and missing/mismatched checksum. `UNQUALIFIED`, `HARNESS_FAILED` and `RECOVERY_FAILED` remain distinct and non-PROVEN.

**Do next:** materialize one real exact-source + resolved-runtime FireDrill-style artifact and make only the coherent case PROVEN. The current FireDrill head remains `NO_CURRENT_QUALIFICATION`.

**Stop:** broad inventory/recovery/OTA/attestation search until this matrix runs.

## 6. CaptureBrief — P0/P1 / EXP-006
**Bottleneck:** lossless packet/history authority plus independently sourced current-action authority, not another SAM wrapper.

Live fixtures prove both historical attachment loss and temporal-authority divergence. `W50S8B-26-Q-A016` shows same filename/different `resourceId` and historical resources omitted from the latest deletion-inclusive manifest. `FA524026Q0041` shows a complete bulk/mirror action set can still select the wrong current action because the bulk schema lacks an authoritative currentness primitive.

**Do next:** carry three independent receipts: `HISTORY_SET_RECEIPT`, `CURRENT_ACTION_RECEIPT`, and `ACTION_ORDER_RECEIPT`. Repeat across the frozen families, especially same-day revisions. Shuffle same-day bulk rows as a negative; any current-selection result that changes under row permutation is deriving authority from non-authoritative order. Current packet completeness runs only after first-party currentness is resolved.

**Stop:** generic SAM/FAR dashboards. Search only successor/deviation authority or a concrete history/currentness-loss gap.

## 7. Installed-Base Lab / Sequencing — P1 / EXP-007
**Bottlenecks:** (1) repair and replay the now-falsified Thermo metadata path; (2) durable physical-action receipt under pre-confirmation ambiguity.

The rights-clean Thermo comparison is complete, not NOT_RUN. OpenTFRaw 1.4.1 and the pinned comparator agreed exactly on all 9,942,753 centroid m/z/intensity pairs across 18,420 spectra, but OpenTFRaw disagreed on MS level for 15,838 spectra, polarity for 15,877, precursor semantics across essentially the full relevant set, and observed-range CV terms for all 18,186 nonempty spectra. The row is **peak-array PASS / acquisition-metadata DISAGREE**.

**Normalization next action:** patch/rebuild event metadata lookup from scan ordinal `idx` to `entry.scan_event`, replay the exact frozen file/hash and require MS-level/polarity/precursor errors to fall to zero or remain explicit. Separately repair observed-range terms and add oracle-backed regressions. Entab is a third adjudicator only for residual disagreement.

For physical actions, execute the SiLA/Opentrons kill/restart matrix with a real persistent provider; missing local receipt remains UNKNOWN.

**Stop:** broad lab/orchestrator/converter discovery until the patched replay and physical ambiguity test run.

## 8. Insurance Subrogation — P1 / EXP-011
Search only authoritative versioned jurisdiction/policy rules, precedence, limitations/fault effective periods and closed-claim settlement evidence. Missing/conflicting/superseded authority = REVIEW / $0. Stop generic claims AI/demand-letter tooling.

## 9. Money-State Integrity / Payments — P1 / EXP-010
**Bottleneck:** intersection of fault-boundary proof, revocable finality and economic terminality in one executable path.

Keep three axes separate: fault boundary; provider/accounting/bank terminality; and later revocation/counter-event. Interlock, effect-broker, Familiarise, Flames-up and Paymob each cover different parts; none proves the whole intersection with independent bank observation.

**Do next:** post-effect process death -> new-process same-effect recovery -> no duplicate -> provider terminal success -> provider-accounting application -> later post-success return -> original obligation reopened without re-pricing -> independent processor/bank finality/readback. Suppress the webhook in one case to test long-tail independent observation.

## 10. Revenue Decision Assurance — P1/P2
Search only held-out replay adapters, real capacity/censoring/no-show/cancellation state, incumbent decision logs and realized revenue/load outcomes. Decision score, evaluator and buyer outcome remain separate. Stop recommendation-only analytics and model-valued ROI.

## 11. Industrial Virtual Commissioning — P1 / EXP-008
**Bottleneck:** real neutral-HSMS execution after correcting the secsgem prediction.

The prior secsgem second-value-wins/partial-mutation prediction is withdrawn. Pinned source validates the full S2F15 batch before mutation, and five existing plus two planted all-or-nothing tests passed 7/7.

Execute two frozen hypotheses with a neutral raw-HSMS requester: **EC-ATOMIC-SHARED** expects duplicate/invalid input rejection with no mutation from both endpoints; **EC-DUPLICATE-POLICY** compares Dreamine malformed/S9 response semantics with secsgem EAC while independently asserting unchanged state. Record every correlated message, independent logical T3 and post-state. Native clients remain a separate compatibility matrix.

**Stop:** third SECS/GEM engine until an actually observed endpoint disagreement needs adjudication.

## 12. Permit / Public-Data Intelligence — P1 / EXP-009
Use source topology + immutable versions + CAP-019 observation receipts + reviewed identity. Freeze three-jurisdiction source-field truth. Search only source-completeness/semantic/identity/version gaps that change a buyer decision. Stop mutable-upsert lead maps.

## 13. Grid / Infrastructure — P1/P2 / EXP-012
**Bottleneck:** evaluator-byte provenance and independence.

Mendeley DOI `10.17632/r4csg2h2ps.1` supplies one exact outer witness package but not the embedded USECPO source hash. Obtain and compare first-party OEDI bytes/digest, then freeze composite event identity, unique county-spell grain and the spell↔event bridge before scoring policy outcomes.

**Stop:** more outage datasets unless a genuinely independent rights-clear oracle remains necessary.

## 14. Independent verification / adjacency / measurement debt
Use the remaining slot on the highest information-value task: independent falsification, external-outcome evidence, measurement debt, or adjacency that closes a named seam. Do not spend it on a familiar saturated family because it is easy to search.

## Current stop list
- Generic freight systems, reconciliation engines, OCR/rating components.
- Generic AP matchers/OCR/RPA before EXP-002.
- Generic commission calculators/statement parsers.
- Generic backup frameworks, broad CMDB matching and more OTA/attestation frameworks before EXP-004.
- Generic construction pay-app/reversal CRUD before EXP-005 scoped counter-event corpus.
- Generic SAM/FAR wrappers before EXP-006.
- Broad lab frameworks and chromatography converters before EXP-007 bounded tests.
- Third SECS/GEM implementation before EXP-008 execution.
- More outage datasets before EXP-012 artifact provenance closes.

## Integrator next bottleneck
The portfolio still has **$0 directly evidenced customer value and $0 directly evidenced revenue**. The highest-value external step remains Freight EXP-001: verified separate environment + one authorized frozen buyer population + one uniquely attributable incumbent miss + actual credit/refund/remittance. Technical work elsewhere should continue only when it makes one of the active experiments cheaper, safer or more falsifiable.

<!-- INTEGRATOR-R15-2026-09-20T2100-0400 -->
## Integrator queue delta — 2026-09-20 21:00 ET
1. **P0 Freight external validation:** treat v15.13 Engagement State Resolver as internal hardening only. Verify the separate environment, freeze one authorized buyer population, and push one challenger-only finding through adjudication and actual settlement. No more generic freight hunting.
2. **P1 CaptureBrief currentness:** use three independent receipts—history set, current action, and action ordering. Run same-day-row permutation negatives and compare against first-party latest-active/current assertions before packet completeness.
3. **P1 Lab Thermo repair:** the dual decode is complete and exposed severe acquisition-metadata disagreement despite exact peak-array agreement. Patch/rebuild the scan-event lookup, replay the frozen fixture, repair observed-range terms and use Entab only for residual adjudication.
4. **P1 ScopeSignal scoped reversal:** execute cross-project transaction-ref/idempotency collisions, duplicate source versions, wrong-tenant reversals and FK/scope negatives. No capacity reopening unless prior-event identity, tenant/project scope, source version, uniqueness and correction authority all agree.
5. **P1 Recovery:** execute the exact-revision qualification + authority/admission matrix rather than find another recovery or attestation framework.
6. **No benchmark policy change:** no benchmark-path commit since the previous scored checkpoint; Pair 1 Experiment remains empty. Preserve SCOREBOARD and SEARCH_SKILLS and do not claim Experiment superiority.

<!-- INTEGRATOR-R15-2026-09-20T2224-0400 -->
## Integrator queue delta — 2026-09-20 22:24 ET
1. **P0 AP / money writeback — phase-qualified negative proof:** upgrade the remaining EXP-002 question from generic “can we prove NOT_APPLIED?” to a typed `ProviderOutcomeReceipt` carrying exact operation identity, provider phase, effect scope, partial-effect possibility, provenance and `APPLIED | NOT_APPLIED | UNKNOWN`. Dynamics `PreProcessingError` and SAP pre-posting cancellation/rejection are strong provider-issued negative-proof exemplars; generic `Failed`, `ProcessedWithErrors`, `PostProcessingFailed`, `PartiallySucceeded`, timeout or ambiguous `Canceled` remain UNKNOWN until effect-level reconciliation. Search next for one real vendor-credit/reversal endpoint whose terminal state proves the exact mutation never entered posting/apply.
2. **P0/P1 safe retry after idempotency expiry:** retain `mathd/ticketing_system@d787b289330ffc8265a5a68382e7e45d510a2ecf` as a 26/30 conclusive-provider-absence component. A fresh money mutation is licensed only after provider query scope, cursor progression, structural completeness, own-vs-foreign identity and bounded termination establish a complete no-match; malformed/truncated/non-progress/bound-exhausted search is UNKNOWN/no-POST. This strengthens effect-broker but does not replace real-provider process-kill or bank-finality proof.
3. **P1 Lab Thermo role correction:** `chromConverter@ddf959...` does not itself pin the actual Thermo decoder: it shells to an externally installed ThermoRawFileParser. Current ThermoRawFileParser v2 depends on separately governed Thermo RawFileReader and has moved to .NET 8 while chromConverter's non-Windows launcher still assumes Mono. Treat `OpenTFRaw@63380...` as the preferred rights-clean default production candidate; ThermoRawFileParser is a technically strong comparator/reference only where its separate vendor rights are cleared. Every EXP-007 receipt must bind the external decoder artifact/version/hash, not just the wrapper SHA. The `Lee_CB_03.raw` dual-decoder row is now peak-array PASS / acquisition-metadata DISAGREE; exact decoder artifact provenance remains mandatory.
4. **P1 Grid evaluator negative:** `Resilient-Supply-Chain/open-supply-chain-control-tower@d0691e25...` is an active downstream USECPO consumer whose notebook groups flat event-correlated rows by `(start_date, county)` and sums them. Treat this as a real implementation of the aggregation hazard, not as an oracle. EXP-012 should explicitly replay that transform against the canonical unique county-spell fact table and require the naive flat-row result to be rejected or quantified as divergent. First-party OEDI archive/member digest identity remains a separate gate.
5. **P2 scientific campaign durability:** `openmm/openmm@5a7a268...` is a useful WATCH reference for recent safer checkpoint/restart hardening, but per-file temp+rename and object-reconstruction tests do not prove multi-artifact crash consistency. If reused as a reliability analogue, require one generation manifest/group-commit receipt and crash injection between log/checkpoint writes; do not call rename-without-fsync power-loss durable.
6. **Benchmark update supersedes the 21:00 note:** Pair 1 Experiment Task 01 is now complete and scored **24/25** versus Control **25/25**. Overall matched tasks are **43**; Experiment mean **24.67** vs Control **24.58**, median paired difference **0**, Experiment task W/T/L **8/29/6**, false promotions **0/0**, no-finds **0/1**, and Experiment remains more search-intensive. Do not declare an Experiment win. The new Task-01 bidirectional money/evidence invariant lesson has only one-task support and is not eligible for SEARCH_SKILLS promotion yet.
7. **Portfolio priority unchanged:** Freight EXP-001 remains the highest-value external bottleneck because the portfolio still has no directly evidenced buyer value/revenue. These technical deltas should shorten/falsify active experiments, not trigger another product launch or broad search family.