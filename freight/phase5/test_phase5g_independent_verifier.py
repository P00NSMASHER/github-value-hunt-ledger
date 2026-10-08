"""Real disposable Postgres16 LOGIN sessions with separately generated credentials.

Run AFTER Phase5C financial seed and Phase5F role migrations. Uses exclusively
retally_phase5_ci and refuses any of the connected Floot cluster identifiers.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime,timezone
from hashlib import sha256
import base64
import copy
import os
from pathlib import Path
import secrets
import unittest

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from freight.phase5.phase5c_oracle import signed_bytes
from freight.phase5.phase5g_independent_verifier import (
    AdmissionRejected,PinnedIssuer,admit_fictional_contract,
)

QA="7694294930552894346"
PRODUCTION="7693746749463444100"
APP="retally_p5g_app_login"
VERIFIER="retally_p5g_verifier_login"
ROOT=Path(__file__).parent


class Phase5GSeparatePrincipal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin_dsn=os.environ.get("RETALLY_PHASE5_CI_DSN")
        if not cls.admin_dsn:
            raise RuntimeError("MISSING_DISPOSABLE_DB_DSN")
        with closing(psycopg.connect(cls.admin_dsn,autocommit=True)) as con:
            db,cluster=con.execute(
                "SELECT current_database(),system_identifier::text FROM pg_control_system()"
            ).fetchone()
            if db!="retally_phase5_ci" or cluster in {QA,PRODUCTION}:
                raise RuntimeError("REFUSE_PRODUCTION_OR_HOSTED_QA")
            migration=(ROOT/"phase5g_disposable_definer.sql").read_text(encoding="utf8")
            if ("current_database() <> 'retally_phase5_ci'" not in migration or
                "ALTER FUNCTION phase5c_qa.guard_signed_financial_record()" not in migration or
                "SECURITY DEFINER" not in migration):
                raise RuntimeError("UNEXPECTED_QA_ONLY_MIGRATION")
            con.execute(migration)
            cls.app_secret=secrets.token_urlsafe(40)
            cls.verifier_secret=secrets.token_urlsafe(40)
            for principal,password in [(APP,cls.app_secret),(VERIFIER,cls.verifier_secret)]:
                con.execute(sql.SQL("""CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER
                   NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD {}""").format(
                    sql.Identifier(principal),sql.Literal(password)))
            con.execute(sql.SQL("GRANT USAGE ON SCHEMA phase5c_qa TO {}").format(
                sql.Identifier(APP)))
            con.execute(sql.SQL("GRANT USAGE ON SCHEMA phase5c_qa TO {}").format(
                sql.Identifier(VERIFIER)))
            con.execute(sql.SQL("""GRANT SELECT ON phase5c_qa.cases,
                phase5c_qa.issuer_keys,phase5c_qa.documents TO {}""").format(
                sql.Identifier(VERIFIER)))
            con.execute(sql.SQL("GRANT INSERT ON phase5c_qa.documents TO {}").format(
                sql.Identifier(VERIFIER)))
            # Crucially, there is NO grant from the table owner role and no
            # runtime SET ROLE ability to assume neondb_owner.
            for principal in (APP,VERIFIER):
                privileges=con.execute("""SELECT rolsuper,rolcreaterole,rolcreatedb,
                     rolbypassrls FROM pg_roles WHERE rolname=%s""",(principal,)).fetchone()
                if not privileges or any(privileges):
                    raise RuntimeError("PRINCIPAL_UNEXPECTEDLY_PRIVILEGED")
            # Phase 5H binds financial RLS to the real DB-authenticated
            # principal, never a client-provided tenant ID or spoofable GUC.
            rls=(ROOT/"phase5h_principal_rls.sql").read_text(encoding="utf8")
            if "current_database()<>'retally_phase5_ci'" not in rls:
                raise RuntimeError("MISSING_DISPOSABLE_TENANT_RLS_GUARD")
            con.execute(rls)
        cls.client_args=conninfo_to_dict(cls.admin_dsn)

    def connect(self,principal):
        cfg={**self.client_args,"user":principal,
             "password":self.app_secret if principal==APP else self.verifier_secret}
        return psycopg.connect(**cfg,autocommit=True)

    def setUp(self):
        suffix=secrets.token_hex(6).upper()
        self.tenant="SIM-P5B-HANDLER-TENANT-A"
        self.case_id="SIM-P5G-CASE-"+suffix
        self.record_id="SIM-P5G-CONTRACT-"+suffix
        self.issuer="SIM-P5G-BUYER-"+suffix
        self.private=Ed25519PrivateKey.generate()
        pem=self.private.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo).decode()
        self.pinned={self.issuer:PinnedIssuer(self.issuer,self.tenant,"BUYER",pem)}
        self.payload={
            "tenantId":self.tenant,"caseId":self.case_id,
            "recordId":self.record_id,"customerId":"SIM-P5G-CLIENT",
            "invoiceId":"SIM-P5G-INVOICE","kind":"CONTRACT",
            "economicKey":"SIM-P5G-ECON-"+suffix,"referenceId":None,
            "amountCents":0,"feeBps":3000,"currency":"USD",
            "occurredAt":"2026-10-03T12:00:00Z",
            "sourceHash":sha256(("SIM-ARTIFACT-"+suffix).encode()).hexdigest(),
            "issuerKeyId":self.issuer,"contractVersion":"SIM-P5G-V1",
            "providerEventId":None,
        }
        with closing(psycopg.connect(self.admin_dsn,autocommit=True)) as con:
            con.execute("""INSERT INTO phase5c_qa.cases(
                tenant_id,case_id,customer_id,invoice_id,carrier_id,
                currency,max_claim_cents)
                VALUES(%s,%s,'SIM-P5G-CLIENT','SIM-P5G-INVOICE',
                'SIM-P5G-CARRIER','USD',0)""",(self.tenant,self.case_id))
            con.execute("""INSERT INTO phase5c_qa.issuer_keys(
                tenant_id,key_id,role,public_key_pem,enabled_from,expires_at)
                VALUES(%s,%s,'BUYER',%s,'2026-09-01','2027-01-01')""",
                (self.tenant,self.issuer,pem))
        self.signature=self.private.sign(signed_bytes(self.payload))
        self.b64=base64.b64encode(self.signature).decode()

    def count(self):
        with closing(psycopg.connect(self.admin_dsn,autocommit=True)) as con:
            return con.execute("""SELECT count(*) FROM phase5c_qa.documents
                WHERE tenant_id=%s AND case_id=%s""",
                (self.tenant,self.case_id)).fetchone()[0]

    def test_real_distinct_credentials_and_names(self):
        with closing(self.connect(APP)) as app,closing(self.connect(VERIFIER)) as verifier:
            self.assertEqual(app.execute("SELECT current_user").fetchone()[0],APP)
            self.assertEqual(verifier.execute("SELECT current_user").fetchone()[0],VERIFIER)
            self.assertNotEqual(APP,VERIFIER)
        self.assertNotEqual(self.app_secret,self.verifier_secret)

    def test_application_login_cannot_read_or_insert_financial_evidence(self):
        with closing(self.connect(APP)) as app:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                app.execute("SELECT count(*) FROM phase5c_qa.documents")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                app.execute("""INSERT INTO phase5c_qa.documents(
                   tenant_id,case_id,record_id,kind,economic_key,amount_cents,
                   fee_bps,currency,occurred_at,source_sha256,issuer_key_id,
                   body,signature_b64)
                   VALUES('SIM-X','SIM-X','SIM-X','CONTRACT','SIM-X',
                   0,3000,'USD',now(),%s,'SIM-X','{}','AAAAAAAA')""",("a"*64,))
        self.assertEqual(self.count(),0)

    def test_valid_independently_signed_document_persists(self):
        with closing(self.connect(VERIFIER)) as connection:
            outcome=admit_fictional_contract(connection,self.payload,self.b64,self.pinned)
        self.assertFalse(outcome.replay)
        self.assertEqual(outcome.record_id,self.record_id)
        self.assertEqual(self.count(),1)

    def test_valid_duplicate_replay_is_idempotent(self):
        with closing(self.connect(VERIFIER)) as connection:
            first=admit_fictional_contract(connection,self.payload,self.b64,self.pinned)
            repeat=admit_fictional_contract(connection,self.payload,self.b64,self.pinned)
        self.assertFalse(first.replay)
        self.assertTrue(repeat.replay)
        self.assertEqual(self.count(),1)

    def test_simultaneous_valid_contracts_are_one_record(self):
        def submit(_):
            with closing(self.connect(VERIFIER)) as connection:
                return admit_fictional_contract(connection,self.payload,self.b64,self.pinned)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(submit,range(12)))
        self.assertEqual(sum(not result.replay for result in results),1)
        self.assertEqual(sum(result.replay for result in results),11)
        self.assertEqual(self.count(),1)

    def test_modified_signed_amount_fails_before_insert(self):
        tampered={**self.payload,"feeBps":4500}
        with closing(self.connect(VERIFIER)) as con:
            with self.assertRaisesRegex(AdmissionRejected,"INVALID_ED25519_FINANCIAL_SIGNATURE"):
                admit_fictional_contract(con,tampered,self.b64,self.pinned)
        self.assertEqual(self.count(),0)

    def test_wrong_tenant_pinned_issuer_fails(self):
        other={self.issuer:PinnedIssuer(self.issuer,"SIM-OTHER","BUYER",
                                      self.pinned[self.issuer].public_key_pem)}
        with closing(self.connect(VERIFIER)) as con:
            with self.assertRaisesRegex(AdmissionRejected,"UNKNOWN_OR_WRONG_SCOPE"):
                admit_fictional_contract(con,self.payload,self.b64,other)
        self.assertEqual(self.count(),0)

    def test_revoked_signer_is_denied_even_on_backdated_doc(self):
        with closing(psycopg.connect(self.admin_dsn,autocommit=True)) as con:
            con.execute("""UPDATE phase5c_qa.issuer_keys SET revoked_at='2026-10-06'
               WHERE tenant_id=%s AND key_id=%s""",(self.tenant,self.issuer))
        with closing(self.connect(VERIFIER)) as con:
            with self.assertRaisesRegex(AdmissionRejected,"REVOKED_OR_EXPIRED"):
                admit_fictional_contract(con,self.payload,self.b64,self.pinned)
        self.assertEqual(self.count(),0)

    def test_missing_trust_root_fails_even_when_db_key_valid(self):
        with closing(self.connect(VERIFIER)) as con:
            with self.assertRaisesRegex(AdmissionRejected,"UNKNOWN_OR_WRONG_SCOPE"):
                admit_fictional_contract(con,self.payload,self.b64,{})
        self.assertEqual(self.count(),0)

    def test_no_unverified_fee_collection_in_zero_recovery_case(self):
        invalid={**self.payload,"kind":"FEE_INVOICE","amountCents":100,
                 "feeBps":None,"recordId":self.record_id+"-FEE"}
        signed=base64.b64encode(self.private.sign(signed_bytes(invalid))).decode()
        with closing(self.connect(VERIFIER)) as con:
            with self.assertRaisesRegex(AdmissionRejected,"UNSUPPORTED_FINANCIAL_DOCUMENT_KIND"):
                admit_fictional_contract(con,invalid,signed,self.pinned)
        self.assertEqual(self.count(),0)

    def test_direct_verifier_sql_remains_a_credential_theft_risk(self):
        """Do NOT treat the DB credential as a cryptographic validation API.

        Test uses a transaction rollback. A party stealing the verifier
        credential could bypass the Python verifier and write a forged
        contract. Production credential separation must protect this secret.
        """
        from psycopg.types.json import Jsonb
        with closing(self.connect(VERIFIER)) as con:
            con.execute("BEGIN")
            try:
                con.execute("""INSERT INTO phase5c_qa.documents
                  (tenant_id,case_id,record_id,kind,economic_key,reference_id,
                   amount_cents,fee_bps,currency,occurred_at,source_sha256,
                   issuer_key_id,body,signature_b64)
                   VALUES(%s,%s,%s,'CONTRACT',%s,NULL,0,3000,'USD',
                          '2026-10-03T12:00:00Z',%s,%s,%s,%s)""",
                   (self.tenant,self.case_id,self.record_id,
                    self.payload["economicKey"],self.payload["sourceHash"],
                    self.issuer,Jsonb(self.payload),"A"*88))
                self.assertEqual(self.count(),0)
                self.assertEqual(con.execute("""SELECT signature_b64
                     FROM phase5c_qa.documents WHERE record_id=%s""",
                     (self.record_id,)).fetchone()[0],"A"*88)
            finally:
                con.rollback()
        self.assertEqual(self.count(),0)


    def test_database_tenant_rls_prevents_cross_tenant_read(self):
        with closing(psycopg.connect(self.admin_dsn,autocommit=True)) as owner:
            owner.execute("""INSERT INTO phase5c_qa.cases
                (tenant_id,case_id,customer_id,invoice_id,carrier_id,currency,max_claim_cents)
                VALUES('SIM-OTHER-TENANT',%s,'SIM-OTHER-CUSTOMER',
                       'SIM-OTHER-INVOICE','SIM-OTHER-CARRIER','USD',0)""",
                       (self.case_id,))
        with closing(self.connect(VERIFIER)) as verifier:
            rows=verifier.execute("""SELECT case_id FROM phase5c_qa.cases
                          WHERE tenant_id='SIM-OTHER-TENANT'""").fetchall()
            self.assertEqual(rows,[])
            self.assertEqual(verifier.execute("""SELECT count(*) FROM phase5c_qa.issuer_keys
                          WHERE tenant_id='SIM-OTHER-TENANT'""").fetchone()[0],0)

    def test_database_authenticated_principal_denies_cross_tenant_insert(self):
        # Even a correctly signed body and previously pinned foreign tenant
        # root cannot bypass the role's principal->tenant mapping.
        foreign={**self.payload,"tenantId":"SIM-OTHER-TENANT"}
        sig=base64.b64encode(self.private.sign(signed_bytes(foreign))).decode()
        with closing(psycopg.connect(self.admin_dsn,autocommit=True)) as owner:
            owner.execute("""INSERT INTO phase5c_qa.cases
                (tenant_id,case_id,customer_id,invoice_id,carrier_id,currency,max_claim_cents)
                VALUES('SIM-OTHER-TENANT',%s,'SIM-P5G-CLIENT',
                       'SIM-P5G-INVOICE','SIM-P5G-CARRIER','USD',0)""",(self.case_id,))
            owner.execute("""INSERT INTO phase5c_qa.issuer_keys
                (tenant_id,key_id,role,public_key_pem,enabled_from,expires_at)
                VALUES('SIM-OTHER-TENANT',%s,'BUYER',%s,'2026-09-01','2027-01-01')""",
                (self.issuer,self.pinned[self.issuer].public_key_pem))
        with closing(self.connect(VERIFIER)) as verifier:
            with self.assertRaisesRegex(AdmissionRejected,"INDEPENDENT_CASE_SCOPE_MISMATCH"):
                admit_fictional_contract(verifier,foreign,sig,
                    {self.issuer:PinnedIssuer(self.issuer,"SIM-OTHER-TENANT",
                        "BUYER",self.pinned[self.issuer].public_key_pem)})
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                verifier.execute("""INSERT INTO phase5c_qa.documents(
                    tenant_id,case_id,record_id,kind,economic_key,reference_id,
                    amount_cents,fee_bps,currency,occurred_at,source_sha256,
                    issuer_key_id,body,signature_b64)
                    VALUES(%s,%s,%s,'CONTRACT',%s,NULL,0,3000,'USD',
                        '2026-10-03T12:00:00Z',%s,%s,%s,%s)""",
                    ("SIM-OTHER-TENANT",self.case_id,self.record_id,
                     self.payload["economicKey"],self.payload["sourceHash"],
                     self.issuer,Jsonb(foreign),sig))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                # The verifier cannot edit its principal->tenant mapping.
                verifier.execute("""UPDATE phase5h_qa.principal_tenants
                                    SET tenant_id='SIM-OTHER-TENANT'
                                    WHERE principal_name=%s""",(VERIFIER,))
        self.assertEqual(self.count(),0)

    def test_principal_bound_rls_is_enabled_on_all_three_tables(self):
        with closing(psycopg.connect(self.admin_dsn,autocommit=True)) as owner:
            rows=owner.execute("""SELECT relname,relrowsecurity FROM pg_class
                          WHERE oid IN ('phase5c_qa.cases'::regclass,
                                        'phase5c_qa.issuer_keys'::regclass,
                                        'phase5c_qa.documents'::regclass)""").fetchall()
            self.assertEqual(len(rows),3)
            self.assertTrue(all(enabled for _,enabled in rows))
            assigned=owner.execute("""SELECT tenant_id FROM phase5h_qa.principal_tenants
                    WHERE principal_name=%s""",(VERIFIER,)).fetchone()[0]
            self.assertEqual(assigned,"SIM-P5B-HANDLER-TENANT-A")


if __name__=="__main__":
    unittest.main()
