# Persistent Worker Contract — Step 1

Every long-lived worker must follow these invariants.

1. **Durable identity** — each worker has a stable agent ID, role, generation, and optional parent.
2. **Durable goal state** — tasks use explicit PENDING/ACTIVE/BLOCKED/VERIFYING/COMPLETE/CANCELLED states.
3. **No false completion** — PENDING cannot jump directly to COMPLETE; a goal must reach VERIFYING first.
4. **Heartbeats** — long-lived workers refresh liveness; stale workers can be reclaimed by incrementing generation.
5. **Append-only evidence** — material actions emit events into a per-agent SHA-256 hash chain.
6. **Rollback without erasure** — snapshots restore operational state but never erase historical events.
7. **Delegation lineage** — subagents are linked to a parent agent.
8. **Memory is not authority** — prior events and state can inform future work but cannot independently authorize consequential actions.
9. **Later controls remain mandatory** — production writes, outbound communication, money movement, destructive actions, and policy promotion are outside Step 1 and must remain separately gated.
