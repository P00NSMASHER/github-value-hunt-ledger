# SEARCH_QUEUE

Integrator-owned search and validation direction. Updated 2026-09-20. **Experiment bottlenecks, independent falsification, source authority and outcome evidence outrank repository count.** This file is current direction, not history; older overrides remain in Git history and hunter catalogs.

## Operating rules for all 14 workstreams
- Check `intelligence/DISPATCH_BACKPRESSURE.md` before claiming. Primary V15 tickets soft-stale after 75 minutes and hard-expire after 150 minutes. Never claim a hard-expired primary ticket; use `WORK_STEAL_QUEUE.md` only after expiry. Work-steal runs are measured separately and do not train V13 primary-routing quality.
- Before claiming routed work, use `intelligence/DISPATCH_BOARD.md` / `dispatch_claim_packets.jsonl`. A generated claim must carry the current `DISPATCH:` ticket exactly. Claiming a different slot is allowed only as an explicit `manual_override` with a reason, and that override must not train the generated-route learner.
- Review `intelligence/ROUTING_LEARNING_REPORT.md` before interpreting worker specialization. V13 trains only from completed MATCHED generated routes and remains observe-only until its evidence thresholds are met; manual reroutes and retrospective repairs do not train it.
- Check `intelligence/WORKER_ROUTING.md` before claiming work. If a worker has a generated V12 route, claim that routed slot; active V11 claims remain locked. Manual reroutes must be explicit and should be recorded as routing overrides rather than silently training the router.
- Claim work through `intelligence/EXECUTION_BOARD.md` / `execution_events/SLOT-XX.jsonl` before executing it. One worker may hold one live claim by default. Heartbeat before lease expiry. Write schema-v11 telemetry first, then append COMPLETE with that exact run ID; completion without matched telemetry is invalid.
- Review `intelligence/ALLOCATOR_LEARNING_REPORT.md` before coordinated cycles. V10 may move at most one slot among experiment/coverage/adjacency after sufficient attributed evidence; measurement, verification and wildcard remain protected. Manual overrides must be explicit and do not train the automatic portfolio learner. **Current report has 0 attributed assignment runs and no role with sufficient evidence, so no portfolio-capacity shift is justified yet.**
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

**Engineering checkpoint:** the known CSV pre-parser seam is now materially hardened in `freight/input_guard.py`: explicit field/row/cells-per-row/total-cell bounds, streaming logical-row inspection, non-materializing physical-line inspection and typed `csv_parse_error` rejection were added, followed by adversarial tests for each bound. Treat this as **IMPLEMENTED + TEST-CODE PRESENT**, not external validation: no exact-commit CI status was available at integration time. Next internal step is execute the hostile-input suite in the real parser sandbox/CI and preserve the evidence receipt. This is not a search trigger.

**Stop:** generic freight audit/TMS/OCR/rating/EDI/reconciliation hunting. Resume external search only if the buyer population exposes one named capability/connector gap.

## 2. AP Leakage Assurance — P0 / EXP-002
**Bottleneck:** reversible authority consumption plus crash-safe external writeback.

Build `ReceiptAuthorityPolicy` + CAP-019 source receipts + exact line-level quantity/amount conservation + Nomenklatura/Canon identity + MiniGraf replay. Add `prathamesh-git9/effect-broker@eb273640...` downstream of the accounting reservation: stable operation identity, durable reservation before I/O, `OUTCOME_UNKNOWN`, lease recovery, authoritative APPLIED/NOT_APPLIED readback and fenced stale workers.

**Highest-value search question:** can a real ERP-facing adapter prove **NOT_APPLIED** conservatively after response loss/process death, without treating an eventually consistent “not found yet” as retry authority?

**Stop:** generic OCR/RPA/three-way-match/anomaly tools until the corpus exposes a missing semantic.

## 3. Partner / Commission Payout Assurance — P0/P1 / EXP-003
**Bottleneck:** independent late-return observation after a payout already reached the success state.

`Practitionist/familiarise_web@020975116ef438fa6269e12abb52de6ad9299781` is now the strongest single-system reference for the middle of the chain: payment-time effective rate authority -> persisted earning/share -> one-use payout claim -> provider `COMPLETED` -> externally delivered `payout.reversed` -> exact provider-payout lookup -> compensating journal -> PAID earning reopened to READY -> future rebatch from the original stored earning rather than current policy. This materially joins the prior EruoFood historical-authority and payout-reversal patterns.

