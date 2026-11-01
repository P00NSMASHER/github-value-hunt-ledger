-- Phase 5G: disposable PostgreSQL only. Do not run against Floot QA or production.
-- In CI, only the explicit disposable database 'retally_phase5_ci' qualifies.
DO $guard$
BEGIN
 IF current_database() <> 'retally_phase5_ci'
 OR (SELECT system_identifier::text FROM pg_control_system()) IN
      ('7694294930552894346','7693746749463444100')
 OR to_regclass('phase5c_qa.documents') IS NULL
 THEN RAISE EXCEPTION 'PHASE5G_REFUSE_NONDISPOSABLE_DATABASE'; END IF;
END $guard$;

-- Harden the existing trigger: only the immutable financial table owner is
-- allowed to lock the parent case row. The intended verifier has INSERT only.
-- Trigger source from Phase 5C already sets search_path=pg_catalog,phase5c_qa
-- and uses fully-qualified SQL table references. Inspect this before adopting
-- in any non-test database.
ALTER FUNCTION phase5c_qa.guard_signed_financial_record()
 SECURITY DEFINER;

-- A SECURITY DEFINER trigger does NOT verify Ed25519; it only enforces the
-- economic constraints of the parent locked case. Genuine signature
-- validation occurs BEFORE insertion, in a separate Python verifier that
-- owns the only INSERT-capable runtime credential.
REVOKE ALL ON FUNCTION phase5c_qa.guard_signed_financial_record() FROM PUBLIC;
REVOKE ALL ON FUNCTION phase5c_qa.reject_mutation() FROM PUBLIC;
