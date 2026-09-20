# EXPERIMENTS

Canonical queue that converts research knowledge into falsifiable economic or technical tests.

The purpose of this file is to stop the system from becoming a museum of interesting repositories.

## Experiment states
- READY — can be run with available lawful/synthetic inputs.
- BLOCKED_EXTERNAL — requires customer-authorized or other externally supplied data/access.
- RUNNING — execution evidence is being produced.
- PASSED — success criteria met.
- FAILED — success criteria not met; record why.
- SUPERSEDED — a better experiment replaced it.

## Experiment schema
- ID / name
- Opportunity / capabilities tested
- Status
- Hypothesis
- Inputs
- Procedure
- Success criteria
- Failure criteria
- Cost/time boundary
- Evidence artifact
- Commercial decision unlocked
- Next action

## Priority queue — 2026-09-20

### EXP-001 — Freight blind audit to realized settlement
- Opportunity: Freight Audit Acceptance Test / Recovery.
- Capabilities: CAP-001, 003, 004, 005, 006, 007.
- Status: **BLOCKED_EXTERNAL**.
- Hypothesis: the stack can identify unique, defensible freight overcharges/incumbent misses and carry at least one through actual credit/refund/remittance without circular truth.
- Inputs: customer-authorized frozen contracts/addenda/rate confirmations, shipment truth, invoices, incumbent output and later settlement evidence.
- Procedure: freeze population -> freeze independent truth -> open incumbent output -> score unique findings -> dispute/review -> follow settlement.
- Success criteria: every asserted dollar has authority + calculation + evidence lineage; false-positive dollars remain below an agreed threshold; at least one unique finding reaches realized settlement.
- Failure criteria: material circularity, unsupported authority, unresolved settlement attribution or false positives above threshold.
- Cost boundary: do not contact customers or spend money without explicit user approval.
- Decision unlocked: whether freight becomes the first scaled commercial recovery business.
- Next action: obtain one authorized closed population when the user approves outreach/data use.

### EXP-002 — AP leakage synthetic three-way audit
- Opportunity: AP Leakage Assurance.
- Capabilities: CAP-001, 002, 007, 008, 016.
- Status: **READY**.
- Hypothesis: independent invoice/PO/receipt/identity/authority logic can separate actionable leakage from unresolved exceptions while preserving durable negative identity knowledge and reversible corrections.
- Inputs: synthetic month with duplicates, partial receipts, price/quantity variance, tax, missing PO/receipt, credits and settlement outcomes; identity cases include alias, explicit non-match, mistaken merge, split/correction and later referent addition.
- Procedure: run candidate identity evidence -> durable POSITIVE/NEGATIVE/UNSURE review -> correction/split where planted -> promoted pinned registry lookup -> invoice/PO/receipt matching -> authority/proof gate -> settlement classification.
- Success criteria: 100% planted case detection with zero unsupported recovery claims; ambiguous authority routes to review/$0; explicit negative identity judgement blocks a later false merge; corrected/split identity state replays deterministically through the promoted registry.
- Failure criteria: exception dollars are mislabeled as recoverable, identity/receipt ambiguity silently resolves, an explicit negative match is later overridden without reviewed evidence, or corrected identity state cannot replay deterministically.
- Decision unlocked: whether AP becomes a second direct-money wedge and whether Nomenklatura-style judgement memory plus Canon-style registry promotion is worth making a shared identity control plane.
- Next action: assemble the common corpus from structured-invoice, Nomenklatura/Canon identity and accounting components and run the identity-correction cases before adding another resolver.

