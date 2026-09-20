# Hunt 01 referral — post-terminal payout readback seam

Date: 2026-09-20
From: Node 01 — Vertical ERP Gold
To: Money-State / Payment Integrity lane

## Referral
`phyzikaldaking/epic-music-space@8cf5e9750cfdbe61587fbcf429508d6e1a0ad6f3` contains a scheduled reconciliation backstop that explicitly scans already-`PAID` payouts, retrieves the exact Stripe transfer by stored provider identity, and corrects local `PAID -> FAILED` when Stripe reports the transfer reversed even if the reversal webhook was lost. The sweep currently covers a 72-hour paid lookback.

This closes the **observation** half of the seam left by `Practitionist/familiarise_web`: Familiarise preserves event-time earning authority and reopens a completed payout's original earning after `payout.reversed`, but its poller does not independently revisit already-completed payouts. Epic Music Space independently revisits terminal payout state, but does not prove a correct same-original-earning reopen/re-pay path.

## Important semantic split
Do not equate every `transfer.reversed` with a worker/provider bank return. Epic Music Space documents its reversal path as a platform clawback commonly caused by refund/dispute and mirrors it as debit revenue splits. For EXP-010, plant two separate cases:

1. `BANK_RETURN_STILL_OWED` — provider/worker remains economically entitled; original earning/payable must reopen and be safely repayable from historical authority.
2. `REFUND_CLAWBACK_NOT_OWED` — underlying customer-side economics were reversed; provider entitlement should decrease rather than reopen for repayment.

## Strong negative oracle
`jedreekPrograms/dofast@284bc515c71477d890bb67ce49b7bb8c049694d4` has careful provider event identity, locking, exact wallet reserve/restore, and definitive settlement handling, but its state machine accepts `SUBMITTED -> PAID/FAILED` and same-terminal duplicates while rejecting `PAID -> FAILED` as contradictory. This is a useful regression oracle: sophisticated payout infrastructure can still be terminal-finality blind.

## Exact unanswered technical question
Can an independent readback observe a counter-event on an already-terminal payout, classify whether it is a bank return versus economic clawback, and—only for bank return—invoke the same idempotent historical-earning reopen used by the webhook path, with no current-rate lookup and no duplicate repayment?
