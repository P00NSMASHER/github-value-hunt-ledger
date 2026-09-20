# EXPERIMENTS

Canonical stage-gate queue converting research into falsifiable technical/economic evidence. Repository quality is not an outcome; commercial validation exists only when a result is recorded in `OUTCOMES.md` with direct evidence.

## States
- READY — lawful/synthetic inputs available.
- BLOCKED_EXTERNAL — requires customer-authorized/external data or access.
- RUNNING — execution evidence is being produced.
- PASSED / FAILED / PARTIAL / INVALID — record under `OUTCOMES.md` when the experiment itself completes.
- SUPERSEDED — replaced by a better test.

## Priority queue — 2026-09-20

### EXP-001 — Freight blind audit to realized settlement
- Opportunity: Freight Recovery v15.3.
- Capabilities: CAP-001, 003, 004, 005, 006, 007.
- Status: **BLOCKED_EXTERNAL**.
- Hypothesis: on one buyer-authorized frozen population, the stack can find at least one unique incumbent-missed freight overcharge with zero unsupported dollars and carry it through actual externally observed settlement.
- Internal technical substage: **substantially exercised, not commercial validation.** The planted 210/812/820 settlement corpus now covers exact unique auto-allocation, reviewed partial/split edges, duplicate events, orphan/excess/wrong-currency/pre-authority cases, full reversal, ambiguous partial reversal and 2,000 deterministic fuzz ledgers. Remaining internal work is persistence/concurrency/security hardening only if defects are exposed.
- Required external inputs: fixed entity/BU/date/population; controlling contracts/rates/RateCons/addenda/tariff authority; shipment/operational evidence; sealed incumbent output; later credit/refund/remittance/bank evidence; documented customer authorization/retention/read-only boundaries.
- Procedure: readiness gate -> freeze/hash population -> freeze independent truth -> open/hash incumbent output -> score unique findings -> buyer adjudication -> authorized dispute/action -> independently observe settlement -> one-use allocation -> recovery certificate -> later counter-event/reversal if applicable.
- Success: unsupported asserted and realized dollars = 0; deterministic replay = 100%; every accepted finding has authority/expected/actual/evidence lineage; false-positive dollars within buyer ceiling; at least one challenger-only validated finding unless genuinely clean; `recovery proven` requires issued adjustment plus unambiguous external settlement allocation.
- Failure: truth circularity, population drift, unsupported authority/identity/evidence, duplicate/preexisting credit, ambiguous allocation counted as realized, returned money left fee-eligible, or false-positive dollars beyond ceiling.
- Next action: obtain one explicitly authorized closed population. Broad freight engineering/discovery remains frozen until that population exposes a named gap.

### EXP-002 — AP source-authority + receipt-policy leakage audit
- Opportunity: AP Leakage Assurance.
- Capabilities: CAP-002, 007, 008, 016, 019.
- Status: **READY**.
- Hypothesis: a governed identity plane plus explicit source observation and policy-specific receipt authority can distinguish recoverable AP leakage from unresolved exceptions without false missing-receipt/PO dollars.
- Inputs: synthetic closed month with duplicate invoices; alias/non-match/mistaken merge/split; partial receipts; mixed PO-level/direct billing; rejected quantity; service PO/SES required and legitimately not required; price/quantity/tax variance; credits; bitemporal corrections; source outage/partial load; later settlement.
- Authority model: `ReceiptAuthorityPolicy(system, PO-line type, buyer config, supplier override, verification mode)` resolving to evidence such as `GoodsReceipt`, `ServiceEntrySheet`, explicit `DirectInvoiceAllowed`, or REVIEW. Source health is separately `PRESENT / VERIFIED_EMPTY / UNAVAILABLE`.
- Procedure: source-observation receipt -> candidate identity -> durable POSITIVE/NEGATIVE/UNSURE judgement -> correction/split -> Canon promoted pinned registry -> policy-specific receipt authority -> PO/receipt/invoice matching -> proof gate -> outcome classification.
- Required regression cases: PO-line billed pool consumed once across multiple partial receipts; amount+quantity residual synchronization after mixed direct/PO-level billing; rejected-quantity denominator; service-entry-sheet variants; source failure not empty-success; corrected receipt after original decision.
- Success: all planted cases detected; unsupported recovery = 0; explicit non-match blocks later false merge; corrected identity and bitemporal state replay deterministically; unavailable source can never create missing-receipt/PO money.
- Failure: universal `has_receipt` assumption, source outage becomes negative evidence, ERP status copied as truth, silent identity resolution, or exception dollars labeled recovered.
- Next action: build one ERP-neutral corpus using ERPNext/Business Central/SAP-derived semantics as independent challengers, not authoritative customer truth.

