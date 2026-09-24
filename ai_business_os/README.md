# AI Business OS

This directory is the incremental implementation of the nine-part AI Business OS upgrade.

## Step 1 — Persistent agent runtime

Status: implemented on this branch.

The first upgrade adds a durable worker substrate with:

- persistent agent identities and roles;
- durable goals with explicit state transitions;
- heartbeats and generation numbers for stale-worker recovery;
- append-only, hash-chained event history;
- snapshots and rollback-safe state restoration;
- parent/child agent relationships for delegated workers;
- process-restart persistence via SQLite;
- no dependency on an LLM provider or external service.

The runtime is intentionally authority-light. It records and coordinates work, but it does **not**
grant production, email, payment, merge, or destructive permissions. Those are added by later
governance/approval upgrades.

### Run the self-test

```bash
python -m unittest ai_business_os.persistent_agents.test_runtime
```

### Design rule

Persistent memory is evidence, not authority. A worker can remember prior outcomes, but later
verification and promotion gates determine whether those lessons become shared policy.
