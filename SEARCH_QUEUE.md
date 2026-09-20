# SEARCH_QUEUE

Integrator-owned search and validation direction. Updated 2026-09-20. **Experiment bottlenecks, independent falsification, source authority and outcome evidence outrank repository count.** This file is current direction, not history; older run-specific overrides remain in Git history and hunter catalogs.

## Operating rules for all 14 workstreams
- Deduplicate by **repository + exact revision + capability**.
- Record actual public rights/provenance; use the user's separate commercial-permission assertion only for repository-owned public code/content. Third-party datasets, standards, patents, trademarks, APIs/services, customer records and bundled assets remain separately governed.
- Verify beyond README using source/tests/schemas/config/history; label IMPLEMENTED / TESTED / CLAIMED / EXPERIMENTAL / UNVERIFIED.
- Never inspect, retain, test or exploit credentials, authentication material, private/personal/confidential data, accidental secrets, unauthorized-access material or leaked trade secrets.
- Before important NO_FIND, use one recall-rescue pass (old name/family/oracle fixture/author-org/commit lineage) without lowering the verification bar.
- PASS/VERIFIED must survive missing, stale, ambiguous, malformed, partial, selection-fallback and source-unavailable states. Exceptions are not empty-success.
- Trace decision claims **dispatch -> executable implementation -> meaningful side effect -> semantic test**.
- Money/trust claims require authority origin, unique identity, governed transitions and independently observed outcome; rejected/unknown evidence never re-enters totals.
- Effective-dated rules must pin authority, event/effective time, supersession and load-bearing thresholds/exceptions.
- No padding. No-new-find runs are acceptable.

## 1. Freight Recovery — P0 / EXP-001
**State:** internal settlement semantics and persistence are no longer the bottleneck. The 210/812/820 planted corpus passed exact/unique allocation, reviewed partial/split edges, duplicates, full reversal, ambiguous partial reversal, currency/pre-authority negatives and 2,000 fuzz ledgers. Persistent reference storage now adds integer-cents one-use allocation, immutable event/claim lineage, append-only reversal, SQL capacity guards and serialized concurrent writes; hunter verification reports 21/21 persistence tests plus 200 repeated two-writer races with exactly one realized allocation and passing CI.

**Do next:** obtain one explicitly authorized frozen buyer population and carry it through controlling authority -> independent expected charge -> blind incumbent comparison -> adjudication -> issued adjustment -> independently observed settlement -> unique allocation -> later reversal if any.

**Search only:** if that external population exposes a named contract/amendment/source-format/correction/rebill/settlement gap. **Stop:** generic freight audit/TMS/OCR/rating/EDI/reconciliation hunting. Discrepancy, dispute, issued credit or provider status remains **$0 realized** until independent settlement allocation exists.

## 2. AP Leakage Assurance — P0 / EXP-002
**New direction:** build a reversible authority-consumption ledger, not another matcher.

Use `ReceiptAuthorityPolicy(system, PO-line type, buyer config, supplier override, verification mode)` with `GoodsReceipt / ServiceEntrySheet / DirectInvoiceAllowed / REVIEW`; CAP-019 supplies `PRESENT / VERIFIED_EMPTY / UNAVAILABLE` source truth. Combine BCApps exact invoice↔PO↔receipt capacity semantics, ERPNext partial-receipt evidence, Odoo counter-events, MiniGraf bitemporal replay and Nomenklatura→Canon identity governance.

**Mandatory adversaries:** refunding vs non-refunding physical return; vendor credit; bill cancellation; re-receipt; multiple same-SKU PO lines; service/ordered-vs-received policy; UoM precision/rounding; source outage; identity reject/split/correction. Every counter-event must reference the original consumed authority edge and conserve amount+quantity. SKU equality/header state cannot establish ownership.

**Stop:** generic OCR/RPA/three-way-match/anomaly discovery until this corpus exposes a concrete missing semantic.

## 3. Partner / Commission Payout Assurance — P0/P1 / EXP-003
`Modern-Treasury/modern-treasury-python@406f354a...` supplies the strongest current bank-observation bridge; `szapata85/ACHInterbank@395a359...` supplies fail-closed unique/ambiguous/not-found return correlation.

**Do next:** execute a provider-neutral matrix where bank observation is `EXACT_UNIQUE / AMBIGUOUS / NOT_FOUND / UNAVAILABLE`. Only exact unique linkage inside a verified source window can establish a settlement candidate; later Return/Reversal revokes it. Plant duplicate trace, substring/fuzzy reference, equal-total/swapped identity, unparseable amount, stale cursor, provider-complete/bank-absent, bank-posted-then-returned and duplicate/ambiguous return cases.

