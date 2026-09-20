# Hunt 04 referral — scope-to-cash authority + bank-finality gap

Date: 2026-09-20
Node: 04 Scope Recovery
Purpose: durable cross-agent handoff after Pair 2 EXPERIMENT tasks 09–15 were confirmed complete. This run resumed the live Scope Recovery mission and focused only on the current EXP-005 bottleneck: an unbypassable measurement -> bill/certification -> payment -> independent cash observation chain. No BENCHMARK_GOLD material was consulted.

## HYPOTHESIS
A commercially useful ScopeSignal acceptance path can be made substantially more defensible by separating two proof planes rather than expecting one construction application to prove everything:
1. **Construction authority plane:** approved field evidence + correct project/work-order/contract-line ownership + measurement inside the billed period + cumulative authorized quantity ceiling -> bill/certificate.
2. **Cash-finality plane:** bill/payment intent -> accounting payment object -> independently imported bank transaction -> reconciliation/clearance -> later return/reversal if applicable.

The run tested whether a public construction implementation already makes that entire chain unbypassable, and whether existing upstream accounting/payment components can close the downstream cash-proof edge without confusing internal `PAID` with external settlement.

## DISCOVERY MODES
1. **Direct domain/problem search:** RA bill + measurement + work order + payment, looking specifically for server-side bill creation from field evidence.
2. **Code-signature search:** UTR/bank reference, payment entry, running bill, measurement status, certification, period filters, billed quantity and payment-state transitions.
3. **Low-attention workflow search:** small/new construction/public-works repositories with measurement-book, RA/IPC and approval terminology.
4. **Dependency/ecosystem traversal:** construction apps built on Frappe/ERPNext -> upstream Bank Transaction and reconciliation implementation/tests.
5. **Cross-lane analog reuse:** imported the already-verified Hunt 13 bank-finality lesson (`provider/payment status != bank/network finality`) and evaluated how it changes ScopeSignal’s downstream proof model.

## BEST NEW FIND — QuantbitERP/Quantbit-Construction-Management
- URL: https://github.com/QuantbitERP/Quantbit-Construction-Management
- Exact revision: `d94af9e2be02aa968155272e46ae8dfd8451e802`
- Date inspected: 2026-09-20
- Category: Repository / Reusable Component / Construction billing authority reference
- Status: **strong component/reference — 24/30; not MASTER**
- Public license/provenance: repository `license.txt` contains MIT grant text; README also states MIT. Repository-owned code is additionally covered by the user’s standing separate commercial-permission assertion. ERPNext/Frappe and all customer records/bank data remain separately governed.

### Capability verified
`SC Bill` contains a real server-side cumulative quantity guard. On validation it loads the linked `Subcontractor Details` row, obtains contracted quantity and already-billed quantity, calculates remaining billable quantity, synchronizes the bill row’s guard field and rejects a requested quantity above the remaining amount. On submit it increments billed quantity; on cancel it reverses it.

Its `get_sc_bill_data(project, subcontractor, period_from, period_to)` selector also has economically useful source logic: it filters Subcontractor Details to the selected project and subcontractor, applies a date window when the detail has a date, excludes fully billed detail rows, reconstructs task hierarchy and returns the remaining quantity at the linked rate.

The wider Frappe app has Contractor Billing that can create a Purchase Invoice / Journal Entry, can create a Payment Entry, and synchronizes paid/outstanding amounts from submitted Payment Entry / Payment Entry Reference records.

### Why it matters
This is one of the cleaner public construction examples found where a bill is at least bounded server-side by an authoritative contracted-vs-billed quantity ledger instead of trusting a typed invoice quantity. It also sits on an accounting ecosystem with a real bank-reconciliation plane, making it useful as a **scope-to-cash reference architecture**.

### Independent red-team / verifier verdict
**ACCEPT AS STRONG COMPONENT; REJECT AS COMPLETE AUTHORITY CHAIN.**

The critical weakness is authority-origin consistency. `get_sc_bill_data` enforces project/subcontractor/date selection when it hydrates candidate rows, but the authoritative `SCBill.validate_billable_qty()` path rechecks only the linked Subcontractor Details row’s remaining quantity. The inspected server validation does **not** re-establish that the linked detail belongs to the bill’s selected project, subcontractor and billing period. A caller who can supply a different valid `subcontractor_refer` may therefore bypass the context enforced by the selection helper unless another framework/model constraint outside the inspected method blocks it.

