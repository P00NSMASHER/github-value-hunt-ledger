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
**Bottleneck:** reversible authority consumption plus crash-safe external writeback.

Build `ReceiptAuthorityPolicy` + CAP-019 source receipts + exact line-level quantity/amount conservation + Nomenklatura/Canon identity + MiniGraf replay. Add `prathamesh-git9/effect-broker@eb273640...` downstream of the accounting reservation: stable operation identity, durable reservation before I/O, `OUTCOME_UNKNOWN`, lease recovery, authoritative APPLIED/NOT_APPLIED readback and fenced stale workers.

**Highest-value search question:** can a real ERP-facing adapter prove **NOT_APPLIED** conservatively after response loss/process death, without treating an eventually consistent “not found yet” as retry authority?

**Stop:** generic OCR/RPA/three-way-match/anomaly tools until the corpus exposes a missing semantic.

## 3. Partner / Commission Payout Assurance — P0/P1 / EXP-003
**Bottleneck:** independent late-return observation after a payout already reached the success state.

`Practitionist/familiarise_web@020975116ef438fa6269e12abb52de6ad9299781` is the strongest single-system reference for the middle of the chain: payment-time effective rate authority -> persisted earning/share -> one-use payout claim -> provider `COMPLETED` -> externally delivered `payout.reversed` -> exact provider-payout lookup -> compensating journal -> PAID earning reopened to READY -> future rebatch from the original stored earning rather than current policy.

The remaining gap is observation redundancy/finality: Familiarise's ordinary poller covers PENDING/PROCESSING, so a permanently lost post-COMPLETED reversal webhook is not independently rediscovered. Keep Modern Treasury + ACHInterbank as bank/return mapping comparators and Layr-Labs as an external provider counter-event comparator.

**Highest-value search/test:** change the rate after earning creation, complete the payout, observe a later reversal, require exact same earning to reopen, ignore duplicate reversal, and prove re-payment equals the original earning amount. Then suppress the reversal webhook entirely and require an independent provider/bank readback to discover the same late return and drive the same idempotent reopen.

**Negative oracle:** any reversal path whose predicate selects only SCHEDULED/PENDING/`payout_pending` after the success path has moved the obligation to PAID/COMPLETED cannot implement revocable finality.

**Stop:** commission calculators, payout wrappers and fuzzy statement matchers. Search only post-success return observation/correlation, independent finality or a concrete failed fixture.

## 4. ScopeSignal / Construction — P0/P1 / EXP-005
**Bottleneck:** independently approved measurement -> exact commercial line -> one-time bill consumption -> scoped provenance-bound counter-event -> independent cash.

Use PMIS for agreement-BOQ/rate/cumulative/certification authority; Nirman for approved-measurement transition; Site-Tracker-Pro as the green-CI negative control. Fast-Vben is a useful positive pattern for scoped source-effect uniqueness and one reversal per prior effect; OpenConstructionERP is a negative control where `transaction_ref`/idempotency can omit project scope.

**Mandatory adversaries:** sequential replay after commit; direct-table/API/RLS bypass; wrong contractor; wrong bill period; same-project/wrong-line evidence; evidence linked after approval; negative/NaN/Inf values; same human transaction reference in two projects; reversal idempotency key without project/tenant scope; duplicate source-version/effect; second reversal; wrong project/tenant; nonexistent prior event; exact prior ID without scope/FK integrity; internal `PAID/Reconciled` vs independent settlement.

**Stop:** generic pay-app/RA-bill CRUD, takeoff/diff and internal payment labels until this corpus runs.

## 5. Recovery Proof — P0/P1 / EXP-004
**Bottleneck:** independently authoritative denominator, identity-correct census, versioned proof-policy currentness, typed proof admission, exact-revision qualification and verifier self-test.

Treat recovery coverage as four governed planes: **OBSERVATIONS -> IDENTITY AUTHORITY -> SCOPE -> PROOF**. Preserve raw cloud/control-plane, endpoint/EDR and scanner/network observations immutably; canonical workload identity is a revisable interpretation. A contradictory concurrently fresh strong identifier is a hard non-merge state, not another weighted feature.

**Mandatory identity corpus before signing the denominator:** hard-ID conflict, agent rotation, weak-only ambiguity, duplicate hard-ID authority, source outage/partial collection. Require durable `MATCHED`, `AMBIGUOUS_REVIEW`, `IDENTITY_CONFLICT`, `SOURCE_DISAGREEMENT`, and `UNOBSERVED/PARTIAL` states.

Bind the proof decision to the CAP-007 versioned authority envelope and require an exact-revision Recovery Qualification Receipt. Run the eight authority/admission negatives plus `exact_revision_without_e2e_receipt`, `older_green_e2e_replayed_as_current`, `harness_setup_failed_before_subject`, and `subject_failure_after_harness_ready`. `UNQUALIFIED`, `HARNESS_FAILED`, and `RECOVERY_FAILED` are distinct and all non-PROVEN.