### EXP-003 — Commission plan-to-bank acceptance test
- Opportunity: Partner / Commission Payout Assurance.
- Capabilities: CAP-002, 006, 007, 016, 018.
- Status: **READY**.
- Hypothesis: frozen plan/assignment/source-payment truth plus a provider-state machine and independent bank/payroll observation can detect entitlement and payout errors without duplicate-send or false-finality risk.
- Inputs: tiers/splits/overrides; plan/hierarchy changes; holds; refunds/clawbacks; carry-forward; partial payout; definite refusal; timeout/unknown; duplicate callback/retry; confirmed provider send; final FX amount/currency; forward ACH/network trace; later Return/Reversal; concurrent sweep races.
- Procedure: freeze authority -> calculate entitlement -> apply holds/reversals -> create one payout claim -> provider result -> independent settlement observation -> later return/reversal -> reconcile entitlement/intended/provider/settled as separate states.
- Success: deterministic expected payout; unknown provider result remains pending and cannot retry; definite refusal alone releases; duplicate paths cannot send twice; provider success and final settlement remain distinct; later return/reversal exactly unwinds finality.
- Failure: provider status establishes entitlement, unknown outcome releases claim, duplicate send, or finality lacks independent observation.
- Next action: execute provider-ID -> forward trace -> bank/payroll observation -> return/reversal matrix.

### EXP-004 — Recovery Proof adversarial + verifier-self-test matrix
- Opportunity: Recovery Proof SLA.
- Capabilities: CAP-007, 010.
- Status: **READY**.
- Hypothesis: the verifier can prove valid recovery, reject wrong-but-restorable state, and remain non-green when either the verifier or proof-delivery path is broken.
- Inputs: isolated PostgreSQL plus non-Postgres/object workload; wrong PITR target; missing history; corrupt object; service-up/data-wrong; stale proof; trust/revocation failure; total-host/credential-boundary case; deliberately mutated verifier/assertion helper; proof-sink outage after successful restore.
- Procedure: restore -> independently measure content/application/relationship invariants -> RTO/RPO -> trust validation -> persist proof -> inject negatives -> mutate verifier -> rerun.
- Success: every planted bad state fails for the intended reason; successful restore with unavailable proof sink remains overall non-green; mutated verifier cannot stay green; positives carry measured RTO/RPO and application truth.
- Failure: any planted wrong state, broken assertion path, stale trust state or missing proof persistence yields PASS.
- Next action: unify PostgreSQL and non-Postgres evidence schemas and execute the proof-sink + broken-verifier controls.

### EXP-005 — ScopeSignal authority-to-paid benchmark
- Opportunity: Construction Change Leakage Recovery.
- Capabilities: CAP-001, 006, 007.
- Status: **READY** synthetic; **BLOCKED_EXTERNAL** for commercial proof.
- Hypothesis: design/field changes can be traced through measurement, contract/work-order authority, notice, bill/certification, retention and independently cleared cash without inventing entitlement.
- Inputs: synthetic project with 20–50 changes; wrong work-order ownership; over-measurement; draft/rejected/approved measurement; wrong billing period; concurrent quantity claim; superseded baseline; retention error; Payment Entry/bank-reconciliation divergence; later reversal.
- Comparator pattern: Nirman approved-measurement-derived billing vs `mradul010/construction_management@ce345579...` server-reloaded work-order/PO quantity/rate bounds. Neither is accepted as complete truth by itself.
- Success: all unsupported/draft/rejected/over-limit states remain nonbillable/REVIEW; authoritative line ownership and cumulative quantity hold; internal `Approved/Paid/Reconciled` never substitutes for independent cleared-cash evidence.
- Failure: caller-entered quantity creates authority, internal accounting status is treated as bank finality, or design delta is treated as entitlement.
- Next action: run the cross-implementation adversarial corpus; search again only if a concrete unbypassable measurement/certification or cash-finality gap remains.

