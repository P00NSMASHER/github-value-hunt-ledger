# Hunter 03 — Freight settlement corpus v1 — 2026-09-20

Purpose: execute the current Freight Recovery stage-gate work rather than continue generic freight/reconciliation discovery. Pair 2 CONTROL tasks 09–15 are already complete. Current integrator guidance says to stop reconciliation-engine hunting and implement the PayOps exact gate + explicit reviewed partial-edge ledger on a rights-clean planted 210/812/820 corpus.

## Stage-gate target

Strengthen `CAP-006` / `EXP-001` with an executable synthetic acceptance model for:

`frozen invoice/discrepancy -> issued adjustment/credit -> independently observed 820/bank settlement -> one-use allocation edge -> realized recovery -> later external return/reversal -> linked counter-edge -> realized recovery clawback`

This synthetic test does **not** satisfy the external buyer/outcome gate in EXP-001. It only tests the ledger semantics that must be safe before an authorized frozen customer population is used.

## Evidence reused from prior validated components

- `aldemirkonuk/RestaurantAIAutomation@79dfea023658f014248f3c805ebe7d903c7f3974`: the 812 parser treats BCD07 / REF*IV as the adjusted invoice reference, distinguishes credit vs debit direction, preserves currency semantics and explicitly refuses to count a debit adjustment as recovered money.
- `lailarallc/edi-reconciliation-tool@11740303e3f5323bf5c89f35522884954e012b2d`: 820 parsing preserves RMR invoice references/amounts and the repository records a real grain bug where line-grain RMR generation inflated paid counts; one RMR per invoice is the correct settlement-test grain for this corpus.
- `payops-labs/solana-payment-ops@7e4d9cc8d137e4d32cdb4b23aa5c0965f3379e94`: exact/unique automatic allocation, immutable claim/event identity, canonical revalidation and one-use persistence boundary.
- `Noone9029/Accounting-App@90e0eaa4896a55c1c8cda1c4101f4ab1323a4a61`: explicit reviewed partial-allocation edges, residual capacity and stateful reversal.
- `frappe/erpnext@db6e0891099ab27f571b7b9697ba90f6573430f5`: external bank transaction distinct from accounting allocation, partial allocation and unreconciliation lifecycle.
- `sebastienrousseau/camt053@f4ff150917231c71f734abfcc2c25bed486cc184`: bank-native external identity plus return/reversal lineage (`RvslInd`, original references, return reason).

## Minimal settlement model tested

### Immutable authorities
1. `recovery_claim`: created only from an **issued** credit/refund/adjustment; an audit discrepancy or open dispute cannot create realized money.
2. `settlement_event`: independently observed 820/bank/refund event with stable external ID, parties, exact currency/amount, booking time and authoritative references.
3. `counter_event`: independently observed return/reversal tied to the original external event; it never deletes the historical settlement event.

### Money-bearing edges
`allocation_edge(claim_id, settlement_event_id, amount_minor, mode, reversed_minor)`

Rules tested:
- exact integer money only;
- claim residual and event residual can never become negative;
- gross settlement-event capacity can be consumed only once, even after a later reversal;
- realized recovery is the sum of allocation amounts minus linked reversed amounts;
- claim capacity reopens after a return/reversal because the claim is no longer economically satisfied;
- the original settlement event does **not** become reusable after reversal; a new external event is required to re-settle the reopened claim;
- automatic allocation is allowed only for exactly one candidate with matching payer/payee/currency, valid timing, authoritative reference and exact remaining amount;
- partial, excess, ambiguous, orphan or split cases remain REVIEW / $0 automatically;
- once a claim enters a reviewed partial/split path, subsequent pieces remain reviewed rather than silently switching back to automatic posting;
- reviewed allocation may create multiple explicit pairwise amount edges, but only within remaining claim and event capacity;
- a full return of an original event may automatically reverse all allocations funded by that event;
- a partial return may auto-claw back only when exactly one live allocation edge is attributable; a partial return across multiple allocation edges is REVIEW until explicitly allocated;
- duplicate settlement-event and duplicate counter-event IDs are idempotent and do not change realized recovery twice.

## Deterministic planted cases executed

All amounts below use integer cents in the test harness.

| Case | Expected behavior | Observed result |
|---|---|---|
| Multi-RMR 820 | two invoice-grain RMR sub-events settle two unique issued claims | PASS — both auto-post; realized = $350.00 |
| Partial payment | 820 amount below claim residual cannot auto-post | PASS — REVIEW/$0; explicit reviewed edge realizes $600.00 and leaves $400.00 claim residual |
| Duplicate invoice number | invoice-only reference matches two open claims | PASS — REVIEW/$0 |
| Credit after dispute | settlement before issued claim cannot realize; later issued adjustment can | PASS — pre-issue event REVIEW/$0; post-issue exact event auto-posts $300.00 |
| Overpayment | event exceeds claim residual | PASS — REVIEW/$0 automatically; reviewed $700.00 edge leaves $50.00 event residual |
| Orphan remittance | no issued claim matches | PASS — REVIEW/$0 |
| Split settlement | one claim paid by two partial external events | PASS — both pieces require reviewed edges; final realized = $900.00 |
| Duplicate external event replay | same stable event ID received twice | PASS — second ingest is duplicate; realized unchanged |
| Full later return/reversal | previously settled single event fully returned | PASS — linked counter-edge claws realized amount from $500.00 to $0 and reopens $500.00 claim residual |
| Duplicate return replay | same counter-event ID received twice | PASS — second ingest is duplicate; no second clawback |
| Partial return after multi-claim split | one original event funded multiple claims and later partially returns | PASS — REVIEW; realized remains unchanged until counter-allocation is adjudicated |
| Second payment after claim already satisfied | new event references a zero-residual claim | PASS — REVIEW; realized not double-counted |
| Same settlement event consumed twice | reviewed allocation tries to reuse exhausted event capacity | PASS — second allocation rejected |
| Wrong currency | reference/amount match but event currency differs | PASS — REVIEW/$0 |
| Settlement predates issued claim | external event timestamp precedes adjustment authority | PASS — REVIEW/$0 |

