# Hunt 01 -> Money-State / Payment Integrity referral — 2026-09-20

## Candidate
`tonytonycoder11/stripe-connect-reckon@deb30aabfed84c7b0b2e5ae28c92cc9f85f79193`

## Why refer
This zero-star MIT component provides an independent Stripe Connect observation plane. Its reconciliation path lists provider payouts for every configured connected account over a configurable window, regardless of the host application's local payout state, and can separately detect unprocessed `payout.failed` events when the application supplies processed-event IDs.

This directly addresses the observation half of EXP-010's remaining lost-post-success-webhook seam: a vertical ERP can stop polling after local `PAID/COMPLETED`, while an independent observer continues reading provider truth.

## Verified evidence
- Direct per-connected-account `stripe.payouts.list(...)` with Stripe-Account header and pagination.
- Payouts fetched unconditionally on reconciliation runs; application state is only required for refund/event-gap comparisons.
- Tests verify failed payout mapping and critical classification.
- Tests verify an unprocessed `payout.failed` event is surfaced as a critical event gap.
- Read-only by design: no provider mutation and no automatic host-ledger repair.

## Important limitation
Do **not** treat a provider failed/reversed payout as automatic evidence that a worker/vendor is still owed. The observer lacks the vertical economic context needed to distinguish:
- `BANK_RETURN_STILL_OWED` -> reopen historical earning/payable; versus
- `REFUND_CLAWBACK_NOT_OWED` -> reduce/reverse entitlement.

It also does not itself map the provider payout back to an immutable historical rate/earning artifact or perform the compensating/re-payment path.

## Exact unanswered technical question
Can an adapter compare already-terminal local payouts against independently polled provider payout/event truth by exact provider ID, classify `still owed` vs `economic clawback`, and only then invoke the same idempotent authority-preserving reopen/re-pay path from the original earning snapshot?

## Suggested EXP-010 fault
1. Create historical earning under rate A.
2. Pay it and mark local payout COMPLETED.
3. Suppress the provider reversal/failure webhook.
4. Provider payout becomes failed/returned.
5. Independent provider scanner must discover contradiction by exact payout ID.
6. Scanner must **not** automatically reopen until economic reason is classified.
7. `BANK_RETURN_STILL_OWED` must reopen rate-A earning and allow safe re-pay.
8. `REFUND_CLAWBACK_NOT_OWED` must reduce entitlement instead.
9. Redelivery/repeated scans must be idempotent.
