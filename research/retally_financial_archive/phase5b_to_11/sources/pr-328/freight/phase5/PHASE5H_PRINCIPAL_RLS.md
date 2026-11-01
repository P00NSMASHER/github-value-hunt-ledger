# RETALLY Phase 5H: database-principal tenant isolation, disposable only

This phase extends Phase 5G's independently executable verifier with **real PostgreSQL row-level security scoped to the authenticated database principal**. It does not invent another ledger or replace payment processing. The change is CI-only. Production RecoveryOS and unpublished Floot QA were inspected READ ONLY for this phase.

## Verified starting point

Published production cluster: `7693746749463444100`. Unpublished Floot QA cluster: `7694294930552894346`. The actual QA application connects as `neondb_owner`, which also owns its financial evidence tables. Floot `list_resources` lists a single managed `FLOOT_DATABASE_URL` for this project; there is no independently configured restricted runtime credential or verifier service. `request_external_resource(POSTGRES)` would require the owner to explicitly supply a new connection string and attach it; we have not requested credentials or modified the active app.

## Implemented and executable

- `phase5h_principal_rls.sql`: disposable PostgreSQL 16 migration, guarded by exact `current_database()='retally_phase5_ci'` and exclusion of both real Floot clusters. Creates an administrator-controlled mapping from PostgreSQL authenticated `current_user` to a single fictional tenant. Enables RLS on the existing case, issuer-key and signed-document tables. Policies grant only matching tenant read/insert access to the Phase 5G verifier LOGIN. The role cannot change its mapping. The ordinary app login still has no financial table access.
- `test_phase5g_independent_verifier.py`: now applies that migration after creating the two independent LOGIN identities. Additional positive/negative tests verify RLS is actually enabled; foreign-tenant cases/issuer records are inaccessible; a separately signed foreign-tenant record cannot pass verifier case scoping; and direct foreign-tenant SQL insertion is denied by the database. The verifier cannot update its tenant mapping.
- Valid same-tenant signed CONTRACT admission, idempotent 12-request concurrent replay, invalid signature/wrong signer/revocation/unsupported fee tests remain in the original Phase 5G suite.

The policy is based on DB-authenticated `current_user`, not on user-provided financial tenant headers or a spoofable custom PostgreSQL session variable.

## Threat model and limitations

The Phase 5G verifier uses a restricted financial INSERT credential to publish **fictional buyer-signed CONTRACTs** after independent Ed25519 validation. The restricted credential remains a valuable secret: if stolen, an attacker with direct SQL access could bypass the Python verifier. RLS limits that attacker to its assigned tenant but does NOT establish signed evidence authenticity. The table owner can bypass RLS unless FORCE ROW LEVEL SECURITY and/or a genuinely non-owner runtime is used. The existing QA runtime is still the unrestricted `neondb_owner`.

This migration is intentionally NOT installed on hosted Floot QA or production because the real app lacks a separate scoped runtime connection. Applying RLS to the owner-owned financial schema while app is still `neondb_owner` would not provide trustworthy host isolation and could damage working experimental flows.

**Remaining acceptance gate:** separately controlled Floot application/verifier credentials, external genuine issuer authority, actual hosted RLS/session evidence, and complete customer-posted-credit/carrier-bank authenticity. Original 26 findings remain OPEN_UNVERIFIED. Customer A/B/C financial scenarios remain fictional; RETALLY actual recovery and revenue remain zero.

## Release verdict

**PASS for disposable tenant-scoped PostgreSQL verifier integration only. BLOCKED for live hosted credential and cryptographic admission isolation.** No merges, deployments, external carrier/bank actions, purchases, new scheduled tasks, or production writes.