The remaining gap is observation redundancy/finality: Familiarise's ordinary poller covers PENDING/PROCESSING, so a permanently lost post-COMPLETED reversal webhook is not independently rediscovered. Keep Modern Treasury + ACHInterbank as bank/return mapping comparators and Layr-Labs as an external provider counter-event comparator.

**Highest-value search/test:** change the rate after earning creation, complete the payout, observe a later reversal, require exact same earning to reopen, ignore duplicate reversal, and prove re-payment equals the original earning amount. Then suppress the reversal webhook entirely and require an independent provider/bank readback to discover the same late return and drive the same idempotent reopen.

**Negative oracle:** any reversal path whose predicate selects only SCHEDULED/PENDING/`payout_pending` after the success path has moved the obligation to PAID/COMPLETED cannot implement revocable finality.

**Stop:** commission calculators, payout wrappers and fuzzy statement matchers. Search only post-success return observation/correlation, independent finality or a concrete failed fixture.

## 4. ScopeSignal / Construction — P0/P1 / EXP-005
**Bottleneck:** independently approved measurement -> exact commercial line -> one-time bill consumption -> independent cash.

Use PMIS for agreement-BOQ/rate/cumulative/certification authority; Nirman for approved-measurement transition; Site-Tracker-Pro as the green-CI negative control.

**Mandatory adversaries:** sequential replay after commit; direct-table/API/RLS bypass; wrong contractor; wrong bill period; same-project/wrong-line evidence; evidence linked after approval; negative/NaN/Inf economic values; internal `PAID/Reconciled` vs independent settlement.

**Stop:** generic pay-app/RA-bill CRUD, takeoff/diff and internal payment labels.

## 5. Recovery Proof — P0/P1 / EXP-004
**Bottleneck:** independently authoritative denominator, identity-correct census, versioned proof-policy currentness, typed proof admission and verifier self-test.

Treat recovery coverage as four governed planes: **OBSERVATIONS -> IDENTITY AUTHORITY -> SCOPE -> PROOF**. Preserve raw cloud/control-plane, endpoint/EDR and scanner/network observations immutably; canonical workload identity is a revisable interpretation. A contradictory concurrently fresh strong identifier is a hard non-merge state, not another weighted feature. Hostname/IP/MAC evidence may propose a relationship but may not overrule conflicting cloud instance/agent/device authority.

**Mandatory identity corpus before signing the expected-subject denominator:** same hostname + same public IP + different fresh cloud instance IDs => `IDENTITY_CONFLICT`; same cloud instance + rotated EDR agent => allowed relationship with rotation history; weak-only hostname/scanner evidence => `AMBIGUOUS_REVIEW`; two canonicals claiming the same hard ID => duplicate-authority conflict; source outage/partial collection => `UNOBSERVED/PARTIAL` and non-green denominator. Require durable terminal states such as `MATCHED`, `AMBIGUOUS_REVIEW`, `IDENTITY_CONFLICT`, `SOURCE_DISAGREEMENT`, and `UNOBSERVED/PARTIAL` before scope publication.

Bind the resulting proof decision to a **versioned authority envelope**. Use `foundriesio/aktualizr-lite@1d089b006295cd924b3c87337679fef7295e4329` and `uptane/aktualizr@e5118a74874c0561ebac57560c667c18b19d984b` as cross-domain currentness/rollback oracles only. Add `carabiner-dev/ampel@5cf19bc2786cbd73a8423383a966fbf842222d23` as a proof-admission accelerator for signer binding, policy expiry, explicit PASS/FAIL/SKIP and signed result output; add `in-toto/in-toto@e352b43ad7cb8915d84c36d791aa61346152a0a3` for authorized-functionary thresholds/artifact agreement. Preserve Sigstore's recurring signed-but-wrong-predicate failure class as a defensive negative oracle and require current exact predicate/type checks. None of these defines recovery-policy substance.

**Mandatory proof-admission negatives:** `tampered_policy_metadata`; `expired_policy_metadata`; `policy_version_rollback`; `snapshot_mix`; `wrong_authority_role`; `wrong_predicate_type`; `threshold_shortfall`; `skip_exit_zero`. A cryptographically valid evidence object is non-green when policy is stale/mixed, the signer role is wrong, the requested evidence type is absent, threshold is incomplete or semantic result is SKIP—even if the wrapper process exits successfully.