### EXP-006 — CaptureBrief 10-solicitation packet/authority benchmark
- Opportunity: CaptureBrief FAR-Deviation Readiness.
- Capabilities: CAP-002, 007, 011, 019.
- Status: **READY**.
- Hypothesis: separate deterministic planes for notice/version history, attachment state, immutable artifacts, current rule/deviation authority and entity/award lineage materially improve packet completeness and analyst trust over latest-row ingestion.
- Inputs: 10 current solicitations; official notice/action/history; attachment manifests; public attachments where access is authorized; FAR/supplement/deviation sources; entity/award IDs; source-run metadata; planted out-of-order/missing history, attachment disappearance/deletion and source-failure cases.
- Architecture: official SAM/Data Services for notice/action lineage; public SAM attachment-manifest state as a separate plane; immutable downloaded artifact hashes; deterministic history/event hydration; explicit source degradation. `chrisfulcher/orrery@89ae2218...` is a strong implementation reference for manifest/currentness and fail-closed shape drift, not sole authority.
- Success: exact packet completeness for the frozen rubric; correct amendment ordering; append-only/lossless manifest history or equivalent; byte/event-stable reruns; source failure cannot become no-change/no-record; correct current rule/deviation applicability; no false entity/incumbent joins.
- Failure: bulk/version history assumed attachment-complete, disappeared/deleted attachment silently lost, undocumented manifest shape yields clean empty result, stale authority applied, or confident unresolved join.
- Next action: freeze the 10-solicitation rubric and add historical manifest snapshots/diff rules before analyst scoring.

### EXP-007 — Installed-base sequencing/lab handoff acceptance
- Opportunity: Installed-Base Lab Automation.
- Capabilities: CAP-013, CAP-017 plus governance/provenance components.
- Status: **READY** for rights-clean synthetic tests.
- Hypothesis: a concrete Clarity -> sample-sheet/run identity -> InterOp -> provenance chain can improve workflow evidence without sequence-content/PHI dependence; standards facades over installed instruments are useful only when real actuation, acceptance and ownership are proven.
- Inputs: synthetic Clarity QC/pooling/run-prep state, generated sample sheet, lawful/public InterOp fixtures, stable run identity, invalid transition, missing/mismatched identity, missing metric artifact and run-metric exception.
- Success: deterministic workflow/run linkage, independent sample-sheet validation, rejection of mismatched identities/transitions, explicit unknowns and replayable provenance.
- Failure: wrong run joined, missing evidence turns green, sensitive reads/PHI become required, or a standards facade is mistaken for safe control without command arbitration/HITL evidence.
- Next action: build S4 Clarity + sample-sheet validator + InterOp synthetic handoff. LADS/CETONI remain WATCH until hardware-in-loop/regression and single-actuation authority are demonstrated.

### EXP-008 — Industrial virtual pre-FAT differential benchmark
- Opportunity: Industrial Pre-FAT / Virtual Commissioning.
- Capabilities: CAP-014.
- Status: **READY**.
- Hypothesis: customer/profile-derived virtual endpoints can catch binding/type/state/fault defects before hardware when independently differential-tested.
- Inputs: synthetic L5K/PLC namespace with planted drift; frozen SECS/GEM dialogue/error profile; Dreamine.Gem and unrelated `bparzella/secsgem` implementation; duplicate-event/EC atomicity probe.
- Success: all PLC defects detected; valid bindings preserved; every SECS/GEM disagreement classified as profile ambiguity, implementation defect or unresolved standards/vendor question; missing/error states cannot silently pass.
- Failure: same-family self-agreement used as proof, implementation agreement labeled formal conformance, or a disagreement is hidden by generic success.
- Next action: execute the frozen Dreamine <-> secsgem corpus before any third-engine search.

