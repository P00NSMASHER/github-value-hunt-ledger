# Cross-lane referral — Hunt 01 → Money-State / Payment Integrity — 2026-09-20

## Candidate
`timboisvert/cocoscout@bf236883efc0d5ed56eccd75d6b046013a83012a`

## Why this matters
CocoScout implements a rare money-out counter-event path. A worker payout that was genuinely `paid` can later become `returned` after Stripe reports either `transfer.reversed` or a connected-account `payout.failed`. The implementation preserves the original payout ledger entry, posts a compensating reversal, restores the worker's payable balance, reopens the payout batch from completed to partially paid, clears `completed_at`, and preserves provider/cash-location distinctions. Webhook redelivery is idempotent and ambiguous amount-only bank returns fail closed instead of guessing which prior transfer to reverse.

This materially strengthens CAP-016/CAP-018 and the payroll side of EXP-010.

## Important limitation
CocoScout freezes contribution amount/source linkage but does not pin an explicit event-time pay-rate version onto the approved work event. Staff-pay construction looks up the current member/role rate. `synapp-dev/synapp@3e3d279f83f4972382a665b42cdc0989c83fd6d7` provides the complementary primitive: approved timesheet staging with `base_rate_cents` and pay-run `pay_rate_snapshot_cents`, but no verified later payout-return/reopen path.

## Exact unanswered technical question
**Can a later returned payroll payment be reconciled to an immutable pay-rate/timesheet snapshot without recomputing under current rates, and can the repayment preserve the same obligation/effect identity across retries?**

## Suggested EXP-010 additions
- exact transfer-ID reversal after apparent success;
- connected-account bank rejection days after transfer;
- ambiguous same-payee/same-amount return must not auto-match;
- original payout + compensating reversal both retained;
- completed run reopens and worker payable balance returns;
- platform-cash return distinguished from money still sitting in a payee/provider balance;
- duplicate webhook redelivery produces one counter-event;
- historical rate snapshot remains unchanged through return and repayment.

Full evidence: `hunters/01-run15-2026-09-20.md`.