Then run missing expected subject, stale inventory, silent disappearance, scope-selector mismatch, aggregate-mask, service-up/data-wrong, rc=0/wrong-value, proof-sink failure, cleanup failure and deliberately broken verifier across PostgreSQL plus one dual-plane workload.

**Do next:** wrap one actual EXP-004 restore-proof artifact in the integrated admission matrix. One fresh coherent correct bundle should become PROVEN; all eight negatives must fail for the intended reason. Durable publication should emit a current in-toto SVR v0.2-style summary carrying exact policy ResourceDescriptors/digests and point to the deeper signed proof bundle. `SVR/VSA` is a summary/index, not replacement evidence.

**Search only:** exact stable-identity conflict handling, collector-run completeness/provenance, tombstones/exclusions or a concrete proof-admission/currentness gap exposed by the matrix. Do not search another generic attestation/update framework before the integrated test.

**Stop:** broad asset-inventory/CMDB/recovery-framework or OTA/update-framework search. First-match, confidence-only, “highest score wins” identity logic, signature-only currentness, process-exit-as-PASS and signed-but-wrong-type evidence are negative-control material, not denominator/proof authority.

## 6. CaptureBrief — P0/P1 / EXP-006
**Bottleneck:** lossless packet/history authority, not another SAM wrapper.

Live SAM fixture `W50S8B-26-Q-A016` proved: same filename can mean different `resourceId`; latest deletion-inclusive manifest can omit a resource still recoverable from historical action manifests; historical action endpoints can expose later tombstone state. Therefore preserve action membership and observation-time state separately.

**Do next:** repeat the historical-action-union test across the remaining nine frozen families. Record `union(all successful historical action manifests) - latest`, same-name/different-ID replacements, retroactive tombstones, restricted/offsite resources and source-failure cases. Maintain append-only local observation snapshots regardless of what old endpoints return later.

**Stop:** generic SAM/FAR dashboards. Search only successor/deviation authority or a concrete history-loss gap.

## 7. Installed-Base Lab / Sequencing — P1 / EXP-007
**Bottlenecks:** (1) multi-vendor data-normalization acceptance on a rights-clean corpus; (2) durable external execution receipt under pre-confirmation ambiguity with a real persistent provider, not a dry-run adapter.

For CAP-013, use `ethanbass/chromConverter@ddf959bb71a595357a3f4028be48afd006a78714` as the strongest new normalization component. It supplies registry-driven Agilent/Shimadzu/Waters/Thermo/Varian/open-format dispatch, canonical source-hash/parser provenance, open-format writers and fixture-backed numerical/metadata comparisons. Its recent CI archaeology is valuable because prior green CI silently skipped meaningful Entab/netCDF/Shimadzu paths before the workflow was hardened. Reverse-engineered format success is still fixture-scoped, not vendor certification.

**Normalization test:** freeze a customer-owned/rights-clean or synthetic golden corpus spanning Agilent, Shimadzu, Waters and Thermo; pin parser/runtime revision; retain raw bytes/hash; emit normalized object/open format + provenance; independently compare a stratified subset against vendor/open exports; require measurement-value and minimum metadata/provenance preservation; unsupported versions/disagreement = explicit blocker. Stop broad chromatography-converter discovery until this corpus runs.

For physical actions, current MADSci SiLA path does not make client `action_id` equal the server-assigned CommandExecutionUUID; correlation is in memory only after the SDK call returns. `trieu04/lab-in-the-loop@80eb9524a4a36178b35810a7999cd95e8394d4fc` proves that a strong orchestration contract can still be a false positive operationally: it durably prepares intent, models `AMBIGUOUS/RECONCILING/BLOCKED` and reconciles by idempotency key before resubmit, yet its only installed lab provider is explicitly memory-only dry run and real mode is rejected. `MolBioFreak/BioModStack@9b36a0b106cd538d772de39092c1d532ad361083` supplies a conceptual provider-queryable stable request-key/command/receipt complement, but the combined crash-persistent real-provider join is NOT proven.