### EXP-003 — Commission plan-to-settlement acceptance test
- Opportunity: Partner / Commission Payout Assurance.
- Capabilities: CAP-002, 006, 007, 016, 018.
- Status: **READY**.
- Hypothesis: frozen plan/assignment/source-payment truth plus an explicit provider-settlement state machine can independently detect entitlement errors without creating duplicate payout risk when provider results are ambiguous.
- Inputs: a synthetic closed month spanning tiers, splits, plan changes, writing/direct vs override compensation, staffing/compliance holds, hierarchy changes, lending sequence/slab cases, refunds/cancellations, clawbacks, minimum/carry-forward, partial payouts, definite provider refusal, timeout/unknown result, duplicate retry/callback, confirmed payout, final FX-settled amount/currency, reversal-after-payout and concurrent sweep races.
- Procedure: freeze plan/assignment/source-credit authority -> calculate independent entitlement -> apply hold/reversal/carry-forward rules -> create one payout intent/claim -> inject provider outcome -> reconcile final settlement -> compare expected entitlement, intended payout and actual settled amount/currency as separate states.
- Success criteria: deterministic expected payout across all supported cases; ambiguous credit ownership remains unresolved; an ambiguous provider result remains claimed/pending and is **not** automatically retried; only a definite refusal releases the claim for retry; retries/callbacks/concurrent sweeps cannot duplicate money; confirmed provider send and final settlement remain distinct; final amount/currency and reversal lineage reconcile exactly.
- Failure criteria: retroactivity/refund/carry-forward semantics cannot be reproduced; unknown provider outcomes release the claim or trigger duplicate send; “sent” is treated as “settled”; provider status overrides entitlement authority; or settlement discrepancies are silently absorbed.
- Decision unlocked: whether commission assurance has a sufficiently complete entitlement-to-cash proof chain to compete with freight/AP as a direct-money business.
- Next action: normalize OpenPartner, Spree and the membership/staffing/lending/hierarchy adapters into one vendor-neutral case schema and run the full synthetic outcome matrix before seeking a customer period.

### EXP-004 — Recovery Proof adversarial matrix
- Opportunity: Recovery Proof SLA.
- Capabilities: CAP-007, 010.
- Status: **READY**.
- Hypothesis: the combined verifier can prove good recovery and reliably reject deliberately wrong recovery.
- Inputs: synthetic/isolated PostgreSQL plus one non-Postgres workload; wrong PITR target, missing history, checksum corruption, service-up/data-wrong, stale proof and trust failures.
- Success criteria: every negative control is rejected for the correct reason; positive recovery includes measured RTO/RPO and application/data invariants.
- Failure criteria: any planted bad state produces a pass.
- Decision unlocked: whether to package Recovery Readiness Audit as an immediate service.
- Next action: unify evidence schema across two restore engines and trust validation.

### EXP-005 — ScopeSignal evidence-to-paid benchmark
- Opportunity: Construction Change Leakage Recovery.
- Capabilities: CAP-001, 007.
- Status: **READY** for synthetic; **BLOCKED_EXTERNAL** for commercial proof.
- Hypothesis: design/field change evidence can be traced through contract/notice/authorization/cost/payment state without inventing entitlement.
- Inputs: synthetic project with 20–50 changes plus deliberate missing/conflicting clauses/evidence.
- Success criteria: correct change classification, explicit unknown states and no unsupported billable-dollar assertions.
- Failure criteria: document delta is treated as entitlement by default.
- Decision unlocked: whether ScopeSignal deserves a near-term commercial pilot.
- Next action: build synthetic end-to-end change-state corpus.

### EXP-006 — CaptureBrief 10-solicitation authority benchmark
- Opportunity: CaptureBrief FAR-Deviation Readiness.
- Capabilities: CAP-002, 007, 011.
- Status: **READY** using current public authoritative sources.
- Hypothesis: source packet/history + FAR/deviation + entity/award lineage materially improves analyst decision quality and rule currency when amendment/version history is deterministic and source failure cannot silently become “no change.”
- Inputs: 10 current solicitations with authoritative source artifacts, frozen amendment/version sequence, entity/award identifiers and source-run metadata; add planted out-of-order amendment, missing-history and source-failure cases in a synthetic companion fixture.
- Procedure: freeze every source artifact/version -> normalize deterministic history/events -> prove idempotent rerun -> resolve packet/amendment order -> apply current FAR/supplement/deviation authority -> resolve entity/award lineage -> manually verify outputs. Use the `contract-delta-au` history/event model only as an architecture pattern; do not import its Australian procurement semantics as U.S. authority.
- Success criteria: packet completeness, exact source citations, correct amendment ordering, byte-/event-stable idempotent reruns, explicit missing-history/source-failure state, correct current rule/deviation applicability and no false incumbent/entity joins after manual verification.
- Failure criteria: stale or misapplied authority, missing/out-of-order amendments silently accepted, source failure treated as no change/no record, nondeterministic history, or confident unresolved joins.
- Decision unlocked: whether CaptureBrief can sell rule-currency/readiness diagnostics now and whether deterministic source-version lineage materially improves trust over latest-row ingestion.
- Next action: select 10 live solicitations, freeze the evaluation rubric and build the small planted amendment/history-failure companion fixture before reviewing outputs.

