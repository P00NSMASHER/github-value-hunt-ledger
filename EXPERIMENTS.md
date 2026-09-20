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
- Hypothesis: independent invoice/PO/receipt/identity/authority logic can separate actionable leakage from unresolved exceptions.
- Inputs: synthetic month with duplicates, partial receipts, price/quantity variance, tax, missing PO/receipt, credits and settlement outcomes.
- Success criteria: 100% planted case detection with zero unsupported recovery claims; ambiguous authority routes to review/$0.
- Failure criteria: exception dollars are mislabeled as recoverable or identity/receipt ambiguity silently resolves.
- Decision unlocked: whether AP becomes a second direct-money wedge.
- Next action: assemble common corpus from current structured-invoice, identity and accounting components.

### EXP-003 — Commission plan-to-payout acceptance test
- Opportunity: Partner / Commission Payout Assurance.
- Capabilities: CAP-002, 006, 007, 016.
- Status: **READY**.
- Hypothesis: frozen plan/assignment/CRM/payment truth can independently detect under/overpayment, stale-plan attribution, reversals and carry-forward errors.
- Inputs: 40-case synthetic closed month spanning tiers, splits, plan changes, refunds, cancellations, holds, partial payouts and carry-forward.
- Success criteria: deterministic expected payout and settlement classification across all planted cases; ambiguous credit ownership stays unresolved.
- Failure criteria: retroactivity/refund/partial settlement semantics cannot be reproduced.
- Decision unlocked: whether commission assurance is as commercially attractive as freight/AP.
- Next action: normalize current commission components into one shared case schema.

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
- Hypothesis: source packet/history + FAR/deviation + entity/award lineage materially improves analyst decision quality and rule currency.
- Inputs: 10 current solicitations with authoritative source artifacts.
- Success criteria: packet completeness, exact source citations, correct current rule/deviation applicability and no false incumbent/entity joins after manual verification.
- Failure criteria: stale or misapplied authority, missing amendments or confident unresolved joins.
- Decision unlocked: whether CaptureBrief can sell rule-currency/readiness diagnostics now.
- Next action: select 10 live solicitations and freeze evaluation rubric before reviewing outputs.

### EXP-007 — Governed lab campaign shadow test
- Opportunity: Installed-Base Lab Automation / Governed Campaign Shadow Audit.
- Capabilities: CAP-013 plus governance/provenance components.
- Status: **READY** for rights-clean synthetic campaign.
- Hypothesis: governance/validation/recovery policies reduce invalid actions and improve replay completeness relative to optimizer-only control.
- Inputs: closed-loop synthetic campaign with invalid-action traps and recoverable failures.
- Success criteria: lower invalid-action rate, comparable/better objective performance, complete replay/provenance and deterministic stop/recovery behavior.
- Failure criteria: governance adds cost without measurable safety/quality gain.
- Decision unlocked: whether this remains radar/watch or moves toward an enterprise implementation wedge.
- Next action: define plain-optimizer baseline and common cost metrics.

### EXP-008 — Industrial virtual pre-FAT bind benchmark
- Opportunity: Industrial Pre-FAT / Virtual Commissioning.
- Capabilities: CAP-014.
- Status: **READY** with synthetic configuration.
- Hypothesis: a configuration-derived virtual controller can catch HMI/SCADA binding/type/fault defects before hardware.
- Inputs: synthetic L5K-like export with planted missing tags, type drift, UDT/array mismatch and fault behaviors.
- Success criteria: all planted defects detected; valid bindings preserved; evidence is reproducible.
- Failure criteria: namespace/type semantics diverge enough to create false confidence.
- Decision unlocked: whether to package a fixed-price pre-FAT regression service.
- Next action: create a small synthetic machine namespace and acceptance checklist.

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
- Next action: define canonical event/money-state schema and run two independent implementations.

## Portfolio rule
Do not start another product build merely because a new repository is exciting. First ask whether it changes one of these experiments, creates a better experiment, or invalidates an existing hypothesis.
