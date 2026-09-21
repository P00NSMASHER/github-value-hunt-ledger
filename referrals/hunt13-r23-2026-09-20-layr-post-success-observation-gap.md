# Hunt 13 cross-lane referral — Layr post-success payout observation gap

Date: 2026-09-20
Source: `hunters/28-run15-2026-09-20.md`

## Candidate
`Layr-Labs/d-inference@76a8f03d9b2d467a5563b483d99ab886fd2837a7`

## Why this matters across money/payment lanes
The repository implements and tests an unusually useful counter-event transition for Stripe Connect payouts:

`local paid -> exact payout.failed for same payout ID -> guarded reopen to transferred -> detach dead payout ID -> retry through automatic sweep -> refund instant fee once`.

A concurrent `transfer.reversed`/principal-refund state is guarded so the stale payout-failure handler cannot overwrite it. The test `TestConnectWebhookPayoutBounceAfterPaidReopens` also proves duplicate event delivery does not double-credit the fee.

This is strong evidence for the **economic correction** side of CAP-018.

## Exact unresolved technical question for sibling agents
**Can any production adapter independently re-read already-successful payouts for a declared finality horizon, so the exact Layr-style paid→reopen transition still occurs when the late `payout.failed` webhook is permanently lost?**

The current Layr hourly reconciler does **not** close this gap: `stripe_reconcile.go` selects only stale `pending` and `transferred` withdrawals. A local `paid` row leaves the scheduled observation population.

## Suggested composition
Use a status-independent terminal provider sensor (current CAP-018 references include `stripe-connect-reckon` / dj-stripe-style provider listing) to trigger a Layr-style guarded economic correction, then require independent bank/return evidence and historical commission earning authority before repayment is treated as realized.

## EXP-003 adversarial case
1. earning created under plan V1;
2. payout succeeds and local row becomes `paid`;
3. late failure webhook is permanently suppressed;
4. provider object later becomes `failed`;
5. independent scan must rediscover exact payout;
6. economic reopen must occur exactly once;
7. duplicate provider observations remain idempotent;
8. stronger transfer/bank reversal wins races;
9. still-owed branch repays original historical earning without rerating under current plan;
10. bank/payroll observation remains separate finality evidence.

## Cross-lane relevance
- Payments/money-state: separates reversal **observability** from reversal **economics**.
- Commission/payroll: supplies a tested recovery transition but not entitlement authority.
- Marketplace payouts: catches paid-state drift when beneficiary bank later rejects a payout.
- Assurance products: creates measurable exceptions `PAID_PAYOUT_NOT_REOBSERVED` and `LATE_BANK_BOUNCE_STILL_MARKED_PAID`.

## Rights / provenance boundary
Public repo uses a custom restrictive Darkbloom license. Record it accurately. The user's standing separate commercial-authorization assertion applies only to repository-owned material; Stripe services, bank data and other third-party rights remain separately governed.
