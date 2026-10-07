# RecoveryOS Phase 3 — Security Test Evidence

Collected: 2026-10-07 UTC  
Target: Freight RecoveryOS production data-plane design  
Floot project: `c719b60c-9b3b-4193-a543-0be9d3ceaef2`  
Production URL: `https://freight-recoveryos.floot.app`

This file records tests actually executed while hardening Phase 3 Step 1. It does
not convert external assurance into an internal pass.

## Current production resources observed

The Floot project resource inventory showed exactly two connected application
resources relevant to RecoveryOS:

- `FLOOT_DATABASE_URL` — Floot-managed PostgreSQL database (Neon);
- `JWT_SECRET` — application authentication signing secret.

Secret values were not returned by the resource inventory.

The production app was observed as published at
`https://freight-recoveryos.floot.app`.

## Cross-tenant negative probe

A transaction-scoped synthetic test created two tenants:

- `p3_sec_tenant_a`;
- `p3_sec_tenant_b`.

Tenant A owned population `p3_pop_a`. The test then attempted to create a
tenant-B freight record whose `population_id` referenced tenant A.

Expected: database refusal.  
Observed: PostgreSQL foreign-key violation.  
Result: **PASS**.

The fixture was rolled back. No synthetic tenant/customer rows from this probe
were retained.

This proves the tested composite tenant/population constraint. It does not by
itself prove every possible application authorization path.

## Audit-chain probe

The same transaction caused normal insert triggers to append tamper-evident
audit events. `recovery_verify_audit_chain` recomputed event hashes and checked
link continuity.

Observed before rollback:

- tenant A events: 2;
- tenant A invalid hashes: 0;
- tenant A broken links: 0;
- tenant B events: 1;
- tenant B invalid hashes: 0;
- tenant B broken links: 0.

Result: **PASS**.

The audit writer obtains a per-tenant PostgreSQL advisory lock before reading
the chain head and appending a new event, preventing ordinary concurrent inserts
from silently forking the chain.

## Authentication hardening

Applied and typechecked in RecoveryOS:

- registration email normalized to lowercase;
- database unique index on `lower(email)`;
- minimum password length raised from 8 to 12;
- uppercase, lowercase and numeric requirements enforced server-side;
- login rate limiting retained;
- signed session lifetime aligned to 12 hours;
- database session expiry is explicitly checked;
- expired-session cleanup uses `expires_at`;
- cookies remain `HttpOnly; Secure; SameSite=Lax`;
- browser mutation requests enforce same-origin `Sec-Fetch-Site` / `Origin` when those headers are present, blocking cross-origin cookie-authenticated mutations.

This is password-authentication hardening. It is **not MFA**.

## API-key hardening

Applied and typechecked:

- plaintext token is generated once;
- only SHA-256 key digest is stored;
- scopes are now distinct: `ingest` and `payment_event`;
- a generic ingest key can no longer submit payment lifecycle events;
- active/revoked key metadata can be listed without secret values;
- owner-only revocation is implemented;
- revoked keys cannot be modified back into service;
- API-key creation/revocation participates in the tenant audit trail.

## API-key revocation audit-chain probe

A separate transaction-scoped probe created a synthetic tenant/API key, revoked
the key through the database guard, and ran `recovery_verify_audit_chain`.

Observed before rollback:

- events: 2 (create + revoke);
- invalid hashes: 0;
- broken links: 0.

Result: **PASS**.

The fixture was rolled back.

## Payment database controls

Previously implemented payment lifecycle controls remain in force:

- owner authorization is required;
- authorized amount must equal prepared instruction amount;
- provider event amount must match instruction amount;
- invalid state jumps are rejected;
- event chronology is enforced;
- payment instructions, authorizations and provider events are append-only.

## Parser boundary

The deployed RecoveryOS customer-data application currently accepts governed
canonical JSON through its application API. It does not expose the repository's
PDF/archive/document parsing code as a production parser runtime.

Therefore parser sandboxing is recorded as **NOT_APPLICABLE to the current
deployed runtime**, not as "proven sandboxing."

## External evidence deliberately not manufactured

No internal activity in this step is presented as:

- MFA evidence;
- enterprise SSO evidence;
- an independent penetration-test report;
- SOC 2 Type II;
- ISO/IEC 27001 certification;
- provider encryption attestation;
- provider backup/PITR/restore attestation.

Those remain `PENDING_EXTERNAL` in the machine-readable readiness snapshot.
