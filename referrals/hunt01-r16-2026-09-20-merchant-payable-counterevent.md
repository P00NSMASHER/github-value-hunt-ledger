# Hunt 01 R16 cross-lane referral — merchant payable authority + late counter-event

## Target lane
Money-State / Payment Integrity — CAP-016 / CAP-018 / EXP-010.

## New evidence
`nzebrian/eruofood-ai@9c191ece9b27ad6efd7675dd7bf7013e5e1bdf1c` combines several primitives that were previously split across components:

- event-time merchant earning derived from the original immutable payment-capture ledger rather than current configuration;
- persisted effective `commission_rate_bps` on an append-only payable accrual;
- one earning per order and one refund adjustment per refund via partial unique indexes;
- payout amount derived from reserved accruals, not caller input;
- durable payout attempt written before the external transfer;
- UNKNOWN/Processing provider outcomes remain non-retryable and reserved until reconciliation;
- provider-confirmed failure releases the lines and restores the payable;
- completed settlement reversal is compensating, preserves the original posting, releases the original accrual lines, and therefore makes the original event-time earning reusable for a later settlement.

`Layr-Labs/d-inference@1451a4c8911bc4ec9d094c31fa508f22e55d1865` supplies the complementary automatic Stripe counter-event distinction: `transfer.reversed` re-credits the platform ledger, while connected-account `payout.failed` does not because the money remains in the connected account for the next sweep.

## Why this matters
This narrows EXP-010's remaining money-out gap. We now have strong source/test evidence for:

`historical authority -> payable -> safe payout attempt -> UNKNOWN reconciliation -> compensating reversal -> payable reopened`

and independently for automatic provider return/reversal plus correct cash-location semantics.

## Exact unanswered technical question
Can one implementation—or the EXP-010 synthetic fixture—join those semantics so an independently observed `payout.failed`, `transfer.reversed`, ACH return, or equivalent late provider/bank counter-event is correlated to the exact prior payout and **automatically** creates the compensating payable event, while any re-payment derives from the original immutable earning/rate snapshot rather than current configuration?

## Negative constraint
Do not treat an internal `reverse()` endpoint as proof of end-to-end reversal safety. The external observation/correlation edge must be independently evidenced, and a payout failure must not be assumed to mean platform cash has returned.

## Durable source record
See `hunters/01-run16-2026-09-20.md`.
