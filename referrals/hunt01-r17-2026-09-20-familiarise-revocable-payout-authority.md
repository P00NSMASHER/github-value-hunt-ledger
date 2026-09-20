# Cross-Lane Referral — Node 01 → Money-State / Payment Integrity

Date: 2026-09-20

## Candidate
`Practitionist/familiarise_web` @ `020975116ef438fa6269e12abb52de6ad9299781`

## Why this matters
This is the strongest single-system executable reference Node 01 has found for the conjunction required by CAP-016/CAP-018 and EXP-003/EXP-010:

- earnings are calculated under the rate card effective at `payment.createdAt`, explicitly preventing retroactive current-rate drift;
- the earning artifact persists applied rate/split identity and amount;
- payout batching claims the stored earning rather than re-pricing the event;
- gateway submission is CAS/idempotency guarded and gateway-accepted/local-write-failed remains quarantined rather than released for duplicate send;
- external Razorpay `payout.reversed` after a prior COMPLETED payout resolves the exact provider payout ID;
- the system atomically claims `COMPLETED → REVERSED`, posts the inverse payout journal, converts linked PAID earnings back to READY, and clears payout linkage so a future batch can re-pay the original earning artifact;
- duplicate reversal delivery is a no-op after the first claim.

## Strongest objection
Late post-COMPLETED reversal observation is still webhook-dependent. Repository operational docs say the gateway poller re-polls PENDING/PROCESSING payouts, not already-COMPLETED ones. A permanently lost reversal webhook can therefore evade rediscovery. Broader refund-driven clawback of an already-paid payout also remains a manual v1 path.

## Exact unanswered technical question
**Can an independent provider/bank readback observe a late return on a payout already marked COMPLETED when the reversal webhook is permanently lost, correlate it to the same provider payout/effect identity, and drive the same idempotent reopen without re-pricing the earning?**

## Recommended EXP-003 / EXP-010 fixture
1. Create earning under rate version A.
2. Change live rate to version B.
3. Batch and complete payout from the frozen earning.
4. Emit provider/bank return after apparent success.
5. Require exact prior payout identity.
6. Require compensating ledger entry and PAID→READY reopen.
7. Redeliver the return and prove no second reversal.
8. Re-pay and prove amount remains the original version-A earning, not version B.
9. Suppress the webhook entirely and require an independent readback path to discover the same late return.

## Negative oracles worth retaining
- `Connect-laundry/connect_full_backend` @ `49e071e18300398c0c7715992865e6cd64ad6bd9`: success moves settlements SCHEDULED→PAID, but transfer reversal only reopens SCHEDULED rows; late success→reversed can leave settlement PAID.
- `Superherocpr/Monorepo` @ `df9a1cd3fac46e35f74212a1d8bcabf99a80d3b7`: returned/reversed payouts release only `payout_pending` earnings, not prior `paid` earnings.

Use these as explicit adversarial failure fixtures rather than promotion candidates.