### EXP-007 — Governed lab campaign + sequencing-operations shadow test
- Opportunity: Installed-Base Lab Automation / Governed Campaign Shadow Audit / Sequencing Operations Evidence.
- Capabilities: CAP-013, CAP-017 plus governance/provenance components.
- Status: **READY** for rights-clean synthetic tests.
- Hypothesis: governance/provenance improves replay and fail-closed behavior, and a concrete Clarity -> InterOp -> provenance profile can link workflow state to sequencer operational evidence without sequence-content analysis or PHI.
- Inputs: (A) closed-loop synthetic campaign with invalid-action traps and recoverable failures; (B) synthetic Clarity QC/pooling/run-prep workflow, lawful/public InterOp fixtures, stable synthetic run/workflow identity and provenance store.
- Procedure: run a plain optimizer/control baseline and governed campaign; separately execute Clarity state transitions, attach InterOp operational metrics, replay the same run, and inject invalid transition, missing/mismatched run identity, missing metric artifact and run-metric exception cases.
- Success criteria: governed path lowers invalid actions or improves replay completeness without unacceptable objective loss; sequencing profile deterministically links workflow/run evidence, rejects mismatched identities/transitions, preserves unknown states and requires no sequence reads/PHI.
- Failure criteria: governance adds cost without measurable safety/quality gain; sequencing evidence silently joins the wrong run, turns missing evidence into success, or requires sensitive sequence/patient data for the proposed operations wedge.
- Decision unlocked: whether Installed-Base Lab Automation should move from generic platform integration to a concrete sequencing-core implementation service.
- Next action: build the synthetic S4 Clarity + Illumina InterOp + provenance acceptance fixture before seeking any customer environment.

### EXP-008 — Industrial virtual pre-FAT bind + protocol-state benchmark
- Opportunity: Industrial Pre-FAT / Virtual Commissioning.
- Capabilities: CAP-014.
- Status: **READY** with rights-clean synthetic configuration/profile.
- Hypothesis: configuration/profile-derived virtual industrial endpoints can catch binding/type/state/fault defects before hardware when validated against independent clients/implementations rather than self-agreement.
- Inputs: (A) synthetic L5K-like export with planted missing tags, type drift, UDT/array mismatch and fault behaviors; (B) a frozen rights-clean SECS/GEM dialogue/profile containing communication/control-state transitions, variables/constants, event reports, alarms, remote commands, bounded spooling and Stream-9/error cases.
- Procedure: instantiate the PLC/OPC profile and run independent client/binding checks; separately run the identical SECS/GEM dialogue/error corpus against Dreamine.Gem and one unrelated implementation/simulator, recording every semantic disagreement. Keep current SEMI/vendor conformance outside the claim unless separately established.
- Success criteria: all planted PLC binding/type defects detected; valid bindings preserved; SECS/GEM state/error outcomes are reproducible and every cross-implementation disagreement is classified as profile ambiguity, implementation defect or unresolved standard/vendor-authority question.
- Failure criteria: namespace/type/state semantics diverge enough to create false confidence; same-family agreement is used as independent proof; implementation agreement is mislabeled formal standards conformance; or missing/error states silently become success.
- Decision unlocked: whether to package a fixed-price pre-FAT regression service spanning controller binding and stateful industrial protocol acceptance rather than a single PLC emulator demo.
- Next action: build the small synthetic machine namespace plus frozen SECS/GEM dialogue/error corpus and identify one unrelated legal/public simulator or implementation for the differential pass.

