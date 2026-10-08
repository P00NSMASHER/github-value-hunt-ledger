# RETALLY Phase 5F | Restricted DB Roles and Unresolved Signature-Admission Bypass

Research-only draft stacked on Phase 5E PR #314. All test data fictional. Existing phase5c_qa database, not a new settlement engine.

## Exact database boundary

Published RecoveryOS: project c719b60c-9b3b-4193-a543-0be9d3ceaef2, PostgreSQL system identifier 7693746749463444100; no mutations in this mission.
Unpublished QA: project 7257eaf3-a4d7-43db-9136-fe81e5df35bf, identifier 7694294930552894346.

The QA Floot connection still uses current_user = neondb_owner; this also owns the phase5c_qa financial evidence tables. Active application credentials were not switched.

## Actual installed roles

Migration: freight/phase5/phase5f_db_role_boundary.sql. Guarded to the exact QA cluster; for disposable PostgreSQL CI the expected identifier is replaced only after checking the database name and independent system identifier.

- retally_p5f_untrusted_app is NOLOGIN, NOINHERIT, with schema USAGE but no SELECT, INSERT, UPDATE, DELETE, TRUNCATE or EXECUTE on protected finance resources.
- retally_p5f_independent_admission is NOLOGIN, NOINHERIT, with schema USAGE, SELECT on case, issuer and evidence tables, INSERT on evidence only, no UPDATE/DELETE/TRUNCATE. This is a FUTURE verifier principal, NOT an actual independent verifier and NOT a production credential.
- PUBLIC privileges on the financial schema were revoked; the table owner still has its owner powers.

Read-only queries to the actual isolated QA database observed the two roles have no login, superuser, create-role, create-database or bypass-RLS privileges. Actual role-level table privilege checks returned untrusted INSERT=false/SELECT=false/UPDATE=false, admission INSERT=true/SELECT=true/UPDATE=false.

IMPORTANT PROVIDER DETAIL: Neon automatically granted administrative membership in the new roles to neondb_owner, with admin_option=true, inherit_option=false and set_option=false. Attempting SET LOCAL ROLE through neondb_owner failed with permission denied. The current app remains the powerful owner, not the restricted role. Independent role session tests therefore execute in disposable PostgreSQL with an isolated superuser allowed to assume those NOLOGIN roles.

## Actual remaining attack surface

PostgreSQL pgcrypto does not verify Ed25519 signatures, and the QA database has no supported Ed25519 extension available. The existing QA TypeScript endpoint checks signatures; the phase5c_qa INSERT trigger checks financial conservation, issuer role, record scope and admission-time revocation, but does not cryptographically verify signature_b64.

Disposable PostgreSQL testing attempted to insert a forged signature-shaped CONTRACT under the prospective admission role. PostgreSQL correctly **denied** the attempt before any signature check: the financial trigger performs SELECT ... FOR UPDATE on the parent case, and that requires privileges the NOLOGIN admission role does not possess. This role therefore cannot currently insert legitimate or forged documents. We intentionally did NOT grant broad UPDATE permission on cases to make it work.

The prior Phase 5E test independently reproduced forged signature-shaped records being accepted under the unrestricted **table-owner** connection. That owner-level signature-verification bypass remains OPEN_UNMITIGATED. The Phase 5F restricted-role test proves a fail-closed boundary, not a production-ready verifier.

The unrestricted table owner can still bypass application checks. No role grant or SQL policy prevents the table owner from editing its own schema. A secure implementation requires the real application to use restricted database credentials, and a separate independently controlled Ed25519 verifier to be the only service authorized to insert signed financial evidence. Signed event authority and case ownership must be verified outside the general financial writer. No spoofable boolean, arbitrary GUC, or self-attested HMAC is an acceptable substitute.

Floot currently offers this connected QA project its managed FLOOT_DATABASE_URL; this work did not obtain a separate validated credential and did not reconfigure the running app to restricted credentials. Consequently this research DOES NOT CLOSE the owner-SQL bypass.

## Earlier evidence preserved

- Customer A: fictional $10 posted credit, $5 reversed, final $1.50 earned fee, $1 refund adjustment from Phase 5C.
- Customer B: signed fiction-only contract, zero recovered cash and no earned fee.
- Customer C: same zero supported recovery; negative commercial decision remains assumption-based.
- Historical D-07: original offline-research code reproduced/repaired in Phase 5D, still OPEN_UNVERIFIED for full historical/product closure.
- Historical findings: 26 remain formally OPEN_UNVERIFIED, real RETALLY revenue = $0.

## Release decision

PARTIAL DATABASE ROLE HARDENING RESEARCH ONLY. Financial cryptographic admission remains OPEN_UNMITIGATED until actual Floot runtime credential and independent verifier control are demonstrated. No production write, real money, carrier or customer interaction, application publication, merged PR or scheduled-task changes.
