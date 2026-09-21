# Hunt 13 referral — PayPal late-return two-predicate gap — 2026-09-20

## Referral target
Payments / finance / commission-payout assurance lanes working CAP-018 / EXP-003.

## Finding
`Superherocpr/Monorepo@df9a1cd3fac46e35f74212a1d8bcabf99a80d3b7` is a high-value negative oracle because it demonstrates two independent ways a mature payout subsystem can mishandle a late counter-event after success.

1. **Observation horizon:** the hourly/admin reconciliation route polls only local `assumed_complete`, `failed`, and `needs_review` batches. `completed` is explicitly terminal and excluded, so a permanently lost later PayPal RETURNED/REFUNDED webhook cannot be independently rediscovered.
2. **Economic transition:** the shared reconciler correctly maps PayPal RETURNED/REFUNDED/REVERSED to local `denied`, but its earning-release UPDATE only admits current `payout_pending`. A prior SUCCESS has already moved the earning to `paid`, so an observed late counter-event can fail to reopen the already-paid earning.

The repository also has strong surrounding controls—atomic reservation, immutable attempt rows, webhook replay protection, denial provenance, retry lineage, shared provider re-read—which makes the negative result more useful than a toy implementation.

## External provider check
PayPal's current first-party Payouts docs list `SUCCESS`, `RETURNED`, `REFUNDED`, and `REVERSED` payout-item states, and publish distinct RETURNED/REFUNDED webhooks. Unclaimed payouts can return after 30 days. Therefore late counter-events are part of the provider model, even though not every SUCCESS item is asserted to transition later.

## Cross-lane implication
Treat these as separate acceptance capabilities:
- reversal semantics;
- post-success reversal observability;
- idempotent economic correction from the actual success state.

Do not infer one from another.

## Exact unanswered technical question
**Can one production implementation keep successful payouts in an independent observation set through a defined finality horizon and, after a permanently lost or late provider/bank return, idempotently repair the exact historical earning from `paid` rather than only from a pre-success state?**

## Suggested EXP-003 tests
- SUCCESS -> local paid; suppress late RETURNED webhook; independent scheduled observer must rediscover it.
- SUCCESS -> local paid; deliver late RETURNED/REFUNDED; exact earning must reopen/compensate exactly once.
- Replay provider state/event; no duplicate compensation.
- Mixed successful/returned items; only exact linked earning changes.
- Explicit finality-horizon expiration policy with evidence.

## Commercial relevance
Potential audit exceptions:
- `TERMINAL_SUCCESS_NOT_REOBSERVED`
- `LATE_RETURN_DOES_NOT_REOPEN_PAID_EARNING`

These map directly to duplicate-payment risk, unpaid-but-marked-paid balances, close/reconciliation drift, and unsafe manual reissues.

## Rights/provenance
Repository is public; no root LICENSE was found at the inspected revision. Repository-owned code is covered only by the user's standing separate commercial authorization. PayPal service/API/data rights are separate and not inferred.