# HUNTER-03 R20 — EXP-003 historical-authority late-return fixture

Date: 2026-09-21

Status: **synthetic fixture executed; external provider/bank and buyer-month evidence remain unverified**

## Assigned question

Execute the provider-neutral EXP-003 acceptance matrix. A later return/reversal must revoke prior settlement exactly once, preserve history, and reopen/re-pay the original earning without consulting a changed current commission policy. Ambiguous or unavailable evidence must not mutate money.

## Baseline execution

The existing 24-case matrix at `referrals/hunt13-r15-2026-09-20-exp003-provider-bank-matrix.py` was re-executed unchanged:

- 24/24 classifications matched the hand-authored expectations.
- All six unsafe evaluator mutants were killed.
- 200 two-writer claim races produced zero double-send violations.
- Duplicate return replay produced one counter-event.
- Deterministic result digest: `7d24e0c5e0cce2ffac5b40590bf346c273639422c0e8a28ce6c0072af491474d`.

## Gap found in the baseline

The baseline does not model an immutable earning/rate snapshot, changed current policy, post-return re-payment, or append-only event history. It therefore cannot establish the assignment's stronger acceptance claim that a late return reopens the original obligation **without rerating under current policy or deleting prior finality history**. The `return_identity_replayed` Boolean also tests a classification branch, not a durable re-payment lifecycle.

This is a coverage gap in the synthetic fixture, not evidence that a deployed commission product is defective.

## Added and executed fixture

`referrals/hunt03-r20-2026-09-21-exp003-historical-authority-fixture.py` freezes earning `earn-1` under `plan-A@2026-01-01` at 10% / 10,000 cents, settles it, changes the notional current policy to 13%, and then exercises the late-return lifecycle.

Observed result: **9/9 checks passed**.

- Exact return evidence from an independent readback inside a verified window appends a counter-event and reopens the original earning.
- The original claim and settlement events remain present.
- Re-payment is 10,000 cents under the original rule revision, not 13,000 cents under current policy.
- A second claim cannot be minted while the re-payment is claimed.
- Duplicate and eight-way concurrent return replay create exactly one reopen.
- Ambiguous, not-found, partial-window, unavailable-window, wrong-payout and webhook-only observations do not mutate money.
- `REFUND_CLAWBACK_NOT_OWED` revokes settlement without reopening an amount owed.
- A permanently lost webhook can be recovered by the modeled independent readback path, while webhook-only evidence is insufficient for this fixture.

Deterministic extension digest: `e33df249cd8a3eb38a48650df6a64a35eaebee335d965d62e734d641db357176`.

## Claims and limits

**Locally tested:** provider-neutral state semantics and concurrency controls in this synthetic Python fixture.

**Not verified:** a real provider adapter; a real bank/payroll feed; source-window completeness; production durability across process/database failure; buyer-authorized historical data; live settlement or realized recovery. This run must not be reported as independent bank finality or commercial outcome evidence.

## Capability / experiment handoff

- **Capability delta:** CAP-018's synthetic corpus now covers historical-rate preservation and reason-aware late-return reopen semantics, not only settlement classification.
- **Experiment impact:** EXP-003 remains READY for an adapter-backed test. The exact next gate is to bind these transitions to one real sandbox/provider-plus-independent-statement fixture with source receipts.
- **Commercial implication:** prevents returned payouts from being silently repriced under today's plan or converted into duplicate repayment obligations.
- **Negative knowledge:** a settlement/return classifier can pass while never testing the historical authority used by the subsequent repayment.

## Blocker and next question

No valid activation/claim event could be persisted because the current repository branch exposes routing/dispatch artifacts but not the referenced worker-presence and execution-event paths. This work is therefore recorded as **unallocated**, not generated/claimed.

Next: can one concrete provider/bank sandbox pair reproduce the same lost-webhook, exact-return, reason classification and historical-rate re-payment path while proving the observation window is complete?