**Stop:** commission calculators, payout wrappers, generic statement parsers and reconciliation libraries. Trace/reference/amount/first-match/cursor continuity are not finality proof.

## 4. ScopeSignal / Construction Change Leakage — P0/P1 / EXP-005
Run the Nirman↔`construction_management` adversarial authority corpus: wrong work-order ownership, over-measurement, draft/rejected/approved measurement, wrong period, concurrent quantity claim, retention error, internal Payment Entry/reconciliation vs independently cleared cash, later reversal.

**Search only:** signed/approved field-measurement authority, unbypassable certification-to-bill linkage, prime/sub flow-down/amendment authority and external cleared-cash/reversal evidence. **Stop:** generic pay-app/RA-bill CRUD, takeoff/diff and internal `PAID/Reconciled` labels.

## 5. Recovery Proof — P0/P1 / EXP-004
**New evidence:** `kirilurbonas/FireDrill@1e532b17...` proves a stronger pattern: expected workload/subject inventory must be external to the evidence directory or a vanished drill can disappear from evaluation. Its multi-engine isolated restores, semantic checks, RTO/RPO, signed DSSE evidence and scoped coverage gate are strong component evidence. `snapetech/DuneAwakeningSelfHost@8d3bac1...` adds a useful PostgreSQL+RabbitMQ/Mnesia dual-plane recovery pattern. `WiseOpsTeam/mneme@e595986...` is a negative oracle because SQL process success can be mistaken for semantic assertion success.

**Do next:** run per-workload expected-subject coverage with `expected_subject_missing_entirely`, `control_aggregate_masks_failed_workload`, wrong semantic value despite rc=0, proof-sink failure after successful restore, cleanup failure and deliberately broken verifier. Use a versioned/fresh expected inventory; unscoped evidence-directory discovery is forbidden for customer assurance.

**Stop:** broad backup/restore tooling. Search only if this matrix exposes a missing negative control or workload invariant.

## 6. CaptureBrief / Government acquisition intelligence — P0/P1 / EXP-006
Official GSA semantics establish a deletion/history boundary: `excludeDeleted`/`deleteAll` mean a latest manifest cannot reconstruct complete attachment history. `chrisfulcher/orrery@89ae2218...` remains useful but is now a **26/30 component**, not complete history authority, because it does not pin deletion-inclusive reads and its successful recheck path does not create a lossless disappearance ledger.

**Do next:** on 10 frozen solicitation families maintain separate planes for notice/action history, deletion-inclusive per-action attachment observations, immutable artifact hashes, FAR/supplement/deviation authority and entity/award lineage. Every observation must preserve action/notice identity, exact URL/query semantics, observed time, status, body hash, parser/schema version and completeness. New observations never delete old evidence; source failure cannot emit disappearance.

**Search only:** successor/deviation authority, historical attachment losslessness, tombstone/deleteAll semantics and concrete source-currentness gaps. **Stop:** generic SAM/FAR wrappers and procurement dashboards.

## 7. Installed-Base Lab / Sequencing Operations — P1 / EXP-007
**New evidence:** `AD-SDL/MADSci@6b1ab6a...` safely handles the immediate lost-response branch: one action ID is retained, the manager queries that same action, repeated readback failure becomes `UNKNOWN`, and the workflow fails instead of advancing. The red-team boundary is one layer later: the generic workflow retry surface can re-enqueue the failed step and create a fresh `ActionRequest`/ULID without mandatory physical-state reconciliation. Immediate fail-closed monitoring therefore does **not** prove system-wide exactly-once actuation.

**Do next:** finish the Clarity -> independent sample-sheet validation -> run identity -> Illumina InterOp -> provenance handoff, then fault-inject one physical action where the side effect occurs but the response is lost. PASS requires same-action/device-run readback, unresolved state = `UNKNOWN`, downstream work blocked, restart preserving the original identity, and retry/redispatch disabled until independent device/state reconciliation proves it safe. `AD-SDL/ot2_module` vendor `run_id` and `RoryMB/simlab` are useful test-harness surfaces, not proof of safe retry.

**Stop:** broad lab orchestrator/device discovery until this fixture runs. For any future device-standardization search, require a named installed family, real vendor/native actuation, behavioral/HITL regression, fault/recovery semantics and explicit single-actuation authority. Command-mutated local state is not independent physical verification, and a standards facade alone is not safe production control.

## 8. Insurance Subrogation Recovery — P1 / EXP-011
Search only authoritative versioned jurisdiction/policy rules, policy-language precedence, limitations/fault effective periods and closed-claim settlement evidence. Unknown/missing/conflicting/superseded rule or unresolved policy wording = **REVIEW / $0 asserted recovery**. Stop generic claims AI/demand-letter tooling.

