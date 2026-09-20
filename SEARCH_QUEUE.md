# SEARCH_QUEUE

Integrator-owned search and validation direction. Updated 2026-09-20. **Experiment bottlenecks, independent falsification, source authority and outcome evidence outrank repository count.** This file is current direction, not history; older run-specific overrides remain in Git history and hunter catalogs.

## Operating rules for all 14 workstreams
- When a retained strong/MASTER root deserves expansion, use `intelligence/ADJACENCY_QUEUE.md` to choose a bounded neighbor hypothesis. Record the `ADJ:` ID/type/root in V6 telemetry. Adjacency never overrides a domain STOP gate and social/code proximity is not evidence.
- Start from `intelligence/SEARCH_SEEDS.md` when a ranked seed matches an authorized active gap. Treat seeds as hypotheses, not authority. Record the `seed_id` in V5 telemetry. Deliberate wildcard exploration remains allowed with `seed_mode: free_exploration`.
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
**New evidence:** `raahul2701/nirman@9b860bf5...` contains an unusually relevant DB-side `consume_billable_measurement` transition: exact measurement row lock, approval provenance, BOQ/project lock, cumulative quantity ceiling, BOQ-derived rate, bill-item insertion and audit event. Red-team inspection still blocks promotion because row locking does not make the measurement one-time consumable, direct bill-item mutation appears to remain possible, contractor selection can be project-level/ambiguous, bill-period authority is not enforced, and the hardening migration references authority schema not proven reproducible from the inspected migration chain. `jbhp9fysxx-droid/construction-billing-verification-engine@3fb551a8...` is useful as a narrow independent BOQ/RA-bill comparator but synthetic falsification showed negative and NaN quantities can pass its current float-based checks.

**Do next:** extend the Nirman↔`construction_management` authority corpus with `ROW_LOCK_WITHOUT_CONSUMED_IDENTITY__SEQUENTIAL_REPLAY`, `SECURE_RPC_EXISTS__DIRECT_TABLE_INSERT_BYPASS`, `MULTI_CONTRACTOR_PROJECT__LIMIT_ONE_AMBIGUITY`, `MEASUREMENT_OUTSIDE_BILL_PERIOD__NO_PERIOD_GATE`, `MIGRATION_REPLAY__AUTHORITY_COLUMN_MISSING`, `GOOD_SERVICE_PATH__GENERIC_CRUD_BYPASS`, and explicit negative/NaN/Inf quantity-money cases. Preserve the existing wrong work-order ownership, over-measurement, draft/rejected/approved measurement, concurrent claim, retention, internal-payment-vs-cleared-cash and later-reversal cases.

**Authority rule:** `SELECT ... FOR UPDATE` is concurrency control, not consumed identity; a correct trusted RPC is not authoritative while an equivalent API/table/RLS/serializer mutation path bypasses it; project identity is not exact commercial-line authority; bill-number text is not period authority; float parsing is not valid economic-domain validation.

**Search only:** a reference that binds independently approved measurement to exact contract/work-order line and bill period, atomically makes that evidence unconsumable after one accepted claim, forces every equivalent mutation path through the invariant, and survives clean-migration/sequential-replay tests; plus independent cleared-cash/reversal evidence. **Stop:** generic pay-app/RA-bill CRUD, takeoff/diff and internal `PAID/Reconciled` labels.

## 5. Recovery Proof — P0/P1 / EXP-004
**New evidence:** `kirilurbonas/FireDrill@1e532b17...` proves that expected subject/workload inventory must be external to the evidence directory or a vanished drill can disappear from evaluation. `jorgedlcruz/open-backup-ui@d3956a4b...` independently demonstrates the missing census primitive by reconciling live infrastructure inventory against protected backup objects. `DanMrxs/danlab-vps-backup-control@6b071acd...` adds versioned inventory/manifests with explicit considered-vs-backed-up sets. `OmarRao/r3vp@404f7f7...` is a negative oracle for protected-set-derived inventory, and `NHSDigital/terraform-aws-backup@e0dbc8b...` shows scope-selector drift can corrupt compliance coverage. FireDrill's multi-engine isolated restores, semantic checks, RTO/RPO, signed DSSE evidence and scoped gates remain strong proof-plane evidence; `snapetech/DuneAwakeningSelfHost@8d3bac1...` adds PostgreSQL+RabbitMQ/Mnesia recovery and `WiseOpsTeam/mneme@e595986...` remains a process-exit-as-semantic-proof negative oracle.

**Coverage authority contract:** define the denominator through three separately versioned planes: `CENSUS` = independently observed workloads with stable IDs, source revision, collected-at/freshness and tombstone/disappearance history; `SCOPE` = in/out-of-scope, criticality, RPO/RTO, owner, exclusion reason and expiry; `PROOF` = restore evidence for every resulting expected subject. The protected/evidence set may never define its own denominator, and a heartbeat is not inventory-snapshot freshness.

**Do next:** add `protected_set_used_as_census`, `inventory_snapshot_stale`, `subject_disappears_without_retirement_tombstone` and `scope_selector_semantics_mismatch` to the existing `expected_subject_missing_entirely`, `control_aggregate_masks_failed_workload`, wrong-semantic-value-despite-rc=0, proof-sink failure, cleanup failure and deliberately broken verifier matrix. PASS requires per-subject coverage against a frozen/fresh CENSUS+SCOPE snapshot before restore proof is considered complete.

**Search only:** multi-source inventory reconciliation with stable identity, last-seen/tombstones, versioned exclusions/scope and independently verifiable snapshot provenance if this matrix exposes a missing authority component. **Stop:** broad backup/restore tooling and any design that computes coverage over only the protected/evidence set.