A second path (`Contractor Billing`) is weaker: its browser code fetches Task Progress / equipment / manpower parent records by project and site date, filters child rows by contractor and `!billed`, then copies quantity/rate/amount into bill details. The inspected server `ContractorBilling` class does not independently revalidate those source filters before submit.

Test evidence is also weak for the new construction-specific invariant: `subcontractor_management/doctype/sc_bill/test_sc_bill.py` defines an integration-test class but the body is only `pass`. The server guard is implemented, but no inspected semantic regression test proves wrong-project, wrong-subcontractor, out-of-period or over-billed rejection.

### Score
- A Speed to first revenue: 4
- B Plausible customer value / ACV: 4
- C Build/domain compression: 5
- D Rarity / technical advantage: 3
- E Evidence/completeness/reproducibility: 3
- F Rights/deployment clarity: 5
- **Total: 24/30**

### Commercial implication
Use as a reference/component for a **Scope-to-Cash Acceptance Test** rather than as a trusted entitlement oracle. A paid diagnostic can independently rebuild allowable billed quantity from buyer-authorized project/work-order/contract-line/measurement evidence and compare it with the app’s bill/payment/accounting state. The most valuable exceptions are not generic arithmetic errors but **authority-join failures**: valid quantity from the wrong work order, period, subcontractor, commercial baseline or payment state.

## STRONG DOWNSTREAM COMPONENT — frappe/erpnext Bank Transaction
- URL: https://github.com/frappe/erpnext
- Exact revision inspected: `db6e0891099ab27f571b7b9697ba90f6573430f5`
- Date inspected: 2026-09-20
- Status: **strong downstream settlement/readback component — 25/30**
- Public license/provenance: GPL-3.0 at the inspected revision; user standing permission applies to repository-owned public code. Customer bank statements and banking APIs/services remain separately governed.

### Capability verified
ERPNext’s Bank Transaction model is a genuine external-readback/reconciliation plane rather than an internal `paid` flag:
- preserves bank account, currency, deposit/withdrawal, transaction/reference identifiers, allocated/unallocated amount and reconciliation state;
- prevents duplicate voucher allocation inside one Bank Transaction;
- allocates observed bank-transaction amounts to Payment Entry / other reconciliation doctypes;
- writes or clears voucher `clearance_date` when the related external bank transaction is reconciled/delinked;
- supports cancellation/reopening and Bank-Transaction-to-Bank-Transaction linking for correction/refund-style cases;
- bank-statement import maps configured CSV/XLSX statement fields into submitted Bank Transaction records with per-row savepoints and explicit success/error counts.

### Test evidence
`test_bank_transaction.py` exercises the money-state boundary directly:
- reconciliation drives unallocated amount to zero and sets Payment Entry clearance date;
- cancelling the Bank Transaction clears the Payment Entry clearance date;
- cancelling an already reconciled Payment Entry reopens the Bank Transaction allocation;
- an amended Payment Entry does not inherit the original clearance date;
- already-reconciled and debit/credit matching behavior is tested.

### Red-team boundary
A reconciled ERPNext Bank Transaction is stronger than an internal construction `PAID` state, but it is **not self-authenticating bank finality**. A manually created or stale/incomplete Bank Transaction feed can still be wrong or incomplete. ScopeSignal must preserve bank-source provenance, import/run health and freshness, and separately represent later network returns/reversals. The existing Hunt 13 referral’s `moov-io/ach` Return Entry/original-trace semantics and statement-normalization work are therefore complementary rather than redundant.

### Score
- A4 B4 C5 D2 E5 F5 = **25/30**.

## OTHER CANDIDATES / NEGATIVE CONTROLS

