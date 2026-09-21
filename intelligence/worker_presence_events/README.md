# V16 worker presence events

Each registered worker may maintain an append-only presence log:

`intelligence/worker_presence_events/HUNTER-XX.jsonl`

No file means **UNKNOWN**. Unknown is not a negative performance signal.

## Events

- `READY` — worker is awake and willing to accept one generated assignment.
- `HEARTBEAT` — extend a current READY lease.
- `BUSY` — worker is temporarily unavailable outside the V11 claim state.
- `PAUSE` — explicit operator/worker pause.
- `OFFLINE` — explicit shutdown.

READY/HEARTBEAT use the TTL in `worker_presence_policy.json` unless an event supplies a smaller valid TTL.

V11 active claims remain authoritative: a worker with a live claim derives `ACTIVE_CLAIM` regardless of the latest presence event.

Use `tools/ti_worker_presence_event.py` to append local presence events. Commit/push the append-only event before relying on it for generated activation.
