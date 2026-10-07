# RecoveryOS Disaster-Recovery Runbook

Version: 1.0  
Prepared: 2026-10-07

## Scope

This runbook covers application-level recovery of RecoveryOS evidence and
financial state. It is deliberately split into what Freight Recovery can verify
inside the application and what requires provider backup/restore evidence.

## Recovery priorities

1. Preserve source evidence and tenant boundaries.
2. Prevent writes while the integrity of the data plane is unknown.
3. Verify audit-chain continuity.
4. Restore authoritative freight/finding/review/payment state.
5. Reconcile provider-observed payment events before any money state is reported.
6. Resume writes only after semantic checks pass.

## Application-level semantic checks

After any recovery or database migration:

- every freight record must still bind to a tenant-owned population;
- every finding must still bind to its tenant/population;
- every review disposition must bind to a tenant-owned finding;
- payment instructions/authorizations/events must preserve tenant and lifecycle
  constraints;
- immutable evidence tables must still reject mutation;
- `recovery_verify_audit_chain(tenant_id)` must return zero invalid hashes and
  zero broken links for each restored tenant;
- current payment state must be recomputed from ordered provider events;
- a reversed settlement must not remain reported as settled;
- API-key rows may restore only hashes and revocation state, never plaintext
  tokens.

## Existing application-level recovery evidence

The repository already contains a semantic backup/restore drill for the local
audit + settlement stores. That test restores into fresh databases and compares
business semantics, rather than accepting a copied file as recovery proof.

The production RecoveryOS PostgreSQL data plane now adds independently
verifiable tenant constraints and audit-chain verification, but provider backup
and PITR evidence has not yet been captured.

## Production-provider drill required

Status: **PENDING_EXTERNAL**

Before setting a buyer-facing RPO/RTO or backup claim, obtain evidence for the
exact Floot/Neon RecoveryOS database and perform a controlled restore drill.

Required drill:

1. identify the production database and provider-supported recovery mechanism;
2. record backup/PITR retention window;
3. capture a pre-drill semantic manifest (tenant counts, evidence counts,
   payment-state counts, audit-chain heads);
4. restore to an isolated non-production target;
5. do not point production traffic at the restored target;
6. rerun tenant-isolation constraints;
7. verify each restored audit chain;
8. compare semantic manifest before/after;
9. verify payment lifecycle and reversal state;
10. record elapsed recovery time and effective recovery point;
11. destroy or retain the isolated restore according to the approved data
    handling policy;
12. preserve the drill artifact and hashes.

## RPO/RTO claim rule

Until that provider drill has been executed:

- RPO: **not externally evidenced**;
- RTO: **not externally evidenced**.

Do not invent an RPO/RTO from provider marketing, plan labels, or general cloud
expectations.

## Incident recovery

For suspected compromise, recovery is subordinate to evidence preservation.
Do not immediately overwrite/delete the affected environment if doing so would
destroy evidence needed to determine exposure, unless containment requires it.

Follow the incident-response state machine and notification authorization rules
before customer notification commitments are made.