### EXP-009 — Permit intelligence multi-jurisdiction benchmark
- Opportunity: Permit-to-Development Opportunity Intelligence / PermitPlate.
- Capabilities: CAP-002, 012.
- Status: **READY** using lawful public jurisdiction feeds.
- Hypothesis: canonical versioned permit events plus parcel/economic context can outperform raw permit lead lists on reliability and actionability.
- Inputs: three jurisdictions with different source systems and 30–100 held-out permit events.
- Success criteria: high source completeness, correct field semantics, stable identity/versioning and useful development/opportunity features with source dates.
- Failure criteria: semantic mapping errors, duplicate/version confusion or unsupported economic inference.
- Decision unlocked: whether to deepen PermitPlate into a generalized permit-to-opportunity engine.
- Next action: select three heterogeneous jurisdictions and freeze source-field truth set.

### EXP-010 — Money-state integrity common month
- Opportunity: Money-State Integrity / Close Assurance.
- Capabilities: CAP-006, 016.
- Status: **READY**.
- Hypothesis: one generalized event-to-accounting truth boundary can underpin multiple vertical assurance businesses.
- Inputs: synthetic month of orders/usage/invoices/credits/payments/journals with planted missing, duplicate, unbalanced and period-lock faults.
- Success criteria: operational and accounting planes reconcile on correct cases and expose every planted disagreement with source lineage.
- Failure criteria: vertical-specific semantics make the generalized boundary too lossy.
- Decision unlocked: whether to make this a platform component under AP, commissions, telecom, utilities and marketplaces.
- Next action: define canonical event/money-state schema and run two independent implementations, including automated idempotency/refund/reversal/outbox failure cases before relying on any untested payment core.

### EXP-011 — Subrogation rule-and-quantum fail-closed benchmark
- Opportunity: Insurance Subrogation Recovery Diagnostic.
- Capabilities: CAP-001, CAP-006, CAP-007 plus deterministic recovery-quantum workflow under evaluation.
- Status: **READY** for synthetic technical validation; **BLOCKED_EXTERNAL** for commercial outcome proof.
- Hypothesis: a Recoupe-style workflow can prioritize defensible recovery opportunities only if jurisdiction/policy authority is explicit, versioned and fail-closed rather than inferred from illustrative/default rules.
- Inputs: fully synthetic closed claims covering paid-loss composition, comparative/contributory fault regimes, policy limits, made-whole/deductible handling, limitations windows, missing/conflicting authority and settlement outcomes. Any legal/rule values in the benchmark must be deliberately authored test fixtures unless separately sourced as current authority.
- Procedure: freeze facts -> freeze explicit synthetic rule-pack version -> calculate quantum -> proof/evidence gate -> demand/negotiation state -> synthetic settlement. Include unknown jurisdiction, missing rule, superseded rule, conflicting rule and unsupported policy-language cases.
- Success criteria: exact deterministic quantum on supported cases; every unknown/conflicting/missing authority case remains REVIEW/$0 asserted recovery; no generic jurisdiction fallback silently creates money; settlement state remains distinct from calculated opportunity.
- Failure criteria: an illustrative/default legal rule yields a hard-dollar recovery assertion, LLM output controls authoritative money/legal state, or calculated recovery is mislabeled as realized settlement.
- Decision unlocked: whether the subrogation architecture merits a future customer-authorized closed-claim diagnostic after authoritative rule packs are supplied.
- Next action: replace repository illustrative rule data with explicit synthetic benchmark rules first; only then test a separately sourced/current rule pack or buyer-authorized closed claims.

## Portfolio rule
Do not start another product build merely because a new repository is exciting. First ask whether it changes one of these experiments, creates a better experiment, or invalidates an existing hypothesis.