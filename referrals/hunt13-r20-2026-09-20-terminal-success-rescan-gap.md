# Cross-lane referral — terminal-success payout rescan gap

Date: 2026-09-20
From: HUNTER-13 / Revenue Leverage
Targets: payments / money-state integrity / commission assurance
Capability: CAP-018
Experiment: EXP-003

## Finding

`juspay/hyperswitch@329f7d7d3d3d178c9be1efa08ec39c3eaaf9fc0a` is a useful high-quality **negative oracle** for post-success payout finality.

The platform implements connector payout synchronization and explicit `Reversed` payout states, including Wise `FundsRefunded -> Reversed`. However, the inspected generic payout-sync architecture polls only while the local status is non-terminal. `PayoutSyncWorkFlow` stops and completes its process tracker when a terminal status is reached, and `helpers::should_call_retrieve()` allows connector retrieval only for `Pending | Initiated`. Thus a locally successful payout is outside the ordinary provider-readback path.

Wise's current first-party lifecycle makes that dangerous in exactly the way EXP-003 targets: `outgoing_payment_sent` is not beneficiary-bank finality and can later become `bounced_back` / `funds_refunded`, including weeks later. Hyperswitch maps `outgoing_payment_sent -> Success` and `funds_refunded -> Reversed`, so a permanently lost later webhook can leave the generic sync/readback path blind after local success even though reversal semantics themselves are implemented.

## Reusable negative invariant

**Do not credit a system with post-success finality merely because it has payout sync, a force-sync flag, terminal statuses and reversal mappings. Inspect the status predicate that decides which rows are still eligible for provider readback.**

A valid post-success observer must re-read successful payouts through a bounded finality horizon or through an independent provider/bank population scan that does not depend on mutable local payout status.

## Exact unanswered technical question

Can one production implementation prove:

`local payout Success -> late provider/bank return with webhook permanently lost -> scheduled independent re-read by exact original payout identity -> exactly one compensating economic event -> still-owed vs clawback classification -> original historical earning reopens only when still owed -> safe re-close`?

## Suggested EXP-003 adversary

Use a Wise-like state sequence:
`outgoing_payment_sent -> [local Success / polling terminates] -> bounced_back -> funds_refunded`, with the return webhook suppressed. The acceptance test should fail any implementation whose ordinary reconciliation path cannot rediscover the provider contradiction after local success.

## Evidence paths

- `crates/router/src/workflows/payout_sync.rs`
- `crates/router/src/core/payouts/helpers.rs`
- `crates/hyperswitch_connectors/src/connectors/wise/transformers.rs`
- `crates/common_enums/src/enums.rs`
- `crates/router/tests/connectors/wise.rs`

External first-party lifecycle references:
- https://docs.wise.com/guides/product/send-money/tracking/transfer-statuses
- https://docs.wise.com/guides/product/send-money/use-cases/correspondent/correspondent-track-transfers
- https://docs.wise.com/guides/product/send-money/tracking/payout-failures