Current `sila2` 0.14.0 documentation exposes `ClientObservableCommandInstance(..., execution_uuid, lifetime_of_execution=...)`, so a **client-only restart** is a concrete rebind test when the CommandExecutionUUID was durably captured and the same server execution lifetime remains authoritative. Official SiLA semantics make `ServerUUID` stable across server lifetimes while CommandExecutionUUID is lifetime-scoped; same ServerUUID after server restart therefore does not make an old command receipt valid.

**Execute seven branches plus provider-binding check:** provably not accepted => `SAFE_TO_REISSUE`; accepted/effect may have started but confirmation lost => `RECONCILIATION_REQUIRED`; confirmation received but client dies before durable receipt => `RECONCILIATION_REQUIRED`; durable receipt + positive same-operation readback => `CONFIRMED_APPLIED`; durable receipt + bounded authoritative NOT_APPLIED => `SAFE_TO_REISSUE`; client process restart with valid persisted receipt/server lifetime => reconstruct/query the same operation, no redispatch; server restart or execution-lifetime expiry => `RECONCILIATION_REQUIRED`; and real provider mode must actually be installed/persistent rather than memory-only dry run.

Persist at minimum `(client_intent_id, intent_hash, server_uuid, feature_fqi, command_identifier, command_execution_uuid, lifetime_of_execution, receipt_received_at, receipt_durable_at, client_runtime_version, sila_runtime_version, reconciliation_state, last_authoritative_readback_at)`. Pin the exact SiLA/runtime and adapter factory during acceptance.

Use `auths-dev/auths-proof@34fa1f33...` only as a transfer oracle for the alternative pattern “stable pre-dispatch business reference + provider-searchable metadata + idempotency + read-only reconciliation”; require equivalent device/server semantics before transferring it.

**Stop:** broad lab-device/orchestrator and chromatography-converter discovery until both bounded tests run. Stable endpoint/server identity is not operation identity; an abstract reconciliation API is not provider evidence.

## 8. Insurance Subrogation — P1 / EXP-011
Search only authoritative versioned jurisdiction/policy rules, precedence, limitations/fault effective periods and closed-claim settlement evidence. Missing/conflicting/superseded authority = REVIEW / $0. Stop generic claims AI/demand-letter tooling.

## 9. Money-State Integrity / Payments — P1 / EXP-010
**Bottleneck:** intersection of fault-boundary proof, revocable finality and economic terminality in one executable path.

Keep three axes separate:
- Fault axis: response suppression -> process death/restart -> same-effect/no duplicate.
- Economic axis: provider object -> provider final state -> provider accounting application -> payout/balance -> independent bank/processor observation.
- Revocation axis: previously successful economic effect -> later externally observed return/reversal -> compensating entry -> original obligation reopened under original authority -> safe re-close.

Interlock strongly covers crash+provider-accounting application; effect-broker covers general crash/reconciliation; Familiarise now covers event-time authority + post-success provider reversal + reopened original earning; Flames-up covers provider payout terminality; Paymob covers provider ambiguity/refund child evidence. None alone proves the full intersection with independent bank observation.

**Do next:** one path with post-effect process death -> new-process same-effect recovery -> no duplicate -> provider terminal success -> provider/accounting application -> later post-success return -> original obligation reopened without re-pricing -> independent processor/bank finality/readback. Suppress the webhook in one case to test whether long-tail independent observation can discover the counter-event.

## 10. Revenue Decision Assurance — P1/P2
Search only held-out replay adapters, real capacity/censoring/no-show/cancellation state, incumbent decision logs and realized revenue/load outcomes. Decision score, evaluator and buyer outcome remain separate. Stop recommendation-only analytics and model-valued ROI.

## 11. Industrial Virtual Commissioning — P1 / EXP-008
**Bottleneck:** independent measurement of endpoint behavior.

Execute duplicate-ECID S2F15 with a neutral raw-HSMS requester. Record every correlated wire message, classify EXPECTED_SECONDARY/F0/STREAM9/OTHER/none, maintain an independent logical T3 clock, and read EC post-state. Run native Dreamine and secsgem requesters separately as host-policy comparators.

**Stop:** third SECS/GEM engine until an actually executed endpoint disagreement needs adjudication. Same System Bytes is correlation evidence, not sufficient proof of expected transaction completion.

## 12. Permit / Public-Data Intelligence — P1 / EXP-009
Use source topology + immutable versions + CAP-019 observation receipts + reviewed identity. Freeze three-jurisdiction source-field truth. Search only source-completeness/semantic/identity/version gaps that change a buyer decision. Stop mutable-upsert lead maps.

