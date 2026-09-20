# Hunter 03 — external settlement readback / reversal evidence — 2026-09-20

Purpose: durable overflow note for the Freight Stack lane. This run resumed normal Node 03 work after Pair 2 CONTROL benchmark tasks 09–15 were already complete. Scope was deliberately narrow because the current queue says to stop generic reconciliation-engine hunting and close the external settlement/finality seam for CAP-006 / CAP-018 / EXP-001.

## Active hypothesis
The remaining software seam is not another matcher. Realized recovery should require two orthogonal layers: (1) an independently sourced bank/network `settlement_event` or `counter_event` with stable source identity and booking/reversal semantics, and (2) a one-use amount-bearing allocation edge to an immutable issued recovery claim. A provider/internal `paid` flag, deterministic match, or ERP reconciliation state alone is not finality.

## Discovery modes used
1. Direct bank-statement / bank-reconciliation / partial-allocation / refund-reversal search.
2. ISO 20022 camt.053/camt.054 code-level search for stable references, booking status, `RvslInd`, return reasons and original-payment lineage.
3. Mature ERP/accounting analog search focused on the persistence mutation that consumes bank-transaction amount rather than the candidate-matcher UI.
4. Adversarial comparison against generic reconciliation ledgers to test whether external transaction IDs, one-use constraints and residual capacity are actually enforced.

## BEST NEW FIND — frappe/erpnext Bank Transaction subsystem — STRONG COMPONENT — 26/30
- URL: https://github.com/frappe/erpnext
- Exact revision: `db6e0891099ab27f571b7b9697ba90f6573430f5` (`develop` HEAD inspected 2026-09-20; commit dated 2026-09-19).
- Category: external bank readback + amount allocation + refund/unreconcile lifecycle.
- Public license / provenance: GPL-3.0 repository license. Per the user's standing instruction, do not downrank the repository solely for public copyleft terms; third-party Plaid service/data rights and deployment obligations remain separate.
- Concrete capability verified: the Plaid ingestion path imports only non-pending transactions, uses Plaid `transaction_id` as external identity, skips a transaction when that ID already exists, and persists date, bank account, deposit/withdrawal, currency, transaction ID/type, reference and description as a submitted `Bank Transaction`.
- Allocation semantics verified: a `Bank Transaction` maintains `allocated_amount`, `unallocated_amount` and child payment entries; duplicate voucher references within one bank transaction are rejected; the allocation routine computes prior allocations across submitted bank transactions, refuses negative/over-allocated voucher capacity, consumes only `min(allocable_amount, remaining_amount)`, and can link one bank transaction to another explicitly for cases such as a refund.
- Reversibility verified: `unreconcile_transaction` and `unreconcile_transaction_entry` remove/cancel reconciliation links; cancelling a reconciled voucher restores the bank transaction's unallocated amount instead of leaving a false settled state.
- Tests inspected: `test_reconcile` drives a 1700 bank transaction to zero unallocated and sets clearance; cancelling the bank transaction clears that evidence. `test_cancel_voucher` shows cancelling the reconciled payment returns the transaction to 1700 unallocated with no payment entries. `test_already_reconciled` expects a validation failure on a second reconciliation attempt. `test_clear_sales_invoice` proves a bank transaction can be allocated directly to an invoice and clears the bank amount.
- External corroboration: current ERPNext documentation describes Bank Transaction as a bank-statement/integration record, supports allocating one bank transaction across multiple vouchers, and recommends preserving source transaction identifiers for duplicate detection/audit. Plaid integration documentation describes synchronized bank transactions carrying transaction identity.
- Why it matters to Freight Stack: this is the strongest new mature implementation this run that joins an independently observed bank event to explicit amount consumption and reversible accounting state. Combined with the previously found PayOps exact/unique gate and Accounting-App residual-edge model, it provides a credible reference for the final `issued freight recovery claim -> externally observed bank movement -> allocation -> realized` seam.
- Buyer / painful problem: freight-audit/payment vendors, enterprise shippers and 3PL finance teams cannot safely bill shared savings if a carrier promise, credit memo or internal `paid` state is mistaken for money that actually settled.
- First paid wedge: ingest customer-authorized bank/remittance evidence after a freight credit/refund is issued; auto-credit realized recovery only for a uniquely attributable external event and explicit persisted allocation. Ambiguous, partial or split cases remain review until explicit edges are created.
- Money path: fewer false recovery invoices, less manual credit/refund tracing, defensible contingency billing, and accurate clawback when a settlement is later reversed.
- Build/domain advantage: compresses several months of bank-transaction state, partial allocation, refund/unreconcile and audit semantics into a mature production reference.
- Red-team limits: (1) Plaid amount handling crosses Python `float`/Frappe `flt`, weaker than integer/Decimal money used by the strongest settlement oracle; (2) this run did not verify a database UNIQUE constraint on `transaction_id`, so the application-level `exists` check may not be race-proof; (3) manual CSV/XLSX import does not expose the same strong external-ID dedupe invariant as the Plaid path; (4) no PayOps-style row lock / canonical-decision reload / conditional residual decrement was proven around all allocation writes; (5) ERP `Reconciled` is allocation state, not irreversible external finality.
- Score: A4 + B5 + C5 + D4 + E5 + F3 = **26/30**.
- Strongest objection: mature reconciliation accounting is not itself a proof oracle. For CAP-006, use the bank event as independent evidence but retain the stricter PayOps exact gate, explicit reviewed partial edges, one-use constraints and counter-event logic.
- Next action: reproduce these semantics in the planted freight settlement corpus with exact money types and database-enforced event uniqueness rather than importing ERPNext wholesale.