Then run missing expected subject, stale inventory, silent disappearance, scope-selector mismatch, aggregate-mask, service-up/data-wrong, rc=0/wrong-value, proof-sink failure, cleanup failure and deliberately broken verifier across PostgreSQL plus one dual-plane workload.

**Do next:** one exact-revision-qualified artifact should become PROVEN under one fresh coherent authority bundle while every planted authority, qualification and semantic failure remains non-green for the intended reason.

**Stop:** broad asset-inventory/CMDB/recovery/OTA/attestation search until this matrix runs.

## 6. CaptureBrief — P0/P1 / EXP-006
**Bottleneck:** lossless packet/history authority plus independently sourced current-action authority, not another SAM wrapper.

Live fixtures prove both historical attachment loss and temporal-authority divergence. `W50S8B-26-Q-A016` shows same filename/different `resourceId` and historical resources omitted from the latest deletion-inclusive manifest. `FA524026Q0041` shows a complete bulk/mirror action set can still select the wrong current action because the bulk schema lacks an authoritative currentness primitive.

**Do next:** carry three independent receipts: `HISTORY_SET_RECEIPT`, `CURRENT_ACTION_RECEIPT`, and `ACTION_ORDER_RECEIPT`. Repeat across the frozen families, especially same-day revisions. Shuffle same-day bulk rows as a negative; any current-selection result that changes under row permutation is deriving authority from non-authoritative order. Current packet completeness runs only after first-party currentness is resolved.

**Stop:** generic SAM/FAR dashboards. Search only successor/deviation authority or a concrete history/currentness-loss gap.

## 7. Installed-Base Lab / Sequencing — P1 / EXP-007
**Bottlenecks:** (1) multi-vendor data-normalization acceptance on a rights-clean corpus; (2) durable external execution receipt under pre-confirmation ambiguity with a real persistent provider.

For CAP-013, retain `ethanbass/chromConverter@ddf959bb71a595357a3f4028be48afd006a78714` as the normalization component and use `Sigilweaver/OpenTFRaw@63380dff0d25898f5c6e1184087dc590b0d7b6ab` as the preferred independent Thermo RAW decoder oracle because its inspected path directly decodes RAW bytes rather than wrapping the same vendor decoder lineage. Entab is a third challenger, not the sole oracle.

**Normalization test:** execute CC0 `MSV000094032/raw/Lee_CB_03.raw` through the pinned production Thermo decoder and OpenTFRaw **before any shared normalization**. Freeze source hash and both revisions; compare predeclared scan count, RT, MS order, filter strings, centroid m/z/intensity or invariant aggregates, TIC/BPC and precursor/isolation fields where both support the semantic. Classify each field `PASS | DISAGREE | UNSUPPORTED | ORACLE_UNAVAILABLE`. XSD-valid mzML and one real-file CI fixture are structural evidence, not full scientific equivalence. Stop converter discovery until this runs.

For physical actions, MADSci/SiLA still has pre-confirmation ambiguity and Opentrons still has side-effect-before-action-persistence risk. Execute the seven-branch restart/rebind matrix with a real persistent provider; missing local action/receipt is never NOT_APPLIED.

**Stop:** broad lab-device/orchestrator and chromatography-converter discovery until both bounded tests run.

## 8. Insurance Subrogation — P1 / EXP-011
Search only authoritative versioned jurisdiction/policy rules, precedence, limitations/fault effective periods and closed-claim settlement evidence. Missing/conflicting/superseded authority = REVIEW / $0. Stop generic claims AI/demand-letter tooling.

## 9. Money-State Integrity / Payments — P1 / EXP-010
**Bottleneck:** intersection of fault-boundary proof, revocable finality and economic terminality in one executable path.

Keep three axes separate: fault boundary; provider/accounting/bank terminality; and later revocation/counter-event. Interlock, effect-broker, Familiarise, Flames-up and Paymob each cover different parts; none proves the whole intersection with independent bank observation.

**Do next:** post-effect process death -> new-process same-effect recovery -> no duplicate -> provider terminal success -> provider-accounting application -> later post-success return -> original obligation reopened without re-pricing -> independent processor/bank finality/readback. Suppress the webhook in one case to test long-tail independent observation.

## 10. Revenue Decision Assurance — P1/P2
Search only held-out replay adapters, real capacity/censoring/no-show/cancellation state, incumbent decision logs and realized revenue/load outcomes. Decision score, evaluator and buyer outcome remain separate. Stop recommendation-only analytics and model-valued ROI.

## 11. Industrial Virtual Commissioning — P1 / EXP-008
**Bottleneck:** independent measurement of endpoint behavior.

Execute duplicate-ECID S2F15 with a neutral raw-HSMS requester. Record every correlated wire message, maintain an independent logical T3 clock and read EC post-state. Run native Dreamine and secsgem requesters separately as host-policy comparators.

