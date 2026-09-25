# Persistent Production Worker Contract

## Purpose

The Railway runtime is the always-on process for AI Business OS agent workers. Supabase remains the
durable queue and lease authority.

## Claim model

A worker may claim only:

- goals assigned to an ACTIVE agent;
- goals in PENDING state;
- goal types for which that runtime has an explicitly registered executor.

Each claim is atomic and receives a monotonically increasing lease generation. At most one live
leased goal exists per agent.

## Lease safety

Every heartbeat, submission, and failure report must match:

- goal ID;
- assigned agent ID;
- worker instance ID;
- run ID;
- lease generation;
- an unexpired lease.

Stale generations and expired leases fail closed. A database cron job requeues expired leases and
closes their run record as LEASE_EXPIRED.

## Completion boundary

Workers never write COMPLETE. Successful execution ends in VERIFYING with an output hash and
structured evidence references. Existing independent Auditor / Manager verification remains the only
path to COMPLETE.

## Executor registry

The runtime claims only goal types present in its in-process executor registry. The initial built-in
executor is SYSTEM_HEALTH_CHECK, which performs read-only health/planning reads and submits evidence.

No executor exists yet for commercial outreach, money movement, production deployment, destructive
operations, or arbitrary RESEARCH/REVENUE_MEASUREMENT goals. Those goals therefore cannot be
silently claimed by this worker.

## Failure behavior

Executor exceptions BLOCK the goal rather than creating an infinite retry loop. Process crashes are
different: if the lease expires without a terminal report, the recovery job requeues the goal for a
new generation.

## Deployment

The existing private Railway service remains the runtime host. The worker loop starts in the same
process and uses the existing authenticated Supabase runtime gateway. No Supabase database password
or service-role key is stored in Railway.
