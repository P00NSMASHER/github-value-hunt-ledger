# RETALLY Priority 3 — difficult freight-recovery resilience

**Classification: SYNTHETIC-ONLY / read-only software improvement.**
This work implements **planning and safety decisions**, not commercial
recovery, an authenticated carrier workflow, a bank payment, a legal opinion,
actual customer consent, a released pilot, or collection activity.

## 29–40: Requirement-to-implementation matrix

| # | Scenario | Read-only safety behavior | Adversarial test |
|---|---|---|---|
| 29 | Carrier refuses/disputes a finding | `CARRIER_DENIAL` and `CARRIER_DISPUTE` hold at `DISPUTED_EVIDENCE_HOLD`; prepare *private* evidence for authorized review. `APPEAL_PREPARED` requires a prior disputed/denied event; no appeal is transmitted. | `test_difficult_carrier_events_hold_without_claiming_recovery`, `test_appeal_requires_proven_dispute_reference_and_time_order` |
| 30 | Bankruptcy, insolvency, or carrier no longer trading | `INSOLVENCY_LEGAL_HOLD`; modeled collectability is not a legal right, bankruptcy probability, or collectible-dollar claim. Referral is a recommendation only; no correspondence. | `test_difficult_carrier_events_hold_without_claiming_recovery` |
| 31 | 6–12 months without collection | Timezones, issue/event chronology, aging in exact calendar days, explicit **planning** response target (not statute), delayed notices and manual deadline review. No scheduled contact or automatic write-offs. | `test_overdue_case_is_planning_alert_not_invented_legal_deadline` |
| 32 | Buyer demands guaranteed savings | `DENY_UNSUPPORTED_FINANCIAL_CLAIM`. No fabricated positive/negative model claim. | `test_customer_request_safety_triage_never_executes` |
| 33 | Buyer demands immediate settlement or fast-track payment | Require fresh authenticated customer/provider authorization. No payment rails, no invented approval and zero transactions. | `test_customer_request_safety_triage_never_executes` |
| 34 | Buyer requests affiliate or changed payee | Existing payee/claim scope cannot be reused. Require a new independently authenticated payee and new permitted instruction; no redirection or money movement. | `test_customer_request_safety_triage_never_executes` |
| 35 | Carrier offers only part of claim, a credit, or split remittance | An **offer** is never realized cash. For actual simulated credit evidence already in the immutable `SettlementStore`, calculate per-claim declared allocation, remaining balance, no bank-certified funds and no collectible/fee authority. | `test_partial_credit_in_existing_store_does_not_create_bank_truth`, `test_full_account_credit_is_not_bank_verified_even_when_net_equals_claim` |
| 36 | Carrier reverses prior credit / returns funds | Read immutable reversal edges and pending counters; pending returns place the case on `RETURN_REVERSAL_REVIEW_HOLD`. A changed settlement snapshot invalidates stale reports; net source-declared balances and fees decrease. | `test_unapplied_return_blocks_recovery_and_stale_snapshot` |
| 37 | Customer rejects RETALLY's finding | `CUSTOMER_DISPUTE` suspends progress. Typed `DISPUTE_FINDING` request requires source adjudication; original proof is immutable, not rewritten. | `test_customer_request_safety_triage_never_executes`, event matrix |
| 38 | Recovery effort may exceed expected benefit | Explicit input probability (unverified, uncalibrated), integer-basis-point modeled fee, loaded labor rate, staff hours, nonlabor costs, and delay. If probability unspecified, expected cash/fee/net are **NULL**. If hypothetical economic net is nonpositive, route to review/HOLD. Actual billable amount remains zero. Incumbent/fee-disqualified claims cannot generate hypothetical fee revenue. | `test_no_calibrated_probability_means_no_estimated_recovery_or_net_value`, `test_high_cost_or_low_collectibility_raises_economic_hold`, `test_recovery_fee_disqualification_stays_outside_client_fee` |
| 39 | Multiple buyers, overlapping account numbers and unrelated carriers | Bind claim reference, issuer/source finding SHA, exact issuance timestamp, payer, payee, currency and amount to one tenant/unit-scoped immutable source; reject cross-tenant store, forged finding and altered issue time. No cross-customer join or shared claim. | `test_cross_customer_store_rejected_and_does_not_mutate`, `test_unrelated_finding_hash_is_rejected_even_when_case_amount_matches`, `test_claim_issuance_time_is_bound_to_snapshot_claim` |
| 40 | Deletion/retention, data export, contractual exceptions | `PRIVACY_AND_RETENTION_LEGAL_HOLD`, no deletion or export without independently verified policy, rights and permissions. Sanitize outputs and avoid private source disclosures. | `test_customer_request_safety_triage_never_executes`, `test_unknown_customer_payment_or_evidence_does_not_write_to_db` |

## Technical scope and evidence gates

- **Source:** `freight/recovery_resilience.py`, one add-on read-only evaluator over actual `freight.settlement_store.SettlementStore.report_snapshot_json`; existing provider/bank/claims engine, SQLite schema and release/privacy gates **unchanged**.
- **Immutable event inputs:** typed carrier and customer scenario declarations, normalized timezone-aware timestamps, signed 64-hex *source identifiers only* (not authenticated signatures), unique event IDs/source digests, rejection of impossible chronology, invalid money, unsupported request types, over-capacity offers, reused proof, forged claim-source identity and stale snapshot. Changing event evidence changes deterministic report SHA.
- **Strong cash distinction:** `source_declared_net_cents` is not bank-cleared cash. Any customer financial claim, actual recovered cash, independently adjudicated freight truth, external contact, provider submission and billable fee remain **ZERO or NOT ESTIMABLE**. Even a full paid-state credit remains source-declared.
- **Recovery feasibility:** uncertainty inputs are labeled `modeled`, with **no empirically calibrated probability**. A source receipt, modeled 30% contingency, hypothetical payoff or reviewer role is neither a signed buyer contract nor fee-billing authority. Financial go/no-go requires external customer evidence and separate authorization.
- **Dispute and bankruptcy:** the engine can recommend private evidence review, authorized legal counsel, or privacy assessment; it **does not send messages**, exercise offsets, alter court records, call payment APIs, register claims, or schedule follow-ups.
- **No new spending**, services, credentials, user data exports, or persistent customer background monitoring.

## Adversarial acceptance and protected release

- Tests: `freight/test_priority3_recovery_resilience.py` (typed validations, scenario state matrix, 120 synthetic combinations, concurrent read-only replay, financial fixture-backed credits/returns, stale snapshot and customer scope).
- Baseline external truth remains: original 110 freight invoice identities lack complete linked independent positive and negative adjudications. Neither a simulation nor source-ledger arithmetic is real freight detection performance.
- CI: `.github/workflows/retally-priority3-recovery.yml` runs dedicated synthetic and native protected financial tests on pinned GitHub Actions identities, with read-only `contents` and **no** external provider/environment activation.
- Integrate only when exact-head CI is successful and protected-main changes are read back; do not weaken owner review, technical/privacy/rights gates, or claim a real pilot.
- This implements Priority 3's **software resilience scope only**, not the legal/financial ability to recover from an insolvent or refusing carrier. Real collection requires signed rights, authenticated terms/payment, appropriate notices, independent adjudication and approved counsel where applicable.

## Roll-forward and rollback

All changes are additive: a self-contained `freight/recovery_resilience.py`, synthetic test, methodology and optional CI. Existing `freight.payment_orchestration`, `settlement_store`, schema, fee gates and original document custody are untouched. Reverting this single source+test+CI addition removes the new hypothetical decision layer without rewriting existing evidence.
