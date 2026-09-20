# V11 execution events

Each slot has its own optional append-only JSONL log under this directory:

`SLOT-01.jsonl` through `SLOT-14.jsonl`.

If a slot log does not exist, the current assignment is AVAILABLE.

## Atomic claim rule

For connector-driven execution, claiming is an optimistic-concurrency operation:

1. Fetch the slot event file if it exists.
2. Confirm the generated execution board says the slot is claimable.
3. Append exactly one `CLAIM` event.
4. Update the file using the exact blob SHA returned by the fetch.

If the file does not yet exist, create it with the first claim event. Two workers racing to create/update the same slot cannot both succeed against the same file version.

Do not rewrite or delete old events. Append only.

## Events

- `CLAIM` — acquire the exact assignment snapshot and a lease.
- `HEARTBEAT` — extend a live lease. It cannot revive an expired lease.
- `START` — mark active execution.
- `COMPLETE` — close the claim and name the V11 `search_run_id` carrying telemetry.
- `FAIL` — close the claim; `retryable=true` returns the assignment to the claimable pool.
- `RELEASE` — voluntarily close without completion.

Every event after CLAIM carries the same `claim_id` and `worker_id`.

## Lease rules

Default lease: 120 minutes.
Heartbeat extension: 120 minutes.
Maximum single lease/extension: 360 minutes.

A lease that expires becomes claimable again. A stale worker cannot later heartbeat or complete the expired claim.

## Completion handoff

A COMPLETE event is valid only if its `search_run_id` exists and that run records:

- schema_version >= 11;
- the same execution claim, worker and slot;
- the same assignment ID, allocator generation, work item and portfolio policy;
- V10 assignment role, work kind, source ID and score.

This makes successful execution inseparable from telemetry delivery.
