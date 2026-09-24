# Upgrade 1 — Persistent Agent Runtime

Status: **IMPLEMENTED**

This folder is the durable worker substrate for the AI Business OS.

## Why this exists

Short-lived agent calls lose execution state when a process crashes or a chat ends. The runtime here preserves the control state outside the model so a worker can resume safely.

The design adopts the strongest pattern identified by the Hunter research around `PrimeIntellect-ai/prime-agent` while keeping the first integration stdlib-only and independently testable.

Pinned Hunter reference:
- `PrimeIntellect-ai/prime-agent@e311d6495124cf0bdc629c813fc97a39a9a3054d`
- Hunter classification at inspection: MIT; persistent goals, sessions, subagents, skills, heartbeats, refinement and rollback.

This repository does **not** copy Prime Agent code. It implements the minimum control contract needed for the Business OS and leaves model/runtime adapters replaceable.

## Implemented invariants

1. Durable worker identity and role registration.
2. Durable goals in SQLite.
3. Priority scheduling.
4. Exclusive goal leases.
5. Lease generations to reject stale workers.
6. Worker heartbeats that extend only the current lease.
7. Automatic recovery/requeue after a crashed worker's lease expires.
8. Immutable run history rows for each claim generation.
9. A stale worker cannot commit success after another worker reclaims the goal.
10. Runtime status dashboard.

## Example

```python
from business_os.agents.persistent_runtime import PersistentAgentRuntime

rt = PersistentAgentRuntime("business-os.sqlite3")
rt.register_agent("research-1", "RESEARCH")

rt.enqueue_goal(
    "Find qualified freight-recovery prospects",
    {"business": "freight-recovery", "minimum_count": 20},
    priority=50,
)

goal = rt.claim_next_goal("research-1", lease_seconds=300)
assert goal is not None

# Worker does bounded work, heartbeating while active.
goal = rt.heartbeat(
    "research-1",
    goal.id,
    goal.lease_generation,
    extend_seconds=300,
)

rt.complete_goal(
    "research-1",
    goal.id,
    goal.lease_generation,
    {"qualified_prospects": 23},
)
```

## What this step intentionally does not do

- No credentials.
- No unrestricted shell access.
- No production deploy rights.
- No email/send authority.
- No money movement.
- No self-modification.
- No LLM-as-judge completion gate.

Those are separate upgrades so the authority surface stays understandable and testable.

## Acceptance test

```bash
python -m unittest business_os.tests.test_persistent_runtime -v
```

A step is complete only if lease ownership, crash recovery, generation fencing, persistence, priority ordering and terminal-state behavior are covered by regression tests.
