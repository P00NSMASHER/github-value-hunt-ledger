"""Disposable PostgreSQL acceptance for RETALLY's QA-only payment contract.

Runs ONLY against a database literally named retally_phase5_ci.
Never connects to Floot, production providers or real customer records.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import unittest

import psycopg
from psycopg.rows import dict_row

QA_IDENTIFIER = "7694294930552894346"
PRODUCTION_IDENTIFIER = "7693746749463444100"
HASH = "a" * 64


class Phase5PostgresAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = os.environ.get("RETALLY_PHASE5_CI_DSN")
        if not cls.dsn:
            raise RuntimeError("Phase 5 CI DSN required; never fall back to a real database")
        with closing(psycopg.connect(cls.dsn, autocommit=True, row_factory=dict_row)) as con:
            info = con.execute(
                "SELECT current_database() AS db, system_identifier::text AS cluster "
                "FROM pg_control_system()"
            ).fetchone()
            if info["db"] != "retally_phase5_ci" or info["cluster"] == PRODUCTION_IDENTIFIER:
                raise RuntimeError("Refusing any non-disposable or production database")
            cls.cluster = info["cluster"]
            con.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            sql = (Path(__file__).with_name("isolated_postgres.sql")
                   .read_text(encoding="utf-8"))
            guard_literal = "<> '" + QA_IDENTIFIER + "'"
            if sql.count(guard_literal) != 1:
                raise RuntimeError("Unexpected migration guard identity")
            sql = sql.replace(guard_literal, "<> '" + cls.cluster + "'")
            con.execute(sql)

    def con(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def seed(self, suffix, *, authorized=True, currency="USD"):
        tenant = "SIM-P5-CI-" + suffix
        inst = "SIM-P5-INSTRUCTION"
        with closing(self.con()) as con:
            con.execute(
                "INSERT INTO phase5_qa.instructions"
                "(tenant_id,instruction_id,currency,amount_cents,authorized)"
                " VALUES (%s,%s,%s,1000,%s)",
                (tenant, inst, currency, authorized)
            )
            con.execute(
                "INSERT INTO phase5_qa.actors"
                "(tenant_id,provider,actor_id,role,authorized)"
                " VALUES (%s,'SIM-MOCK-RAIL','SIM-ACTOR','MOCK_PROVIDER',true)",
                (tenant,)
            )
        return tenant, inst

    def submit(self, tenant, inst, state="SUBMITTED", ref="SIM-REF-1",
               stamp="2026-10-08T14:00:00+00:00", actor="SIM-ACTOR",
               value=1000, source=HASH):
        with closing(self.con()) as con:
            return con.execute(
                "SELECT accepted_event_id,accepted_event_hash,is_replay,result_state "
                "FROM phase5_qa.record_provider_event(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (tenant,inst,state,"SIM-MOCK-RAIL",ref,actor,value,source,stamp)
            ).fetchone()

    def count(self, tenant, inst):
        with closing(self.con()) as con:
            return con.execute(
                "SELECT count(*)::int AS c FROM phase5_qa.events "
                "WHERE tenant_id=%s AND instruction_id=%s",
                (tenant,inst)
            ).fetchone()["c"]

    def test_01_concurrent_exact_replay_one_event(self):
        t,i=self.seed("CONCURRENT")
        with ThreadPoolExecutor(max_workers=12) as pool:
            responses=list(pool.map(lambda _: self.submit(t,i), range(25)))
        self.assertEqual(sum(r["is_replay"] is False for r in responses),1)
        self.assertEqual(sum(r["is_replay"] is True for r in responses),24)
        self.assertEqual(len({r["accepted_event_id"] for r in responses}),1)
        self.assertEqual(self.count(t,i),1)

    def test_02_conflicting_payload_and_actor_fail(self):
        t,i=self.seed("CONFLICT")
        self.submit(t,i)
        with self.assertRaisesRegex(psycopg.Error,"CONFLICTING_PROVIDER_REFERENCE_REPLAY"):
            self.submit(t,i,source="b"*64)
        with self.assertRaisesRegex(psycopg.Error,"MOCK_PROVIDER_ACTOR_UNAUTHORIZED"):
            self.submit(t,i,actor="SIM-FAKE-ACTOR")
        self.assertEqual(self.count(t,i),1)

    def test_03_full_lifecycle_reversal_and_late_replay(self):
        t,i=self.seed("REVERSAL")
        first=self.submit(t,i)
        self.submit(t,i,"ACCEPTED","SIM-REF-2","2026-10-08T14:01:00+00:00")
        self.submit(t,i,"SETTLED","SIM-REF-3","2026-10-08T14:02:00+00:00")
        self.submit(t,i,"REVERSED","SIM-REF-4","2026-10-08T14:03:00+00:00")
        retried=self.submit(t,i)
        self.assertTrue(retried["is_replay"])
        self.assertEqual(first["accepted_event_id"],retried["accepted_event_id"])
        self.assertEqual(self.count(t,i),4)
        with self.assertRaisesRegex(psycopg.Error,"INVALID_PAYMENT_STATE_TRANSITION"):
            self.submit(t,i,"SUBMITTED","SIM-REF-5","2026-10-08T14:04:00+00:00")
        self.assertEqual(self.count(t,i),4)

    def test_04_unknown_outcome_blocks_resubmission(self):
        t,i=self.seed("UNKNOWN")
        self.submit(t,i)
        self.submit(t,i,"OUTCOME_UNKNOWN","SIM-REF-2","2026-10-08T14:01:00+00:00")
        with self.assertRaisesRegex(psycopg.Error,"INVALID_PAYMENT_STATE_TRANSITION"):
            self.submit(t,i,"SUBMITTED","SIM-REF-3","2026-10-08T14:02:00+00:00")
        self.assertEqual(self.count(t,i),2)

    def test_05_tenant_and_currency_scope(self):
        a,i=self.seed("USD",currency="USD")
        b,_=self.seed("EUR",currency="EUR")
        out1=self.submit(a,i)
        out2=self.submit(b,i)
        self.assertNotEqual(out1["accepted_event_id"],out2["accepted_event_id"])
        self.assertEqual((self.count(a,i),self.count(b,i)),(1,1))
        with closing(self.con()) as con:
            rows=con.execute(
                "SELECT currency,count(*)::int AS cnt FROM phase5_qa.instructions "
                "WHERE tenant_id IN (%s,%s) GROUP BY currency ORDER BY currency",
                (a,b)
            ).fetchall()
        self.assertEqual([(x["currency"],x["cnt"]) for x in rows],[("EUR",1),("USD",1)])

    def test_06_missing_authorization_rejected(self):
        t,i=self.seed("NOAUTH",authorized=False)
        with self.assertRaisesRegex(psycopg.Error,"INSTRUCTION_NOT_AUTHORIZED"):
            self.submit(t,i)
        self.assertEqual(self.count(t,i),0)

    def test_07_out_of_order_and_invalid_transition(self):
        t,i=self.seed("CHRONO")
        self.submit(t,i)
        with self.assertRaisesRegex(psycopg.Error,"EVENT_TIME_REGRESSION"):
            self.submit(t,i,"ACCEPTED","SIM-REF-2","2026-10-07T14:00:00+00:00")
        with self.assertRaisesRegex(psycopg.Error,"INVALID_PAYMENT_STATE_TRANSITION"):
            self.submit(t,i,"SETTLED","SIM-REF-3","2026-10-08T14:02:00+00:00")
        self.assertEqual(self.count(t,i),1)

    def test_08_append_only_database_constraints(self):
        t,i=self.seed("IMMUTABLE")
        row=self.submit(t,i)
        with closing(self.con()) as con:
            with self.assertRaisesRegex(psycopg.Error,"IMMUTABLE_QA_EVENT"):
                con.execute("UPDATE phase5_qa.events SET amount_cents=999 "
                            "WHERE event_id=%s",(row["accepted_event_id"],))
            self.assertEqual(self.count(t,i),1)
            with self.assertRaises(psycopg.Error):
                con.execute(
                    "INSERT INTO phase5_qa.events"
                    "(tenant_id,instruction_id,event_seq,provider,provider_reference,"
                    "actor_id,state,amount_cents,source_sha256,occurred_at,event_hash)"
                    " VALUES(%s,%s,99,'SIM-MOCK-RAIL','SIM-REF-1','SIM-ACTOR',"
                    "'SUBMITTED',1000,%s,now(),%s)",
                    (t,i,HASH,"c"*64)
                )

if __name__=="__main__":
    unittest.main()
