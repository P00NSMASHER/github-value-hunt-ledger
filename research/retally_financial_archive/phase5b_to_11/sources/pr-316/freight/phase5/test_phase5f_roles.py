"""Phase 5F disposable PostgreSQL least-privilege proof.

This is not a live Floot credential switch. Tests role privileges in a
disposable PostgreSQL16 cluster and intentionally demonstrate that a privileged
'admission' role still CANNOT establish Ed25519 truth on its own. All attempted
writes occur in transactions that are rolled back.
"""
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import os
import unittest

import psycopg
from psycopg.types.json import Jsonb

ROOT=Path(__file__).parent
QA_SYSID="7694294930552894346"
PROD_SYSID="7693746749463444100"
APP="retally_p5f_untrusted_app"
ADMISSION="retally_p5f_independent_admission"


class Phase5FPrivilegeBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get("RETALLY_PHASE5_CI_DSN")
        if not cls.dsn:
            raise RuntimeError("DISPOSABLE_PG_DSN_REQUIRED")
        with closing(psycopg.connect(cls.dsn,autocommit=True)) as con:
            db,sysid=con.execute("SELECT current_database(),system_identifier::text FROM pg_control_system()").fetchone()
            if db!="retally_phase5_ci" or sysid in {QA_SYSID,PROD_SYSID}:
                raise RuntimeError("REFUSE_ANY_NONDISPOSABLE_OR_CONNECTED_PG")
            if con.execute("SELECT to_regclass('phase5c_qa.documents')").fetchone()[0] is None:
                raise RuntimeError("PHASE5C_INTEGRATION_MIGRATION_MISSING")
            sql=(ROOT/"phase5f_db_role_boundary.sql").read_text(encoding="utf8")
            guard="'"+QA_SYSID+"'"
            if sql.count(guard)!=1:
                raise RuntimeError("MIGRATION_GUARD_CHANGED")
            con.execute(sql.replace(guard,"'"+sysid+"'"))

    def con(self):
        return psycopg.connect(self.dsn,autocommit=True)

    def test_roles_no_login_and_not_privileged(self):
        with closing(self.con()) as con:
            rows=con.execute("""SELECT rolname,rolcanlogin,rolsuper,rolcreaterole,rolcreatedb,
                  rolbypassrls FROM pg_roles WHERE rolname IN (%s,%s)
                  ORDER BY rolname""",(APP,ADMISSION)).fetchall()
        self.assertEqual(len(rows),2)
        for name,*permissions in rows:
            self.assertFalse(any(permissions),(name,permissions))

    def test_untrusted_app_role_is_denied_financial_dml(self):
        with closing(self.con()) as con:
            for privilege in ("SELECT","INSERT","UPDATE","DELETE","TRUNCATE","REFERENCES","TRIGGER"):
                allowed=con.execute("SELECT has_table_privilege(%s,'phase5c_qa.documents',%s)",
                                    (APP,privilege)).fetchone()[0]
                self.assertFalse(allowed,(APP,privilege))
            self.assertTrue(con.execute("SELECT has_schema_privilege(%s,'phase5c_qa','USAGE')",
                                        (APP,)).fetchone()[0])

    def test_actual_set_role_context_cannot_read_financial_documents(self):
        with closing(self.con()) as con:
            con.execute("BEGIN")
            try:
                con.execute("SET LOCAL ROLE retally_p5f_untrusted_app")
                self.assertEqual(con.execute("SELECT current_user").fetchone()[0],APP)
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    con.execute("SELECT count(*) FROM phase5c_qa.documents")
            finally:
                con.rollback()

    def test_actual_set_role_context_cannot_insert_financial_documents(self):
        with closing(self.con()) as con:
            con.execute("BEGIN")
            try:
                con.execute("SET LOCAL ROLE retally_p5f_untrusted_app")
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    con.execute("""INSERT INTO phase5c_qa.documents(
                        tenant_id,case_id,record_id,kind,economic_key,amount_cents,
                        fee_bps,currency,occurred_at,source_sha256,issuer_key_id,
                        body,signature_b64)
                        VALUES('SIM-X','SIM-X','SIM-X','CONTRACT','SIM-X',0,3000,
                          'USD','2026-10-03','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                          'SIM-X','{}','AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')""")
            finally:
                con.rollback()

    def test_proposed_admission_role_can_insert_but_cannot_modify(self):
        with closing(self.con()) as con:
            for privilege in ("UPDATE","DELETE","TRUNCATE","REFERENCES","TRIGGER"):
                allowed=con.execute("SELECT has_table_privilege(%s,'phase5c_qa.documents',%s)",
                                    (ADMISSION,privilege)).fetchone()[0]
                self.assertFalse(allowed,(ADMISSION,privilege))
            self.assertTrue(con.execute("SELECT has_table_privilege(%s,'phase5c_qa.documents','INSERT')",
                                       (ADMISSION,)).fetchone()[0])

    def test_admission_role_denied_by_parent_case_row_lock_fail_closed(self):
        """INSERT grant alone cannot bypass the parent-case FOR UPDATE lock.
        This role currently cannot admit ANY document, even a legitimate one.
        Never grant broad UPDATE privilege to make this artificial test pass.
        An independent verifier service must own a narrowly controlled writer
        path and Ed25519 admission before the role is made operational.
        """
        with closing(self.con()) as con:
            con.execute("BEGIN")
            try:
                tenant="SIM-P5B-HANDLER-TENANT-A"
                case="SIM-P5F-UNTRUSTED-PROOF"
                con.execute("""INSERT INTO phase5c_qa.cases(
                     tenant_id,case_id,customer_id,invoice_id,carrier_id,currency,max_claim_cents)
                     VALUES(%s,%s,'SIM-P5F-CUSTOMER','SIM-P5F-INVOICE',
                     'SIM-P5F-CARRIER','USD',100)""",(tenant,case))
                signer=con.execute("""SELECT issuer_key_id FROM phase5c_qa.documents
                     WHERE tenant_id=%s AND kind='CONTRACT' LIMIT 1""",(tenant,)).fetchone()
                self.assertIsNotNone(signer)
                kid=signer[0]
                document={
                    "tenantId":tenant,"caseId":case,"recordId":"SIM-P5F-FAKE-SIGNATURE",
                    "customerId":"SIM-P5F-CUSTOMER","invoiceId":"SIM-P5F-INVOICE",
                    "kind":"CONTRACT","economicKey":"SIM-P5F-FAKE-ECO",
                    "referenceId":None,"amountCents":0,"feeBps":3000,
                    "currency":"USD","occurredAt":"2026-10-03T12:00:00Z",
                    "sourceHash":"a"*64,"issuerKeyId":kid,
                    "contractVersion":"SIM-V1","providerEventId":None
                }
                con.execute("SET LOCAL ROLE retally_p5f_independent_admission")
                self.assertEqual(con.execute("SELECT current_user").fetchone()[0],ADMISSION)
                with self.assertRaisesRegex(psycopg.errors.InsufficientPrivilege,
                                            "permission denied for table cases"):
                    con.execute("""INSERT INTO phase5c_qa.documents(
                      tenant_id,case_id,record_id,kind,economic_key,reference_id,
                      amount_cents,fee_bps,currency,occurred_at,source_sha256,issuer_key_id,
                      body,signature_b64) VALUES(%s,%s,%s,'CONTRACT',%s,NULL,0,3000,
                      'USD','2026-10-03T12:00:00Z',%s,%s,%s,%s)""",
                      (tenant,case,"SIM-P5F-FAKE-SIGNATURE","SIM-P5F-FAKE-ECO",
                       "a"*64,kid,Jsonb(document),"A"*88))
            finally:
                con.rollback()


if __name__=="__main__":
    unittest.main()