### EXP-009 — Permit intelligence multi-jurisdiction benchmark
- Opportunity: Permit-to-Development Opportunity Intelligence / PermitPlate.
- Capabilities: CAP-002, 012, 019.
- Status: **READY**.
- Hypothesis: canonical versioned permit events plus explicit source observation and parcel/economic context outperform raw lead lists on reliability/actionability.
- Inputs: three heterogeneous jurisdictions, 30–100 held-out permit events, source-run completeness/freshness metadata.
- Success: source completeness established; correct field semantics; stable identity/versioning; source outage never becomes verified-empty; useful buyer features carry source dates.
- Failure: semantic mapping errors, duplicate/version confusion, empty-success, unsupported economic inference.
- Next action: freeze source-field truth for three jurisdictions.

### EXP-010 — Money-state integrity common month
- Opportunity: Money-State Integrity / Close Assurance.
- Capabilities: CAP-006, 016.
- Status: **READY**.
- Hypothesis: a generalized operational-event -> accounting -> external-settlement boundary can underpin multiple assurance verticals.
- Inputs: synthetic month of contracts/orders/usage/invoices/credits/payments/journals with planted duplicates, reversals, outbox/webhook failures, unknown provider result, period-lock fault and later external return.
- Success: operational/accounting planes reconcile where correct; every planted disagreement is surfaced; external contract authority and PSP/bank readback can contradict the internal system.
- Failure: one system grades its own contract/payment state as external truth or vertical semantics become too lossy.
- Next action: run two independent implementations against one canonical event/money-state corpus before adding another payment/billing engine.

### EXP-011 — Subrogation rule-and-quantum fail-closed benchmark
- Opportunity: Insurance Subrogation Recovery Diagnostic.
- Capabilities: CAP-001, 006, 007.
- Status: **READY** synthetic; **BLOCKED_EXTERNAL** commercial.
- Hypothesis: recovery opportunities can be prioritized safely only when jurisdiction/policy authority is explicit, versioned and fail-closed.
- Inputs: synthetic paid-loss facts, comparative/contributory fault regimes, policy limits, made-whole/deductible handling, limitations periods, missing/conflicting/superseded authority and synthetic settlement outcomes.
- Success: exact supported quantum; every unknown/conflicting/missing authority = REVIEW/$0; settlement remains distinct from calculated opportunity.
- Failure: illustrative/default legal rule or model output creates hard-dollar assertion.
- Next action: complete explicit synthetic rule-pack benchmark before any customer claim period.

### EXP-012 — Outcome-priced grid resilience calibration
- Opportunity: Grid/Infrastructure Risk & Inspection.
- Capabilities: CAP-015 plus optimization/routing components.
- Status: **READY with dataset-artifact/rights constraints**.
- Hypothesis: a resilience policy can demonstrate same-input advantage only when evaluator ancestry, construct and independence are explicit and predictions are frozen before prospective challenge.
- Historical plane: USECPO v2 (CC BY 4.0) as event-correlated benchmark; exact v2 ZIP/guideline schema/event keys must be inspected before implementing a manifest. Use whole-event blocking and chronology preservation; record EAGLE-I ancestry.
- Independent/challenge plane: Michigan MPSC as strong regulator evidence subject to restrictive commercial reuse terms; NYC 311 only as construct-validity negative control, not utility-outage oracle; California OES public-domain live utility-map feed for prospective post-freeze challenge, not history.
- Success: model/policy beats simple baselines on frozen same-event outcomes without leakage; evaluator lineage/construct are explicit; proxy agreement is not called independent validation; modeled interruption dollars remain separate from observed outage outcome.
- Failure: related EAGLE-I descendants counted as independent validators, citizen-report proxy treated as grid truth, or rights-constrained evidence embedded commercially without permission.
- Next action: obtain/inspect the exact USECPO v2 artifact schema, then freeze splits/evaluator ancestry and run simple-vs-optimized comparisons; only search for another dataset if a genuinely independent, commercially reusable historical oracle remains necessary.

## Portfolio rule
Do not start another product build because a repository is exciting. New search/build effort must close a named experiment gap, create a cheaper falsifier, or respond to a recorded outcome. When an experiment completes, mirror it in `OUTCOMES.md` and `intelligence/outcomes.jsonl` with originating search-run/capability links.