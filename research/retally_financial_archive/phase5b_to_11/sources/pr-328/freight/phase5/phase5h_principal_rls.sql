-- RETALLY PHASE 5H: tenant isolation tied to the authenticated PostgreSQL
-- principal. DISPOSABLE CI ONLY. Never apply to hosted Floot directly.
-- Requires Phase5C, Phase5F, and Phase5G test identities to exist.
DO $guard$ BEGIN
  IF current_database()<>'retally_phase5_ci'
  OR (SELECT system_identifier::text FROM pg_control_system()) IN
       ('7694294930552894346','7693746749463444100')
  OR NOT EXISTS(SELECT 1 FROM pg_roles
                WHERE rolname='retally_p5g_verifier_login' AND rolcanlogin AND NOT rolbypassrls)
  THEN RAISE EXCEPTION 'REFUSE_NONDISPOSABLE_OR_UNVERIFIED_VERIFIER_ROLE'; END IF;
END $guard$;

CREATE SCHEMA IF NOT EXISTS phase5h_qa;
CREATE TABLE IF NOT EXISTS phase5h_qa.principal_tenants(
  principal_name name PRIMARY KEY,
  tenant_id text NOT NULL CHECK(tenant_id LIKE 'SIM-%')
);

REVOKE ALL ON SCHEMA phase5h_qa FROM PUBLIC;
REVOKE ALL ON phase5h_qa.principal_tenants FROM PUBLIC;
GRANT USAGE ON SCHEMA phase5h_qa TO retally_p5g_verifier_login;
GRANT SELECT ON phase5h_qa.principal_tenants TO retally_p5g_verifier_login;
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON phase5h_qa.principal_tenants
 FROM retally_p5g_verifier_login;

-- Must be independently configured by an administrator, never by an
-- application-provided tenant ID or a freely-settable custom GUC.
INSERT INTO phase5h_qa.principal_tenants(principal_name,tenant_id)
VALUES ('retally_p5g_verifier_login','SIM-P5B-HANDLER-TENANT-A')
ON CONFLICT(principal_name) DO NOTHING;

ALTER TABLE phase5c_qa.cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE phase5c_qa.issuer_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE phase5c_qa.documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS phase5h_case_verifier_scope ON phase5c_qa.cases;
CREATE POLICY phase5h_case_verifier_scope ON phase5c_qa.cases
  TO retally_p5g_verifier_login
  USING( EXISTS(SELECT 1 FROM phase5h_qa.principal_tenants p
                WHERE p.principal_name=current_user AND p.tenant_id=cases.tenant_id));

DROP POLICY IF EXISTS phase5h_issuer_verifier_scope ON phase5c_qa.issuer_keys;
CREATE POLICY phase5h_issuer_verifier_scope ON phase5c_qa.issuer_keys
  TO retally_p5g_verifier_login
  USING( EXISTS(SELECT 1 FROM phase5h_qa.principal_tenants p
                WHERE p.principal_name=current_user AND p.tenant_id=issuer_keys.tenant_id));

DROP POLICY IF EXISTS phase5h_doc_verifier_read_scope ON phase5c_qa.documents;
CREATE POLICY phase5h_doc_verifier_read_scope ON phase5c_qa.documents
  FOR SELECT TO retally_p5g_verifier_login
  USING( EXISTS(SELECT 1 FROM phase5h_qa.principal_tenants p
                WHERE p.principal_name=current_user AND p.tenant_id=documents.tenant_id));

DROP POLICY IF EXISTS phase5h_doc_verifier_insert_scope ON phase5c_qa.documents;
CREATE POLICY phase5h_doc_verifier_insert_scope ON phase5c_qa.documents
  FOR INSERT TO retally_p5g_verifier_login
  WITH CHECK( EXISTS(SELECT 1 FROM phase5h_qa.principal_tenants p
                    WHERE p.principal_name=current_user AND p.tenant_id=documents.tenant_id));

-- Default deny for other roles lacking ownership/BYPASSRLS; existing owner
-- is NOT restricted by this RLS. That is the critical remaining hosted gap.
-- Existing Phase5G disposable SECURITY DEFINER trigger still runs as owner
-- to preserve the locked parent-case invariants. An independent live
-- verifier and restricted application runtime are not installed in Floot.