## OTHER STRONG CANDIDATE — sebastienrousseau/camt053 — STRONG COMPONENT — 26/30
- URL: https://github.com/sebastienrousseau/camt053
- Exact revision: `f4ff150917231c71f734abfcc2c25bed486cc184`.
- Public license / provenance: `Apache-2.0 OR MIT` verified from the root LICENSE.
- Concrete capability verified: the statement parser reads camt.052/053/054 entry identity and money evidence including `NtryRef`, amount/currency, credit/debit indicator, status, booking/value date, `AcctSvcrRef`, `EndToEndId`, `TxId`, `InstrId`, return reason, counterparty fields and entry-level `RvslInd`.
- Exactly-once support: the library computes a deterministic statement dedupe key from `(MsgId, StmtId, ElctrncSeqNb)` and explicitly warns that missing components weaken collision guarantees and require an upstream check.
- Reversal lineage: implementation/tests construct reversing entries by flipping credit/debit direction, setting `RvslInd=true`, retaining original payment references and carrying a return reason. Parser tests independently assert reversal recognition. SWIFT's public guidance aligns with these semantics: camt.053 returned funds should use reversal indication plus the original instruction reference and return reason.
- Evidence quality: the exact revision's release workflow completed successfully. A later scheduled Suite Consistency workflow is visually red, but job inspection shows its actual suite-check step succeeded; the failure was the GitHub issue-opening step, so it is not evidence that the parser/test suite failed.
- Why it matters: CAMT provides a rights-clear network/bank evidence adapter for the `counter_event` side of CAP-018. A later return/reversal can be linked back to the original externally observed settlement using bank-native IDs and reason semantics instead of deleting history or blindly trusting a provider state.
- First paid wedge: accept authorized camt.053/054 files/feed from a customer bank, normalize booked/reversed events into the settlement-event ledger, and let the allocation layer determine whether realized freight recovery should increment, remain pending or be clawed back.
- Red-team limits: (1) a reversal XML generated by the library is not proof a bank actually posted a return; only an incoming authorized bank/network statement should count as external evidence; (2) the package does not implement claim/allocation residual accounting; (3) statement-level dedupe can be weak when IDs are absent; (4) reference preservation still needs claim-side authority and one-use allocation constraints.
- Score: A3 + B4 + C5 + D4 + E5 + F5 = **26/30**.
- Combination: incoming CAMT event/counter-event -> immutable external settlement-event store -> PayOps exact unique gate -> Accounting-App-style reviewed partial/split edges -> realized-recovery derivation.

## NEGATIVE COMPARATOR — blnkfinance/blnk — WATCH / NOT MONEY AUTHORITY — 22/30
- Exact revision inspected: `91bb84d0611c5c469d005ca10632ebefbc1f3100`.
- Useful evidence: external transactions have a primary-key external ID and NUMERIC amount; reconciliation batches write matches transactionally.
- Disqualifying CAP-006 gap: the inspected `matches` table has no proven uniqueness constraint preventing one external transaction or one internal transaction from being reused across multiple match rows, and no explicit per-side residual-capacity invariant. This is acceptable for a generic reconciliation record, not sufficient for realized-recovery proof.
- Negative knowledge: atomic batch insertion is not the same thing as one-use economic settlement. Persisted `matched` rows without consumption constraints/residual accounting must not move the realized-dollar counter.

## CLAIMS TESTED
1. **Independent bank readback can remain separate from accounting allocation:** supported. ERPNext's Bank Transaction concept and CAMT statement entries both model the external observation independently from invoices/claims.
2. **A later return/reversal should delete the original allocation:** falsified. The safer pattern is to preserve the original event/allocation and attach a counter-event/reversal that restores residual capacity or subtracts realized recovery.
3. **An ERP `Reconciled`/`Paid` state is enough for finality:** rejected. It proves an internal allocation state, not absence of later bank/network return.
4. **Stable external identity plus batch-atomic match writes are enough:** rejected. One-use constraints and explicit residual-capacity consumption remain necessary.
5. **Bank/network reversal metadata can carry original-payment lineage:** supported by CAMT implementation plus SWIFT public guidance.

