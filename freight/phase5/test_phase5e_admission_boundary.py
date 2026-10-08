"""Phase 5E admission boundary in disposable PostgreSQL only.

The QA handler still runs as its PostgreSQL table owner, and PostgreSQL does
not have an installed Ed25519 verifier. This suite *demonstrates*, not fixes,
that direct owner-level SQL can bypass application signature checks. The test
transaction is always rolled back. Revoked/expired signer admission fixes ARE
enforced by the SQL trigger, even if a caller bypasses TypeScript.

Use only RETALLY_PHASE5_CI_DSN with current_database='retally_phase5_ci'.
Never point this at either Floot production or the connected staging cluster.
"""
from __future__ import annotations
import json
import os
import unittest
from contextlib import closing

import psycopg
from psycopg.types.json import Jsonb

QA_CLUSTER="7694294930552894346"
PROD_CLUSTER="7693746749463444100"
TENANT="SIM-P5B-HANDLER-TENANT-A"
ID="SIM-P5E-DIRECT-SQL-CHECK"
KEY_ID="SIM-P5C-ISSUER-BUYER-R4"


class Phase5EPostgresAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get("RETALLY_PHASE5_CI_DSN")
        if not cls.dsn:
            raise RuntimeError("DISPOSABLE_CI_DSN_REQUIRED")
        with closing(psycopg.connect(cls.dsn,autocommit=True)) as con:
            db,cluster=con.execute(
               "SELECT current_database(),system_identifier::text FROM pg_control_system()"
            ).fetchone()
            if db!="retally_phase5_ci" or cluster in {QA_CLUSTER,PROD_CLUSTER}:
                raise RuntimeError("REFUSE_CONNECTED_OR_PRODUCTION_DATABASE")
            if con.execute("SELECT to_regclass('phase5c_qa.documents')").fetchone()[0] is None:
                raise RuntimeError("PHASE5C_DISPOSABLE_SCHEMA_REQUIRED")
            if con.execute("SELECT count(*) FROM phase5c_qa.documents").fetchone()[0] < 10:
                raise RuntimeError("PHASE5C_SIGNED_BASELINE_REQUIRED")

    def connection(self):
        return psycopg.connect(self.dsn,autocommit=False)

    def new_case(self,con,suffix):
        case_id=f"{ID}-{suffix}"
        con.execute("""INSERT INTO phase5c_qa.cases(
          tenant_id,case_id,customer_id,invoice_id,carrier_id,currency,max_claim_cents)
          VALUES(%s,%s,'SIM-P5E-CUSTOMER','SIM-P5E-INVOICE','SIM-P5E-CARRIER','USD',100)""",
          (TENANT,case_id))
        return case_id

    def forge(self,con,case_id,source='a'*64):
        """Correct relational envelope, deliberately INVALID fake signature."""
        record_id="SIM-P5E-FORGED-"+case_id
        body={
           "tenantId":TENANT,"caseId":case_id,"recordId":record_id,
           "customerId":"SIM-P5E-CUSTOMER","invoiceId":"SIM-P5E-INVOICE",
           "kind":"CONTRACT","economicKey":"SIM-P5E-ECON-"+case_id,
           "referenceId":None,"amountCents":0,"feeBps":3000,
           "currency":"USD","occurredAt":"2026-10-03T14:00:00Z",
           "sourceHash":source,"issuerKeyId":KEY_ID,
           "contractVersion":"SIM-V1","providerEventId":None,
        }
        con.execute("""INSERT INTO phase5c_qa.documents(
          tenant_id,case_id,record_id,kind,economic_key,reference_id,amount_cents,
          fee_bps,currency,occurred_at,source_sha256,issuer_key_id,body,signature_b64)
          VALUES(%s,%s,%s,'CONTRACT',%s,NULL,0,3000,'USD',
                 '2026-10-03T14:00:00Z',%s,%s,%s,%s)""",
          (TENANT,case_id,record_id,body["economicKey"],source,KEY_ID,
           Jsonb(body),"A"*88))
        return record_id

    def test_new_revoked_issuer_cannot_backdate_forged_record(self):
        with closing(self.connection()) as con:
            try:
                case=self.new_case(con,"REVOKED")
                con.execute("""UPDATE phase5c_qa.issuer_keys SET revoked_at =
                        '2026-10-06T00:00:00Z' WHERE tenant_id=%s AND key_id=%s""",
                        (TENANT,KEY_ID))
                with self.assertRaisesRegex(psycopg.Error,"INVALID_ISSUER_ROLE_OR_PERIOD"):
                    self.forge(con,case)
            finally:
                con.rollback()

    def test_expired_issuer_cannot_backdate_forged_record(self):
        with closing(self.connection()) as con:
            try:
                case=self.new_case(con,"EXPIRED")
                con.execute("""UPDATE phase5c_qa.issuer_keys SET expires_at =
                    '2026-10-07T00:00:00Z' WHERE tenant_id=%s AND key_id=%s""",
                    (TENANT,KEY_ID))
                with self.assertRaisesRegex(psycopg.Error,"INVALID_ISSUER_ROLE_OR_PERIOD"):
                    self.forge(con,case)
            finally:
                con.rollback()

    def test_db_owner_direct_sql_still_bypasses_ed25519_verification_known_gap(self):
        """Intentional outstanding gap. This does NOT certify SQL signature admission."""
        with closing(self.connection()) as con:
            try:
                case=self.new_case(con,"UNREVOKED-BYPASS")
                rid=self.forge(con,case,source="9"*64)
                row=con.execute("""SELECT signature_b64 FROM phase5c_qa.documents
                      WHERE tenant_id=%s AND record_id=%s""",(TENANT,rid)).fetchone()
                self.assertEqual(row[0],"A"*88)
                # The invalid signature succeeded on direct *owner* DML because
                # only the TypeScript layer verifies Ed25519. Do not pretend fixed.
            finally:
                con.rollback()

    def test_qa_data_writer_is_table_owner_not_independent_issuer(self):
        with closing(psycopg.connect(self.dsn,autocommit=True)) as con:
            row=con.execute("""SELECT current_user,tableowner
                  FROM pg_tables WHERE schemaname='phase5c_qa'
                  AND tablename='documents'""").fetchone()
            self.assertEqual(row[0],row[1])
            # A future independent verifier/service role is required. Merely
            # adding a custom GUC or boolean 'signature_verified' is spoofable.

    def test_current_time_revocation_is_in_db_trigger(self):
        with closing(psycopg.connect(self.dsn,autocommit=True)) as con:
            source=con.execute("""SELECT pg_get_functiondef(
               'phase5c_qa.guard_signed_financial_record()'::regprocedure)""").fetchone()[0]
            normalized=source.replace(" ","")
            self.assertIn("transaction_timestamp()>=signer.revoked_at",normalized)
            self.assertIn("transaction_timestamp()>=signer.expires_at",normalized)


if __name__=="__main__":
    unittest.main()