### twishhworkspace/TwishhBuild@`65178eb4f114434dc5a503bab91feb5a8919ebaf`
- Status: **watch / negative control (~19/30)**.
- It has real contractor measurement -> engineer verification -> director decision -> auto-generated running bill transitions.
- However contractor measurement can carry caller-provided physical bill amount; rate values can be caller-supplied; no inspected cumulative authorized-quantity ceiling was found in the approval/bill path.
- Its payment endpoint accepts caller amount, cheque/UTR, bank name and freeform reference, then marks the bill Paid/Partially_Paid. The default reference string can literally contain `/ CLEARED` without any independent bank observation.
- Use as an EXP-005 negative fixture for **approval-shaped workflow + fake finality**.

### Harshitarnav/eastern-estate-erp@`4f8f59291bfe1b1fb31c51e885c6d316940197e8`
- Status: **rejected/deprioritized (~17/30)**.
- RA-bill service has DRAFT -> SUBMITTED -> CERTIFIED -> APPROVED -> PAID-looking workflow, but creation accepts client gross amount and mark-paid accepts a payment-reference string before posting internal accounting state.
- Valuable only as a regression fixture proving that mature-looking commercial states do not establish field authority or cleared cash.

### HolagundiWorks/AQC@`36676304a90aa5677bf38a305d831997575c3033`
- Status: **rejected/deprioritized (~18/30)**.
- Running bills, certification, retention and payment records exist, but bill lines are not proven to be derived from authoritative joint measurement and bank state is an internally entered cash/bank ledger/reference rather than external readback.

### yagsu123/Construction_workflow-management@`7dc9ad3268269d3d48d60e0697831d85753e5f18`
- Status: **watch / workflow reference (~20/30)**.
- Useful e-measurement approval/audit sequence through engineering roles and a payment-trigger state, but the repository explicitly says there is no real PFMS/Treasury integration. Payment trigger is not cash finality.

### nishantpathak35-hash/LWA@`cf79aa3b9c2cc6b72b8738140cfe229119524954`
- Status: **reject for this capability gap**.
- Search surfaced claims around work-order/measurement verification and bank-UTR reconciliation, but this run did not find implementation evidence sufficient to verify those claims.

## COMBINATION DISCOVERED — ScopeSignal scope-to-cleared-cash proof
The strongest architecture is now explicitly multi-plane:

`BIM/drawing delta -> quantity evidence -> controlling contract/work-order/line authority -> approved field measurement -> server-derived bill/certificate -> accounting Payment Entry -> independently imported Bank Transaction -> reconciliation/clearance -> later ACH Return/Reversal check -> realized outcome`

A practical stack can use the existing ScopeSignal change/takeoff/evidence leaders upstream, **Nirman-style APPROVED-measurement-derived RA billing** as the better positive authority pattern, Quantbit as a cumulative-quantity/context-bypass challenger, ERPNext Bank Transaction for bank readback/reconciliation, and the already-verified Hunt 13 `statement-normalizer` + `moov-io/ach` components for independent bank/network observation and post-success invalidation.

## CLAIMS TESTED
- **“Construction app says PAID, therefore cash cleared.” — FALSIFIED.** TwishhBuild and Eastern Estate can enter paid-like states from internal/caller-supplied references without external bank proof.
- **“A cumulative quantity ceiling proves correct billing authority.” — FALSIFIED as a sufficient condition.** Quantbit rechecks remaining quantity but does not re-establish the full project/subcontractor/period origin in the inspected authoritative validator.
- **“Bank reconciliation is stronger than internal PAID.” — VERIFIED.** ERPNext tests show reconciliation sets/clears actual voucher clearance dates and reopens allocations on cancellation.
- **“ERP bank reconciliation alone is final cash truth.” — REJECTED.** Source provenance, import freshness/completeness and later returns/reversals remain separate proof obligations.
- **“One public construction repo currently proves the entire target chain.” — NO.** No inspected candidate simultaneously proved approved measurement, correct work-order/line ownership, period, cumulative ceiling, certified bill and independently cleared cash with robust negative tests.

## EMERGING TECHNOLOGY SIGNAL
**Authority-aware money assurance is becoming a cross-domain pattern rather than a construction-specific feature.** The useful architecture is a sequence of revocable proof states, not one workflow status: physical fact -> commercial authority -> bill/certificate -> payment intent -> externally observed cash -> later return/reversal. This independently reinforces the existing portfolio rule that authority, expected state, actual state and realized settlement must stay distinct.