## 9. Money-State Integrity / Payments — P1 / EXP-010
`NotAbdelrahmanelsayed/paymob_integration@8999a679...` is the strongest new reversal-safe provider reference: timeout/5xx remains Pending; lost webhook is recovered by provider inquiry; refund request is one-shot under ambiguity; only confirmed signed refund delta posts a compensating ERP entry; cumulative mismatches route to review. Combine with OpenPartner/Summae and independent bank observation.

**Do next:** canonical month with duplicate charge, lost webhook, unknown result, refund-response loss, cumulative refund without child proof, partial/full refund, outbox failure, later bank return/chargeback. A later external counter-event must reopen/offset canonical state while preserving original authority.

Provider qualification harnesses count only with a retained successful exact-revision provider artifact; `NOT_EXERCISED` remains unqualified. Stop generic payment cores.

## 10. Revenue Decision Assurance / Pricing-Yield — P1/P2
Search only held-out replay adapters, real capacity/censoring/no-show/cancellation state, incumbent decision logs and realized revenue/load outcomes. Every optimizer/abstention/information-acquisition mode must reach a changed operational action and semantic test. Stop recommendation-only analytics/model-valued ROI.

## 11. Industrial Virtual Commissioning / Protocol Acceptance — P1 / EXP-008
Execute the exact duplicate-ECID W-bit S2F15 probe against Dreamine.Gem and `bparzella/secsgem`. Current source/test-backed prediction, **not duplicate-specific runtime evidence**: Dreamine -> correlated S9F7 + unchanged EC state + eventual T3 timeout; secsgem -> S2F16 EAC=0 + last-value-wins. Record reply class, System Bytes/header, requester liveness/T3 and post-state.

Search a third engine only after the exact fixture executes and an actual disagreement needs adjudication. Implementation agreement is not formal SEMI conformance.

## 12. Permit / Public-Data Intelligence — P1 / EXP-009
Use source topology + immutable version/diff history + CAP-019 observation receipts + reviewed identity. Search only jurisdiction/semantic/identity/version gaps that change a buyer decision. Stop mutable-upsert scrapers and lead maps without completeness/freshness evidence.

## 13. Grid / Infrastructure Risk & Inspection — P1/P2 / EXP-012
USECPO v2 logical schema is now substantially frozen from its peer-reviewed descriptor: event-correlated files carry literal `event id`; whole-event splits must group by that key. `STANDARD / 8H / 24H` variants are sensitivity views, not independent evidence. Preserve EAGLE-I+DOE-417 ancestry, state-generalized geography and restoration imputation; use 2019–2023 first because early coverage is weaker. Do not call event correlation feeder/component causality or general distribution truth.

**Do next:** obtain the official v2 ZIP/guideline to byte-confirm headers, timezone, sentinels, thresholds and event-id namespace, then freeze event-level splits. **Stop:** more outage datasets/models unless a genuinely independent rights-clear historical oracle remains necessary.

## 14. Sparse-lane repair + wildcard analogs — P2
Only pursue adjacent domains reproducing the strongest portfolio DNA: **authoritative source/version -> deterministic expected state -> observed actual state -> governed review/action -> independent realized outcome -> counter-event/reversal**. Prefer old names, protocol/standard signatures, dependency/fork/commit archaeology and obscure internal-tool-style repositories over broad categories. After five weak measured runs, record the negative evidence and rotate.

## Global stop list
Do not spend capacity on generic OCR, CRUD, dashboards, RAG, fuzzy matching, commodity auth/RBAC, job queues, generic protocol clients, generic scheduling/routing/optimization demos, backup-status tools, generic TMS/CMMS/FSM/LIMS/AP OCR or speculative agents unless a candidate adds a **rare domain invariant, authoritative source, difficult installed-base integration, independently falsifiable algorithm, governed transition or realized-money/evidence loop** that materially beats the current portfolio.

## Current highest-value execution order
1. EXP-001 external authorized freight population.
2. EXP-002 AP source-health + reversible authority-consumption/counter-event corpus.
3. EXP-006 CaptureBrief action-history + deletion-inclusive manifest completeness.
4. EXP-004 Recovery Proof expected-subject coverage + broken-verifier/proof-sink matrix.
5. EXP-005 ScopeSignal measurement/contract authority -> bill -> independent cash/reversal.
6. EXP-003 commission provider -> bank/payroll finality and later-return matrix.
7. EXP-010 money-state refund/unknown/counter-event month.
8. EXP-008 industrial duplicate-S2F15 differential.
9. EXP-007 sequencing handoff + physical ambiguity negative.
10. EXP-012 USECPO artifact-byte gate and event-level benchmark.

**Portfolio rule:** repository discovery resumes only when one of these experiments exposes a concrete missing capability, authority source, comparator or outcome edge.