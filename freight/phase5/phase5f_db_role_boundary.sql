-- RETALLY Phase 5F RESEARCH ONLY. Do not run against published RecoveryOS.
-- Re-runnable on dedicated unpublished Floot QA cluster only. Disposable CI
-- replaces exactly the expected QA system_identifier in the guard.
DO $guard$
BEGIN
 IF (SELECT system_identifier::text FROM pg_control_system()) <> '7694294930552894346'
    OR current_database() NOT IN ('neondb','retally_phase5_ci')
    OR to_regclass('phase5c_qa.documents') IS NULL
 THEN RAISE EXCEPTION 'PHASE5F_REFUSE_UNVERIFIED_STAGING_DATABASE'; END IF;
END $guard$;

-- NOLOGIN roles prepare a least-privilege credential separation. They are not
-- active application credentials. No membership grant to neondb_owner occurs.
DO $create$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='retally_p5f_untrusted_app') THEN
   CREATE ROLE retally_p5f_untrusted_app NOLOGIN NOINHERIT;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='retally_p5f_independent_admission') THEN
   CREATE ROLE retally_p5f_independent_admission NOLOGIN NOINHERIT;
 END IF;
END $create$;

DO $assert$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles
   WHERE rolname IN ('retally_p5f_untrusted_app','retally_p5f_independent_admission')
     AND (rolcanlogin OR rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls))
 THEN RAISE EXCEPTION 'PRIVILEGED_OR_LOGIN_ROLE_UNSAFE'; END IF;
END $assert$;

REVOKE ALL ON SCHEMA phase5c_qa FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA phase5c_qa FROM PUBLIC;

-- Untrusted application principal can address the namespace but has NO access
-- to financial evidence tables, issuer keys, summary or mutation routines.
GRANT USAGE ON SCHEMA phase5c_qa TO retally_p5f_untrusted_app;
REVOKE ALL ON ALL TABLES IN SCHEMA phase5c_qa FROM retally_p5f_untrusted_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA phase5c_qa FROM retally_p5f_untrusted_app;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA phase5c_qa FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA phase5c_qa FROM retally_p5f_untrusted_app;

-- The separate NOLOGIN admission role is a TESTABLE FUTURE boundary. It can
-- validate/read scoped case and issuer reference tables and insert immutable
-- evidence, but cannot edit/delete/truncate. It does NOT itself verify Ed25519.
-- Only an independently authenticated verifier service may receive a LOGIN
-- identity/member grant after separate user-approved credential provisioning.
GRANT USAGE ON SCHEMA phase5c_qa TO retally_p5f_independent_admission;
GRANT SELECT ON phase5c_qa.cases,phase5c_qa.issuer_keys,phase5c_qa.documents
 TO retally_p5f_independent_admission;
GRANT INSERT ON phase5c_qa.documents TO retally_p5f_independent_admission;
REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
 ON phase5c_qa.documents FROM retally_p5f_independent_admission;

-- No GRANT of either NOLOGIN role to any existing principal.
-- CRITICAL: neondb_owner remains table owner and can still bypass Ed25519.
-- This migration alone does not fix the runtime owner-account connection.
