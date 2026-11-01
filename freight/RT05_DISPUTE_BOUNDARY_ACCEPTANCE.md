# RETALLY RT05 — enforced disputed-credit recovery and fee boundary

**Status:** Source-only synthetic implementation, 2026-10-22. No actual customer,
signed carrier contract, bank-cleared money, independently adjudicated
overcharge, customer approval, external communications or fee-billing authority.

## Product decision

A carrier credit must remain visible in the **source-declared settlement ledger**
even when its related claim becomes disputed. However, a known dispute must
**not** be converted into a new allowed allocation, validated recovery
certificate, fee-eligible amount or commercial bill. The disputed source
can be recorded, but promotion into recovery requires *separate, authenticated
proof* and external authorization. The code must distinguish:

1. **Invoice/finding**: alleged freight error; not adjudicated until reviewed.
2. **Credit receipt**: immutable financial source declaration, not bank clearing.
3. **Dispute hold**: conservative, durable source-declared warning, not proof
   of legal insolvency, wrongdoing or signed customer instruction.
4. **Allocation**: internal accounting linkage, allowed only when claim not held.
5. **Validated recovered funds or billable fees**: **not established** by any of
   these facts. Existing external customer, rights, bank and independent-review
   launch gates stay in force.

## Implementation

- New immutable claim- and tenant-scoped `claim_dispute_holds` SQL table,
  event-source SHA-256 deduplication, chronological and original-claim-source
  binding, append-only/anti-delete triggers, database-level allocation lock
  and no unauthenticated release route.
- `record_recovery_dispute_notice` is the explicit source-intake adapter for
  typed, scope-bound `RecoveryScenario` + `RecoveryEvent`; it verifies exact
  original claim identity, issue time, customer unit, amount and source hash
  before **atomically** recording a conservative hold. Only the allowed carrier
  dispute/denial, customer challenge/withdrawal, insolvency, shutdown or
  contractual time-bar concern can create a hold; a random payment event
  cannot. An SHA digest alone does not authenticate its issuer.
- `SettlementStore.auto_allocate` returns REVIEW, and
  `review_allocate` rejects new allocations, while an SQL trigger blocks
  even legacy direct inserts for held claims. The immutable original credit
  remains available for private accounting reconciliation.
- Previously allocated credits stay in their original immutable rows.
  **Live** `fee_eligible_cents` and per-currency fee-base candidates become
  zero for held claims. Source-declared net credit remains unchanged and
  never becomes a verified bank receipt.
- `build_persistent_pilot_report` fails closed for a held/bound claim rather
  than producing a stale validated recovery certificate. Report snapshot
  receipt changes whenever hold evidence is added; `assert_report_current`
  correctly invalidates old reports.
- `settlement_review_workflow` excludes held claims from eligible manual
  candidates. The actual store remains the atomic enforcement layer; a
  forged reviewer role cannot override its triggers.
- `recovery_resilience` infers `DISPUTED_EVIDENCE_HOLD` from persisted
  source even if a caller no longer supplies the denial event to a read-only
  view. It reports separate `source_declared_net_cents` and zeros
  fee candidates, billable fees, verified bank cash and actual external
  actions. A durable hold also suppresses hypothetical contingency revenue.
- To avoid changing the frozen prior source-only case fingerprints without a
  new evidence event, the added dispute table is included in snapshot hashes
  only when it contains at least one hold; source-free report digests retain
  their old schema. A hold *does* change the snapshot and report hash.

## Adversarial tests and independent invariants

- `test_rt05_dispute_integrity.py`: 12 direct negative/positive controls,
  100 varied typed synthetic dispute/denial/insolvency/withdrawal cases.
- `test_rt05_boundary_redteam.py`: **120 fresh varied buyer/credit/dispute
  chronologies**, **50 simultaneous source-hold vs auto-allocation races**,
  cross-customer forgeries, immutable SQL UPDATE/DELETE attempts, duplicate
  and inconsistent source evidence, prior-credit grandfathering and
  fee-base invalidation. Repeat on Windows and Linux.
- Verify that no actual bank/source provider action is performed, fee eligible
  cents stay zero when held, post-dispute allocations are blocked at both
  Python and raw SQL layers, no cross-tenant hold spreads to innocent
  claims, accounting credit remains true to the source, and all current
  reports are invalidated by new dispute evidence.
- Require the original Priority 0–4, RT2 receipts/payments, settlement,
  reversal, original-PDF/source rights, repository release, customer-truth
  and protected-main gates to pass at exact source head and merged main.
- Never manufacture new independent freight-error adjudication labels.
  Historical 110 source-only freight invoices remain **UNKNOWN**.

## Deliberate fail-closed boundaries and limitations

**Dispute closure is not self-authorized.** This source-only code does not
offer a role-string, single hash, arbitrary flag or synthetic-HMAC release
API. Reopening a held claim requires a separately designed, externally
authenticated, audited dispute-resolution workflow with genuine entitled
customer/carrier evidence. Existing holds are immutable and persist across
restarts. Real customer source/authentication must be checked *before*
intake; knowingly false notices could otherwise conservatively stop a claim.
Source ingestion, not mere background awareness of a private email, is the
explicit transactional boundary—events never submitted to this entrypoint
cannot be inferred by a ledger.

No real payment or commercially useful outcome was asserted; the run is
**not** proof that a customer recovery is collectible, the product is
flawless, nor approval to launch. Genuine buyer consent, independently
adjudicated freight truth, enforceable carrier terms and bank-authenticated
settlement remain separate gate requirements.