## Adversarial/property pass

A deterministic fuzz pass generated **2,000 synthetic ledgers** with 2–6 claims each, 3–10 settlement events per ledger, mixed exact/partial/excess/orphan/ambiguous references, occasional reviewed allocations and later counter-events.

The following invariants held after every operation:
- every claim residual stayed `>= 0`;
- every settlement-event residual stayed `>= 0`;
- gross event consumption never exceeded the source event amount;
- net claim allocation never exceeded the issued claim amount;
- realized recovery never became negative;
- duplicate source/counter IDs never changed realized recovery twice.

This is an in-memory semantic prototype, not a production concurrency/DB proof. The next implementation must move the same invariants into database constraints/transactions and rerun the corpus under concurrent writers.

## CLAIMS TESTED

1. **An audit discrepancy or dispute can directly create realized recovery:** falsified. Only an issued adjustment/refund/credit may become a `recovery_claim`.
2. **A deterministic reference match is enough for auto-posting:** falsified. Duplicate invoice IDs, partial/excess amounts, wrong currency/party and invalid timing all remain REVIEW/$0.
3. **A partial/split settlement can safely be represented without an opaque many-to-many match object:** supported. Explicit pairwise amount edges plus per-side residual capacity are sufficient for the planted cases.
4. **A later bank/network return should delete the original settlement:** falsified. Preserving the original settlement/allocation and adding a linked counter-edge gives replayable history and correct clawback.
5. **Reversal should make the original settlement event reusable:** rejected. Claim capacity reopens, but the original source event remains historically consumed; a new external money event is required for re-settlement.
6. **A partial return against a split source event can always auto-claw back:** falsified. If the source event funded multiple claims and the return does not uniquely identify the affected edge(s), it remains REVIEW.

## EXPERIMENT IMPACT

`EXP-001` now has a concrete planted settlement/counter-event acceptance specification rather than only a prose requirement. The synthetic safety question is substantially narrowed: the remaining technical work is persistence/concurrency hardening, not another reconciliation search.

The commercial stage gate remains unchanged: `EXP-001` is still `BLOCKED_EXTERNAL` until one explicitly authorized frozen buyer population is carried through controlling authority, independent expected charge, blind incumbent comparison, buyer-approved dispute and actual external credit/refund/remittance allocation.

## CAPABILITY DELTA

`CAP-006 Settlement-grounded recovery attribution` is strengthened with a precise ledger primitive:

`issued claim + independent source event + one-use allocation edge + explicit residual + linked counter-event = replayable realized recovery`

No new capability is promoted because external outcome proof is still missing.

## RADAR SIGNAL

Strengthens `RAD-006 Authority-aware money assurance` and `RAD-001 Proof-carrying operational software` without changing their scores. The important invariant is not "matched payment"; it is a replayable proof chain where every realized dollar is backed by both authority and independent money evidence, and every later return is a separate counter-event.

## COMMERCIAL IMPACT

The synthetic corpus makes the shared-savings pricing boundary more concrete: fee-eligible recovery can be defined as the **net active amount of uniquely attributable external allocation edges**, excluding discrepancy estimates, open disputes, issued-but-unsettled credits, preexisting/automatic credits, duplicates, ambiguous partial/split events and returned/reversed money.

## NEGATIVE KNOWLEDGE / STOP RULE

- Do not hunt another generic reconciliation engine for Freight Recovery unless the first authorized buyer population exposes an unsupported source format or settlement invariant.
- Do not treat 820 envelope/payment total as invoice-grain recovery; preserve RMR grain.
- Do not let invoice number alone auto-post when multiple open claims can share it.
- Do not make a reversed settlement event reusable.
- Do not allocate an ambiguous partial return proportionally by convenience; route it to review unless external evidence uniquely identifies the affected edge.
- Do not move float-based or application-only idempotency semantics into the authoritative recovery ledger.

## CROSS-AGENT REFERRAL

Finance/AP and commission/payout lanes should use the same counter-event test: when one external payment funded multiple entitlement edges, a later partial return must not be auto-distributed unless the bank/provider evidence or reviewed adjudication uniquely identifies which edge(s) were reversed.

Exact unanswered cross-lane question: **which production system enforces this partial-return attribution at the database boundary under concurrent settlement/reversal writes?**

## SEARCH POLICY UPDATE

Current Freight Stack discovery should remain frozen except for concrete source/authority gaps exposed by `EXP-001`. The next high-value work is to port this corpus into the actual Freight Recovery persistence layer with integer/Decimal money, database UNIQUE constraints, residual checks, transactional row locks/conditional updates and concurrent replay tests.

## NEXT HIGHEST-VALUE QUESTION

**Can the Freight Recovery persistence layer pass this same 15-case settlement/counter-event corpus under concurrent writers, proving that duplicate settlement, split allocation and return/reversal races can never double-count or over-claw realized recovery?**