## FAILURE / NEGATIVE KNOWLEDGE
- Generic `RA bill`, `IPC`, `UTR` and `bank reconciliation` searches are now low-yield. Many results are forms/UI or freeform reference fields that manufacture the appearance of settlement.
- Server validation must re-establish the **same authority dimensions** used to select a candidate record. A UI/helper may filter project/subcontractor/date correctly while the final validator checks only quantity; this is an authority-origin inconsistency.
- A valid quantity from the wrong project/work order/contractor/period is not valid money.
- `payment_reference`, `UTR`, `CLEARED`, `Paid` and a posted accounting entry are evidence fields/states, not independent proof of bank settlement.
- Bank-statement readback without source-run completeness/freshness is also not enough; missing/stale feeds must become UNKNOWN, not “no exception”.

## CROSS-AGENT REFERRAL
- **Payments / money-state / commission lanes:** the Hunt 13 bank-finality components are directly reusable for ScopeSignal. The construction lane should not reimplement ACH return semantics or generic statement parsing.
- **Scope Recovery / Integrator:** treat Quantbit as a strong **authority-origin negative/partial-positive control**: server-side remaining-quantity guard is good, but project/subcontractor/period selection must be repeated in the authoritative validator.
- Exact unanswered technical question for the next specialist: **Can a production-shaped bill-submit service re-load the approved measurement and prove exact work-order/contract-line ownership, bill-period inclusion and cumulative authorization inside one transaction, then persist a stable payment identifier that survives into independently imported bank/network evidence?**

## VALUE HANDOFF
1. **CAPABILITY DELTA:** adds a concrete path from construction bill/payment state to independent bank-transaction reconciliation; sharpens the server-side authority-origin invariant for measurement-derived bills.
2. **GRAPH EDGE:** strengthens ScopeSignal / EXP-005 downstream of bill creation and connects it to the portfolio’s settlement/readback capabilities rather than inventing a separate construction-only payment truth layer.
3. **RADAR SIGNAL:** strengthens authority-aware money assurance and revocable settlement finality across construction, commission/payout and AP/recovery stacks.
4. **EXPERIMENT IMPACT:** EXP-005 should add: wrong-project linked detail; wrong subcontractor; valid detail outside bill period; over-billed quantity; approved measurement attached to wrong work order; internally Paid without bank transaction; reconciled bank transaction then cancelled payment; bank feed unavailable/stale; later ACH return after apparent clearance.
5. **COMMERCIAL IMPACT:** sharpens the paid wedge into a **Scope-to-Cash Acceptance Test / Pay-App-to-Bank Trace Audit** for 20–50 subcontractor changes/bills, classifying `APPROVED_NOT_BILLED`, `BILLED_NOT_PAID`, `INTERNALLY_PAID_NOT_CLEARED`, `CLEARED`, `CLEARED_THEN_RETURNED` and `UNKNOWN_SOURCE`.
6. **NEGATIVE KNOWLEDGE:** do not hunt another generic IPC/pay-app/UTR UI. Search only missing authority joins and source-backed cash-finality links; unresolved authority or bank-source health remains REVIEW/$0.

## SEARCH POLICY UPDATE
Next run should search server-side invariant vocabulary rather than product names:
- bill `validate` / `before_submit` that loads `measurement_id` and requires APPROVED;
- exact `work_order_line_id` / contract-line ownership revalidation;
- `measure_date` against authoritative bill period;
- cumulative authorized quantity rechecked within the bill-submit transaction;
- immutable payment identifier propagated from bill/payment to bank transaction/reference;
- imported-statement source/run/freshness state;
- later return/reversal/original-trace handling.

Use adversarial fixtures as discovery vocabulary: foreign-project line, wrong work order, out-of-period approved measurement, already-billed measurement, superseded baseline, manually created bank transaction, cancelled payment after reconciliation and returned ACH after apparent success.

## NEXT HIGHEST-VALUE QUESTION
**Can a production-shaped construction bill-submit path atomically prove APPROVED measurement + exact work-order/contract-line ownership + bill-period inclusion + cumulative authorized quantity, and then carry one stable payment identity through independently sourced bank/network reconciliation and any later return/reversal?**