## Architecture update — two-layer finality boundary
Treat the final seam as two independent proof layers:

`issued_recovery_claim`
→ `external_settlement_event(source, stable_external_id, booked_status, amount, currency, observed_at)`
→ `active_allocation_edge(claim_id, event_id, amount, evidence_version)`
→ `realized_recovery += active_edge.amount`

Later:

`external_counter_event(original_external_id, reversal/return_reason, amount)`
→ `reversal_edge / negative allocation linked to original edge`
→ `realized_recovery -= reversed_amount`

Rules: the source event must be independently observed; the claim must represent an issued credit/refund/adjustment rather than a discrepancy estimate; auto-allocation is exact/unique only; partial/split/N↔M cases require explicit reviewed pairwise edges; no event or claim capacity may go negative or be consumed twice; counter-events preserve the original history.

## EMERGING TECHNOLOGY SIGNAL
This materially strengthens `RAD-006 Authority-aware money assurance` and `RAD-001 Proof-carrying operational software`. The converging architecture across payments, ERP reconciliation and ISO 20022 is now:

**authority -> external observation -> stable identity -> one-use allocation -> explicit residual -> counter-event -> derived realized state**.

The important commercial moat is not a smarter matcher. It is a provable, replayable chain explaining why a dollar entered realized recovery and why it was later removed if the bank/network reversed it.

## FAILURES / NEGATIVE KNOWLEDGE
- Stop generic reconciliation-engine hunting; the current queue is correct.
- Do not use ERP `Paid`, provider `settled`, or internal `Reconciled` as irreversible finality.
- Do not accept manual statement imports without a stable source identity/dedupe policy when they drive money.
- Do not let float-based money or application-level `exists` checks become the authoritative one-use settlement invariant; use exact money plus DB constraints/transactional claims.
- Do not interpret a generated return/reversal message as external truth; the bank/network must independently observe/post it.
- A reconciliation table with transactionally inserted matches is still unsafe if an event can fund two claims or a claim can be over-consumed.

## CROSS-AGENT REFERRAL
Finance/AP + accounting-integrity lanes should compare their bank-import and cash-application candidates against this exact two-layer standard. Exact unanswered question: **which implementation combines bank-native stable identity plus pending/booked/returned status with database-enforced one-use residual allocation, rather than providing only one of those layers?**

## SEARCH POLICY UPDATE
No more broad settlement/reconciliation searches unless a real pilot exposes a specific unsupported source format. Node 03 should now prefer implementation/benchmark closure: build the planted 210 -> adjustment/credit -> 820/bank-readback -> realized-recovery chain, then inject a later ACH/CAMT return and prove the counter-edge automatically claws back realized money without erasing original evidence. Search again only for the exact source adapter missing from the first authorized customer population.

## KNOWLEDGE-TO-VALUE HANDOFF
- **Capability delta:** CAP-006/CAP-018 now have a concrete mature external bank-observation reference (ERPNext) plus a rights-clear ISO 20022 return/reversal adapter (camt053), complementing the existing PayOps exact gate, Accounting-App partial edges and moov-io/ach ACH return logic.
- **Graph edge:** strengthens the final settlement/counter-event edge of `EXP-001`; no longer a generic software-discovery gap. The remaining blocker is external validation on one authorized closed customer population.
- **Radar signal:** reinforces `RAD-006` and `RAD-001`: financial finality is becoming a source-observation + allocation + counter-event proof chain, not a mutable status field.
- **Experiment impact:** extend the planted freight corpus with an externally booked settlement, partial/split review case, duplicate source event, and later bank/network reversal. Assert realized recovery increments only after active allocation and decrements only through a linked counter-edge.
- **Commercial impact:** materially improves the defensibility of shared-savings freight recovery because customer billing can be based on externally evidenced, non-reversed cash/credit allocation rather than carrier promises or internal workflow state; later returns can be clawed back deterministically.
- **Negative knowledge:** bank statement parsing, reconciliation and matching are individually insufficient; the money-bearing primitive is an active, one-use allocation edge tied to independent external evidence and reversible by a linked counter-event.

## NEXT HIGHEST-VALUE QUESTION
**Can the planted 210 -> issued credit/adjustment -> 820/bank settlement corpus prove that a later bank return/reversal automatically subtracts realized recovery through a linked counter-edge, while partial/split allocations remain explicitly reviewed and no source event is consumed twice?**
