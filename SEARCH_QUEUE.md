# SEARCH_QUEUE

Integrator-owned search and validation direction. Updated 2026-09-20. **Experiment bottlenecks, independent falsification, source authority and outcome evidence outrank repository count.** This file is current direction, not history; older overrides remain in Git history and hunter catalogs.

## Operating rules for all 14 workstreams
- Review `intelligence/ROUTING_DECISION_AUDIT.md` before proposing routing experiments. Zero-criticality pairs are the safest future substitution candidates; V14 is evidence-only and does not itself reroute anyone.
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
**Bottleneck:** independently authoritative denominator, identity-correct census and verifier self-test.

Treat recovery coverage as four governed planes: **OBSERVATIONS -> IDENTITY AUTHORITY -> SCOPE -> PROOF**. Preserve raw cloud/control-plane, endpoint/EDR and scanner/network observations immutably; canonical workload identity is a revisable interpretation. A contradictory concurrently fresh strong identifier is a hard non-merge state, not another weighted feature. Hostname/IP/MAC evidence may propose a relationship but may not overrule conflicting cloud instance/agent/device authority.

**Mandatory identity corpus before signing the expected-subject denominator:** same hostname + same public IP + different fresh cloud instance IDs => `IDENTITY_CONFLICT`; same cloud instance + rotated EDR agent => allowed relationship with rotation history; weak-only hostname/scanner evidence => `AMBIGUOUS_REVIEW`; two canonicals claiming the same hard ID => duplicate-authority conflict; source outage/partial collection => `UNOBSERVED/PARTIAL` and non-green denominator. Require durable terminal states such as `MATCHED`, `AMBIGUOUS_REVIEW`, `IDENTITY_CONFLICT`, `SOURCE_DISAGREEMENT`, and `UNOBSERVED/PARTIAL` before scope publication.

Then run missing expected subject, stale inventory, silent disappearance, scope-selector mismatch, aggregate-mask, service-up/data-wrong, rc=0/wrong-value, proof-sink failure, cleanup failure and deliberately broken verifier across PostgreSQL plus one dual-plane workload.

**Search only:** exact stable-identity conflict handling, collector-run completeness/provenance, tombstones/exclusions or signed snapshot provenance if this matrix exposes a missing component. `apurvtyagi/security-asset-correlator@36aef11...` is a useful component/negative oracle because its weighted matcher can still merge contradictory hard IDs; `opsmill/infrahub-sync@76ab2b...` is useful collector provenance, not identity authority.

**Stop:** broad asset-inventory/CMDB/recovery-framework search. First-match, confidence-only or “highest score wins” identity logic is negative-control material, not denominator authority.

## 6. CaptureBrief — P0/P1 / EXP-006
**Bottleneck:** lossless packet/history authority, not another SAM wrapper.

Live SAM fixture `W50S8B-26-Q-A016` proved: same filename can mean different `resourceId`; latest deletion-inclusive manifest can omit a resource still recoverable from historical action manifests; historical action endpoints can expose later tombstone state. Therefore preserve action membership and observation-time state separately.

**Do next:** repeat the historical-action-union test across the remaining nine frozen families. Record `union(all successful historical action manifests) - latest`, same-name/different-ID replacements, retroactive tombstones, restricted/offsite resources and source-failure cases. Maintain append-only local observation snapshots regardless of what old endpoints return later.

**Stop:** generic SAM/FAR dashboards. Search only successor/deviation authority or a concrete history-loss gap.

## 7. Installed-Base Lab / Sequencing — P1 / EXP-007
**Bottleneck:** durable external execution receipt under pre-confirmation ambiguity, with client restart separated from server-lifetime restart.

Current MADSci SiLA path does not make client `action_id` equal the server-assigned CommandExecutionUUID; correlation is in memory only after the SDK call returns. Current `sila2` 0.14.0 documentation exposes `ClientObservableCommandInstance(..., execution_uuid, lifetime_of_execution=...)`, so a **client-only restart** is now a concrete rebind test when the CommandExecutionUUID was durably captured and the same server execution lifetime remains authoritative. Official SiLA semantics make `ServerUUID` stable across server lifetimes while CommandExecutionUUID is lifetime-scoped; same ServerUUID after server restart therefore does not make an old command receipt valid.

**Execute seven branches:** provably not accepted => `SAFE_TO_REISSUE`; accepted/effect may have started but confirmation lost => `RECONCILIATION_REQUIRED`; confirmation received but client dies before durable receipt => `RECONCILIATION_REQUIRED`; durable receipt + positive same-operation readback => `CONFIRMED_APPLIED`; durable receipt + bounded authoritative NOT_APPLIED => `SAFE_TO_REISSUE`; client process restart with valid persisted receipt/server lifetime => reconstruct/query the same operation, no redispatch; server restart or execution-lifetime expiry => `RECONCILIATION_REQUIRED`, never infer NOT_APPLIED.

Persist at minimum `(client_intent_id, intent_hash, server_uuid, feature_fqi, command_identifier, command_execution_uuid, lifetime_of_execution, receipt_received_at, receipt_durable_at, client_runtime_version, sila_runtime_version, reconciliation_state, last_authoritative_readback_at)`. Pin the exact SiLA runtime during acceptance; do not transfer semantics from legacy `sila2` to the actively maintained UniteLabs lineage without a fresh matrix.

Use `auths-dev/auths-proof@34fa1f33...` only as a transfer oracle for the alternative pattern “stable pre-dispatch business reference + provider-searchable metadata + idempotency + read-only reconciliation”; require equivalent device/server semantics before transferring it.

**Stop:** broad lab-device/orchestrator discovery until the real process-kill/rebind ambiguity matrix runs. Stable endpoint/server identity is not operation identity.

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
- Generic backup frameworks **and broad CMDB/asset-inventory matching** before the EXP-004 identity/coverage matrix.
- Generic construction pay-app CRUD before EXP-005.
- Generic SAM/FAR wrappers before EXP-006.
- Broad lab frameworks before EXP-007 ambiguity execution.
- Third SECS/GEM implementation before EXP-008 execution.
- More outage datasets before EXP-012 artifact provenance closes.

## Integrator next bottleneck
The portfolio still has **$0 directly evidenced customer value and $0 directly evidenced revenue**. The highest-value external step remains Freight EXP-001: verified separate environment + one authorized frozen buyer population + one uniquely attributable incumbent miss + actual credit/refund/remittance. Technical work elsewhere should continue only when it makes one of the active experiments cheaper, safer or more falsifiable.