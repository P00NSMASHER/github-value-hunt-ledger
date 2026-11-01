"""Phase5C actual disposable PostgreSQL financial integrity acceptance.

Never use the Floot production or QA DSN here. Uses retally_phase5_ci only;
the stored signatures remain fictional and cryptographically tested separately.
"""
import copy
import json
import os
from pathlib import Path
import unittest
from contextlib import closing

import psycopg
from psycopg.types.json import Jsonb

from freight.phase5.phase5c_oracle import load_fixture,verify_frozen_finances

ROOT=Path(__file__).parent
PROD="7693746749463444100"
QA="7694294930552894346"


class IsolatedPostgreSQLFinancialAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn=os.environ.get("RETALLY_PHASE5_CI_DSN")
        if not cls.dsn:
            raise RuntimeError("DISPOSABLE_POSTGRES_DSN_REQUIRED")
        fixture=load_fixture()
        cls.fixture=fixture
        with closing(psycopg.connect(cls.dsn,autocommit=True)) as con:
            db,cluster=con.execute(
                "SELECT current_database(),system_identifier::text FROM pg_control_system()"
            ).fetchone()
            if db!="retally_phase5_ci" or cluster in {PROD,QA}:
                raise RuntimeError("REFUSE_LIVE_OR_NONDISPOSABLE_DB")
            src=(ROOT/"phase5c_signed_reconciliation.sql").read_text()
            expected="'"+QA+"'"
            if src.count(expected)!=1:
                raise RuntimeError("QA_CLUSTER_GUARD_NOT_UNIQUE")
            src=src.replace(expected,"'"+cluster+"'")
            con.execute(src)
            c=fixture["cases"][0]
            con.execute("""INSERT INTO phase5c_qa.cases(
              tenant_id,case_id,customer_id,invoice_id,carrier_id,currency,max_claim_cents)
              VALUES(%s,%s,%s,%s,%s,%s,%s)""",
              (c["tenant_id"],c["case_id"],c["customer_id"],c["invoice_id"],
               c["carrier_id"],c["currency"],int(c["max_claim_cents"])))
            for k in fixture["keys"]:
                con.execute("""INSERT INTO phase5c_qa.issuer_keys(
                  tenant_id,key_id,role,public_key_pem,enabled_from,expires_at,revoked_at)
                  VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                  (k["tenant_id"],k["key_id"],k["role"],k["public_key_pem"],
                   k["enabled_from"],k["expires_at"],k["revoked_at"]))
            for row in fixture["documents"]:
                cls._insert(con,row)

    @staticmethod
    def _insert(con,row):
        con.execute("""INSERT INTO phase5c_qa.documents(
          tenant_id,case_id,record_id,kind,economic_key,reference_id,amount_cents,fee_bps,
          currency,occurred_at,source_sha256,issuer_key_id,body,signature_b64)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (row["tenant_id"],row["case_id"],row["record_id"],row["kind"],
           row["economic_key"],row["reference_id"],int(row["amount_cents"]),row["fee_bps"],
           row["currency"],row["occurred_at"],row["source_sha256"],row["issuer_key_id"],
           Jsonb(row["body"]),row["signature_b64"]))

    def test_exact_financial_reconstruction_from_real_postgresql(self):
        proof=verify_frozen_finances(self.fixture)
        with closing(psycopg.connect(self.dsn,autocommit=True)) as con:
            cursor=con.execute("""SELECT customer_posted_cents,reversed_cents,
                invoiced_cents,credited_fee_cents,gross_fee_collected_cents,
                fee_refunded_cents,fee_bps
                FROM phase5c_qa.financial_summary WHERE case_id='SIM-P5C-CASE-A'""")
            p=cursor.fetchone()
        self.assertEqual(tuple(map(int,p)),(1000,500,300,150,250,100,3000))
        self.assertEqual(proof["totals"]["net_recovered_cents"],500)

    def assertRejected(self,row,expected=None):
        with self.assertRaises(psycopg.Error) as caught:
            with psycopg.connect(self.dsn) as con:
                self._insert(con,row)
        if expected:
            self.assertIn(expected,str(caught.exception))

    def test_orphan_reversal_rejected_at_database_level(self):
        row=copy.deepcopy(next(x for x in self.fixture["documents"] if x["kind"]=="CUSTOMER_REVERSAL"))
        row.update(record_id="SIM-P5C-NEG-DB-ORPHAN",economic_key="SIM-P5C-ECO-NEG-DB-ORPHAN",
                   source_sha256="f"*64,reference_id="SIM-NONEXISTENT-POST")
        row["body"].update(recordId=row["record_id"],economicKey=row["economic_key"],
                           sourceHash=row["source_sha256"],referenceId=row["reference_id"])
        self.assertRejected(row,"UNBACKED_EXCESSIVE_REVERSAL")

    def test_duplicate_posting_of_same_credit_rejected_at_database_level(self):
        row=copy.deepcopy(next(x for x in self.fixture["documents"] if x["record_id"]=="SIM-P5C-POST-A"))
        row.update(record_id="SIM-P5C-NEG-DB-POST",economic_key="SIM-P5C-ECO-NEG-DB-POST",
                   source_sha256="e"*64)
        row["body"].update(recordId=row["record_id"],economicKey=row["economic_key"],
                           sourceHash=row["source_sha256"])
        self.assertRejected(row,"DUPLICATE_CUSTOMER_POST")

    def test_refund_larger_than_remaining_liability_is_rejected(self):
        row=copy.deepcopy(next(x for x in self.fixture["documents"] if x["kind"]=="FEE_REFUND"))
        row.update(record_id="SIM-P5C-NEG-DB-REFUND",economic_key="SIM-P5C-ECO-NEG-DB-REFUND",
                   source_sha256="d"*64,amount_cents="10")
        row["body"].update(recordId=row["record_id"],economicKey=row["economic_key"],
                           sourceHash=row["source_sha256"],amountCents=10)
        self.assertRejected(row,"REFUND_NOT_DUE_OR_DUPLICATE")

    def test_immutable_financial_history_rejects_sql_updates(self):
        with self.assertRaises(psycopg.Error) as caught:
            with psycopg.connect(self.dsn) as con:
                con.execute("UPDATE phase5c_qa.documents SET amount_cents=999 WHERE record_id='SIM-P5C-POST-A'")
        self.assertIn("IMMUTABLE_FINANCIAL_EVIDENCE",str(caught.exception))

    def test_claim_cap_stays_enforced(self):
        row=copy.deepcopy(next(x for x in self.fixture["documents"] if x["kind"]=="CARRIER_CREDIT"))
        row.update(record_id="SIM-P5C-NEG-DB-OVERCLAIM",economic_key="SIM-P5C-ECO-NEG-DB-OVERCLAIM",
                   source_sha256="c"*64)
        row["body"].update(recordId=row["record_id"],economicKey=row["economic_key"],
                           sourceHash=row["source_sha256"])
        self.assertRejected(row,"CLAIM_CAP_EXCEEDED")


if __name__=="__main__":
    unittest.main()