## 13. Grid / Infrastructure — P1/P2 / EXP-012
**Bottleneck:** evaluator-byte provenance and independence.

Mendeley DOI `10.17632/r4csg2h2ps.1` supplies one exact 12,980,662-byte outer witness package under two byte-identical aliases, SHA-256 `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`. That hash is **not** the embedded USECPO source hash.

**Do next:** in a binary-capable runtime verify the outer package, extract only the source/download manifest, read the exact USECPO URL/release/size/SHA row, and compare it with first-party OEDI bytes or a first-party digest. Keep UNKNOWN/MISMATCH hard-fail. Then freeze whole-event 2019–2023 splits.

**Stop:** more outage datasets unless a genuinely independent rights-clear oracle remains necessary.

## 14. Independent verification / adjacency / measurement debt
Use the V9 allocator to spend the remaining slot on whichever has the highest current information value:
1. independent falsification of one active experiment claim;
2. external-outcome evidence for a high-ranked opportunity;
3. measurement debt that prevents deciding whether a search strategy actually works;
4. adjacency only where it closes a named capability seam.

Do not spend the wildcard slot on a familiar saturated family solely because it is easy to search.

## Current stop list
- Generic freight systems, reconciliation engines, OCR/rating components.
- Generic AP matchers/OCR/RPA before EXP-002.
- Generic commission calculators/statement parsers.
- Generic backup frameworks, broad CMDB/asset-inventory matching and additional OTA/update/attestation frameworks before the EXP-004 identity/coverage/currentness/typed-admission matrix.
- Generic construction pay-app CRUD before EXP-005.
- Generic SAM/FAR wrappers before EXP-006.
- Broad lab frameworks and chromatography-converter hunting before EXP-007 bounded tests.
- Third SECS/GEM implementation before EXP-008 execution.
- More outage datasets before EXP-012 artifact provenance closes.

## Integrator next bottleneck
The portfolio still has **$0 directly evidenced customer value and $0 directly evidenced revenue**. The highest-value external step remains Freight EXP-001: verified separate environment + one authorized frozen buyer population + one uniquely attributable incumbent miss + actual credit/refund/remittance. Technical work elsewhere should continue only when it makes one of the active experiments cheaper, safer or more falsifiable.

<!-- INTEGRATOR-R13-2026-09-20T1900-0400 -->
## Integrator queue delta — 2026-09-20 19:00 ET
1. **P0 Freight pilot gate + external validation:** first harden the Pilot Charter so `KICKOFF_AUTHORIZED` requires strict JSON types and a current authority-bound launch-decision receipt; then stop internal freight discovery and run one explicitly authorized frozen buyer population to actual settlement evidence.
2. **P1 Grid EXP-012 correctness:** obtain/hash the current first-party OEDI artifact; if byte identity is established, freeze composite event identity + unique county-spell grain + event bridge before any historical scoring. Do not run the old bare-`event_id` evaluator.
3. **P1 AP EXP-002 provider semantics:** establish authoritative QBO `requestid` retention/expiry and a conservative VendorCredit negative-readback contract; run the process-restart same-request-ID fixture. Do not hunt generic idempotency libraries.
4. **P1 Payout EXP-010:** join terminal provider scanning to one vertical historical earning/payable by exact payout ID and classify still-owed vs clawback before reopen/re-pay. Do not count generic pending-state polling as finality assurance.
5. **P1 ScopeSignal EXP-005:** execute immutable-evidence mutation corpus before another RA-bill search. Require accepted bill -> immutable measurement version edge and explicit correction/counter-event.
6. **P1 CAP-009 workforce authority:** combine PayrollEngine-style effective/knowledge-time selection with RosterSpec verification/repair on a frozen historical rule bundle. Do not treat static compliance settings as authority.
7. **P2 Protocol pre-FAT:** execute the existing USP/SECS differential fixtures with neutral measurement before discovering a fourth implementation. Caretaker is a negative-control endpoint until runtime evidence exists.
8. **P2 CaptureBrief EXP-006:** keep `VERIFIED_ACTION_MEMBERSHIP / semantic_identity / byte_state` separate; move to the next frozen solicitation family rather than repeatedly guessing routes for the same unavailable historical object.