## 6. CaptureBrief / Government acquisition intelligence — P0/P1 / EXP-006
Official GSA semantics establish a deletion/history boundary: `excludeDeleted`/`deleteAll` mean a latest manifest cannot reconstruct complete attachment history. `chrisfulcher/orrery@89ae2218...` remains useful but is now a **26/30 component**, not complete history authority, because it does not pin deletion-inclusive reads and its successful recheck path does not create a lossless disappearance ledger.

**Do next:** on 10 frozen solicitation families maintain separate planes for notice/action history, deletion-inclusive per-action attachment observations, immutable artifact hashes, FAR/supplement/deviation authority and entity/award lineage. Every observation must preserve action/notice identity, exact URL/query semantics, observed time, status, body hash, parser/schema version and completeness. New observations never delete old evidence; source failure cannot emit disappearance.

**Search only:** successor/deviation authority, historical attachment losslessness, tombstone/deleteAll semantics and concrete source-currentness gaps. **Stop:** generic SAM/FAR wrappers and procurement dashboards.

## 7. Installed-Base Lab / Sequencing Operations — P1 / EXP-007
**New evidence:** `AD-SDL/MADSci@6b1ab6a...` safely handles the immediate lost-response branch: one action ID is retained, the manager queries that same action, repeated readback failure becomes `UNKNOWN`, and the workflow fails instead of advancing. Official `Opentrons/opentrons@03b991fb263b97b6bb767ce311ca56e103d635e4` now supplies the stronger external device/server reconciliation plane: stable vendor `run_id`, persisted run/action/command state and integration tests through Robot Server restart. The red-team boundaries matter more than the feature count: MADSci generic retry can mint a fresh action ID, while Opentrons `RunActionCreate` has no client idempotency/action ID and the run controller initiates play/resume before persisting the action record. Therefore a persisted run/action/status can establish **APPLIED** more strongly, but missing action history cannot by itself establish **NOT_APPLIED / SAFE_TO_REISSUE**.

**Do next:** finish the Clarity -> independent sample-sheet validation -> run identity -> Illumina InterOp -> provenance handoff, then execute an exact three-seam ambiguity matrix against the pinned Opentrons Robot Server: (1) request demonstrably never reaches play; (2) play/effect begins but response is lost; (3) server/process dies after effect initiation but before action persistence. Preserve orchestration attempt ID + vendor `run_id` across restart. PASS requires APPLIED -> no reissue, UNKNOWN -> downstream/retry blocked, and one linked replacement only after independent NOT_APPLIED evidence. After the dev-server fixture, use a customer-authorized non-destructive OT-2/Flex action if available.

**Stop:** broad lab orchestrator/device discovery until this fixture runs. `AD-SDL/ot2_module` and `RoryMB/simlab` are harnesses, not recovery authority. Command-mutated local state is not independent physical verification; action-record absence is not no-effect proof; a standards facade alone is not safe production control.

## 8. Insurance Subrogation Recovery — P1 / EXP-011
Search only authoritative versioned jurisdiction/policy rules, policy-language precedence, limitations/fault effective periods and closed-claim settlement evidence. Unknown/missing/conflicting/superseded rule or unresolved policy wording = **REVIEW / $0 asserted recovery**. Stop generic claims AI/demand-letter tooling.

## 9. Money-State Integrity / Payments — P1 / EXP-010
`NotAbdelrahmanelsayed/paymob_integration@8999a679...` remains the strongest reversal-safe provider reference: timeout/5xx remains Pending; lost webhook is recovered by provider inquiry; refund request is one-shot under ambiguity; only confirmed signed refund delta posts a compensating ERP entry; cumulative mismatches route to review. `az-said/Interlock@822ec54692b30e1fdce04b55dfab62d0b56a60b2` adds a rare higher evidence tier on the provider-accounting side: Stripe test-mode worker SIGKILL after a real credit effect, genuinely new-process recovery, exactly one approved customer-balance credit, and later one-time application of that credit to a paid renewal invoice reducing amount due by exactly $10. Its published careful handwritten baseline ties the money outcome, so treat Interlock as recovery/evidence packaging, not proof of unique economic superiority. Provider-accounting application still is **not bank/payout settlement**.

**Do next:** canonical month with duplicate charge, lost webhook, unknown result, literal post-effect process death, transport-level response loss, refund-response loss, cumulative refund without child proof, partial/full refund, outbox failure, provider-native accounting application and later independent bank return/chargeback. Reproduce the Interlock after-send/application fixture independently or author an equivalent golden; then extend past provider accounting to independent processor/bank finality. A later external counter-event must reopen/offset canonical state while preserving original authority.

Provider qualification harnesses count only with a retained successful exact-revision provider artifact; checked-in self-authored test evidence remains technical evidence, not customer outcome. `NOT_EXERCISED` remains unqualified. Stop generic payment cores.

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
4. EXP-004 Recovery Proof CENSUS+SCOPE authority + expected-subject/broken-verifier/proof-sink matrix.
5. EXP-005 ScopeSignal one-use measurement authority + alternate-path/sequential-replay + independent cash/reversal.
6. EXP-003 commission provider -> bank/payroll finality and later-return matrix.
7. EXP-010 money-state process-death/provider-application/bank-finality month.
8. EXP-008 industrial duplicate-S2F15 differential.
9. EXP-007 Opentrons run-ID / side-effect-before-action-persistence ambiguity matrix plus sequencing handoff.
10. EXP-012 USECPO artifact-byte gate and event-level benchmark.

**Portfolio rule:** repository discovery resumes only when one of these experiments exposes a concrete missing capability, authority source, comparator or outcome edge.