**Stop:** third SECS/GEM engine until an actually executed endpoint disagreement needs adjudication.

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
3. **P1 Lab Thermo oracle:** run `Lee_CB_03.raw` through production Thermo decoder versus `OpenTFRaw@63380...` before normalization; keep Entab as a third challenger. Do not mistake shared decoder lineage, schema-valid mzML, or one-file CI for independent scientific equivalence.
4. **P1 ScopeSignal scoped reversal:** execute cross-project transaction-ref/idempotency collisions, duplicate source versions, wrong-tenant reversals and FK/scope negatives. No capacity reopening unless prior-event identity, tenant/project scope, source version, uniqueness and correction authority all agree.
5. **P1 Recovery:** execute the exact-revision qualification + authority/admission matrix rather than find another recovery or attestation framework.
6. **No benchmark policy change:** no benchmark-path commit since the previous scored checkpoint; Pair 1 Experiment remains empty. Preserve SCOREBOARD and SEARCH_SKILLS and do not claim Experiment superiority.

<!-- INTEGRATOR-R15-2026-09-20T2224-0400 -->
## Integrator queue delta — 2026-09-20 22:24 ET
1. **P0 AP / money writeback — phase-qualified negative proof:** upgrade the remaining EXP-002 question from generic “can we prove NOT_APPLIED?” to a typed `ProviderOutcomeReceipt` carrying exact operation identity, provider phase, effect scope, partial-effect possibility, provenance and `APPLIED | NOT_APPLIED | UNKNOWN`. Dynamics `PreProcessingError` and SAP pre-posting cancellation/rejection are strong provider-issued negative-proof exemplars; generic `Failed`, `ProcessedWithErrors`, `PostProcessingFailed`, `PartiallySucceeded`, timeout or ambiguous `Canceled` remain UNKNOWN until effect-level reconciliation. Search next for one real vendor-credit/reversal endpoint whose terminal state proves the exact mutation never entered posting/apply.
2. **P0/P1 safe retry after idempotency expiry:** retain `mathd/ticketing_system@d787b289330ffc8265a5a68382e7e45d510a2ecf` as a 26/30 conclusive-provider-absence component. A fresh money mutation is licensed only after provider query scope, cursor progression, structural completeness, own-vs-foreign identity and bounded termination establish a complete no-match; malformed/truncated/non-progress/bound-exhausted search is UNKNOWN/no-POST. This strengthens effect-broker but does not replace real-provider process-kill or bank-finality proof.
3. **P1 Lab Thermo role correction:** `chromConverter@ddf959...` does not itself pin the actual Thermo decoder: it shells to an externally installed ThermoRawFileParser. Current ThermoRawFileParser v2 depends on separately governed Thermo RawFileReader and has moved to .NET 8 while chromConverter's non-Windows launcher still assumes Mono. Treat `OpenTFRaw@63380...` as the preferred rights-clean default production candidate; ThermoRawFileParser is a technically strong comparator/reference only where its separate vendor rights are cleared. Every EXP-007 receipt must bind the external decoder artifact/version/hash, not just the wrapper SHA. The `Lee_CB_03.raw` dual-decoder row remains NOT_RUN.
4. **P1 Grid evaluator negative:** `Resilient-Supply-Chain/open-supply-chain-control-tower@d0691e25...` is an active downstream USECPO consumer whose notebook groups flat event-correlated rows by `(start_date, county)` and sums them. Treat this as a real implementation of the aggregation hazard, not as an oracle. EXP-012 should explicitly replay that transform against the canonical unique county-spell fact table and require the naive flat-row result to be rejected or quantified as divergent. First-party OEDI archive/member digest identity remains a separate gate.
5. **P2 scientific campaign durability:** `openmm/openmm@5a7a268...` is a useful WATCH reference for recent safer checkpoint/restart hardening, but per-file temp+rename and object-reconstruction tests do not prove multi-artifact crash consistency. If reused as a reliability analogue, require one generation manifest/group-commit receipt and crash injection between log/checkpoint writes; do not call rename-without-fsync power-loss durable.
6. **Benchmark update supersedes the 21:00 note:** Pair 1 Experiment Task 01 is now complete and scored **24/25** versus Control **25/25**. Overall matched tasks are **43**; Experiment mean **24.67** vs Control **24.58**, median paired difference **0**, Experiment task W/T/L **8/29/6**, false promotions **0/0**, no-finds **0/1**, and Experiment remains more search-intensive. Do not declare an Experiment win. The new Task-01 bidirectional money/evidence invariant lesson has only one-task support and is not eligible for SEARCH_SKILLS promotion yet.
7. **Portfolio priority unchanged:** Freight EXP-001 remains the highest-value external bottleneck because the portfolio still has no directly evidenced buyer value/revenue. These technical deltas should shorten/falsify active experiments, not trigger another product launch or broad search family.