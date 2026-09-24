# Upgrade 8 — Autonomous Software Factory

Status: **IMPLEMENTED**

The Business OS now has a durable software work queue modeled on the strongest
orchestration concepts Hunter identified in OpenAI Symphony.

Each approved engineering item follows a constrained state machine:

```
QUEUED
  -> RUNNING in a unique workspace
  -> VERIFYING
  -> READY_FOR_PR
  -> PR_OPEN
  -> MERGED
```

Failed or stale attempts are requeued until the configured retry limit is
exhausted, after which the item becomes BLOCKED.

## Independent completion boundary

An executor submission cannot become PR-ready by self-assertion. The factory
requires an Upgrade-2 AuditReceipt that:
- binds to the exact acceptance contract;
- binds to the exact executor submission;
- has verdict ACCEPTED;
- comes from an auditor other than the executor.

## Crash/restart behavior

Active attempts use leases. Reconciliation after a process restart identifies
expired RUNNING or VERIFYING attempts, closes their run record and either
requeues them into a fresh isolated workspace or blocks them at the retry
limit.

## Production boundary

The factory records that an externally created PR or merge occurred. It does
not bypass Upgrade-7 governance or directly grant itself production merge
authority.
