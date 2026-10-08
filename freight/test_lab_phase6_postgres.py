"""Real PostgreSQL transaction regression for existing RETALLY Labs 05/06/11/12.

Ephemeral CI PostgreSQL ONLY.  These tests mirror the observed Floot schema
constraints and the Phase 5 FOR UPDATE write transaction.  They are not hosted
Floot HTTP handler tests, payment-provider authentication or cash verification.
"""
import concurrent.futures
import hashlib
import os
import threading
import time
import unittest
import uuid

try:
    import psycopg
except ModuleNotFoundError:
    psycopg = None  # General freight discovery has no isolated PostgreSQL service.

DSN = os.environ.get("RETALLY_PHASE6_TEST_DATABASE_URL")
SCHEMA = "phase6_pg_qa"
FIXED_TIME = "2026-10-08T12:00:00+00:00"
ALLOWED = {"AUTHORIZED": {"SUBMITTED"}, "SUBMITTED": {"ACCEPTED", "FAILED"},
           "ACCEPTED": {"SETTLED", "FAILED"}, "SETTLED": {"REVERSED"},
           "REVERSED": set(), "FAILED": set()}


def connection():
    if not DSN:
        raise RuntimeError("Isolated RETALLY_PHASE6_TEST_DATABASE_URL required")
    return psycopg.connect(DSN, autocommit=True)


def post_event(tenant, instruction, reference, state="SUBMITTED", amount=1000,
               source_hash="a"*64, inject_failure=False):
    """DB-equivalent atomic transition, never a real provider action."""
    with connection() as conn:
        with conn.transaction():
            row = conn.execute(
                f"SELECT id,amount_cents FROM {SCHEMA}.instructions "
                "WHERE tenant_id=%s AND id=%s FOR UPDATE",
                (tenant, instruction),
            ).fetchone()
            if not row:
                raise ValueError("TENANT_INSTRUCTION_NOT_FOUND")
            if row[1] != amount:
                raise ValueError("AMOUNT_MISMATCH")
            auth = conn.execute(
                f"SELECT 1 FROM {SCHEMA}.authorizations WHERE tenant_id=%s AND instruction_id=%s",
                (tenant, instruction),
            ).fetchone()
            history = conn.execute(
                f"SELECT id,state,provider_reference,amount_cents,source_hash,occurred_at "
                f"FROM {SCHEMA}.events WHERE tenant_id=%s AND instruction_id=%s "
                "ORDER BY occurred_at,created_at,id", (tenant, instruction),
            ).fetchall()
            for old in history:
                if old[1] == state and old[2] == reference:
                    if old[3] != amount or old[4] != source_hash or old[5].isoformat() != FIXED_TIME:
                        raise ValueError("CONFLICTING_PROVIDER_REPLAY")
                    return ("REPLAY", old[0])
            prior = history[-1][1] if history else ("AUTHORIZED" if auth else "PREPARED")
            if state not in ALLOWED.get(prior, set()):
                raise ValueError("INVALID_TRANSITION")
            if not auth:
                raise ValueError("MISSING_AUTHORIZATION")
            ident = hashlib.sha256(f"{tenant}:{instruction}:{reference}:{state}".encode()).hexdigest()
            event_id = "pe_" + ident[:28]
            conn.execute(
                f"INSERT INTO {SCHEMA}.events "
                "(id,tenant_id,instruction_id,state,provider,provider_reference,"
                "amount_cents,source_hash,occurred_at,event_hash) "
                "VALUES (%s,%s,%s,%s,'SIM',%s,%s,%s,%s,%s)",
                (event_id,tenant,instruction,state,reference,amount,source_hash,
                 FIXED_TIME,ident),
            )
            if inject_failure:
                raise ValueError("INJECTED_PRECOMMIT_CRASH")
            return ("INSERT", event_id)


class Phase6RealPostgresLabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DSN:
            raise unittest.SkipTest("Dedicated Phase6 PostgreSQL CI job owns integration DB; not available in general freight discovery")
        if psycopg is None:
            raise RuntimeError("PostgreSQL test service was configured without psycopg; fail closed")
        with connection() as conn:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
            conn.execute(f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.instructions(
                id text PRIMARY KEY,tenant_id text NOT NULL,amount_cents bigint NOT NULL
                CHECK(amount_cents>0),UNIQUE(tenant_id,id))""")
            conn.execute(f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.authorizations(
                tenant_id text NOT NULL,instruction_id text NOT NULL,
                PRIMARY KEY(tenant_id,instruction_id),
                FOREIGN KEY(tenant_id,instruction_id)
                REFERENCES {SCHEMA}.instructions(tenant_id,id))""")
            conn.execute(f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.events(
                id text PRIMARY KEY,tenant_id text NOT NULL,instruction_id text NOT NULL,
                state text NOT NULL CHECK(state IN
                  ('SUBMITTED','ACCEPTED','SETTLED','FAILED','REVERSED')),
                provider text NOT NULL,provider_reference text,amount_cents bigint NOT NULL
                CHECK(amount_cents>0),source_hash text NOT NULL,
                occurred_at timestamptz NOT NULL,event_hash text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                FOREIGN KEY(tenant_id,instruction_id)
                  REFERENCES {SCHEMA}.instructions(tenant_id,id),
                UNIQUE(tenant_id,event_hash),
                UNIQUE(tenant_id,provider,provider_reference,state))""")

    @classmethod
    def tearDownClass(cls):
        with connection() as conn:
            conn.execute(f"DROP SCHEMA {SCHEMA} CASCADE")

    def setUp(self):
        self.instruction = "p6_" + uuid.uuid4().hex
        with connection() as conn:
            conn.execute(
                f"INSERT INTO {SCHEMA}.instructions(id,tenant_id,amount_cents) "
                "VALUES (%s,'tenant_a',1000)", (self.instruction,),
            )
            conn.execute(
                f"INSERT INTO {SCHEMA}.authorizations(tenant_id,instruction_id) "
                "VALUES ('tenant_a',%s)", (self.instruction,),
            )

    def count(self):
        with connection() as conn:
            return conn.execute(
                f"SELECT count(*) FROM {SCHEMA}.events WHERE instruction_id=%s",
                (self.instruction,),
            ).fetchone()[0]

    def test_lab11_baseline_unlocked_snapshot_accepts_two_distinct_submissions(self):
        """A negative baseline: existing unique constraints alone cannot conserve."""
        barrier=threading.Barrier(2, timeout=15)
        def unsafe(ref):
            with connection() as conn:
                with conn.transaction():
                    n=conn.execute(
                        f"SELECT count(*) FROM {SCHEMA}.events WHERE instruction_id=%s",
                        (self.instruction,),
                    ).fetchone()[0]
                    self.assertEqual(n,0)
                    barrier.wait()
                    digest=hashlib.sha256(ref.encode()).hexdigest()
                    conn.execute(
                        f"INSERT INTO {SCHEMA}.events VALUES "
                        "(%s,'tenant_a',%s,'SUBMITTED','SIM',%s,1000,%s,%s,%s,now())",
                        ("pe_"+digest[:28],self.instruction,ref,"a"*64,FIXED_TIME,digest),
                    )
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(unsafe,["unsafe_A","unsafe_B"]))
        self.assertEqual(self.count(),2)

    def test_lab11_100_simultaneous_exact_callbacks_one_insert_99_replays(self):
        began=time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            results=list(pool.map(lambda _:
                 post_event("tenant_a",self.instruction,"identical"),range(100)))
        self.assertEqual(sum(x[0]=="INSERT" for x in results),1)
        self.assertEqual(sum(x[0]=="REPLAY" for x in results),99)
        self.assertEqual(len(set(x[1] for x in results)),1)
        self.assertEqual(self.count(),1)
        print(f"PHASE6_REAL_POSTGRES count=100 concurrent_workers=32 "
              f"insert=1 replay=99 persisted=1 seconds={time.monotonic()-began:.3f}")

    def test_lab05_conflicting_concurrent_references_one_rejected(self):
        def attempt(reference):
            try: return post_event("tenant_a",self.instruction,reference)[0]
            except ValueError: return "CONFLICT"
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(attempt,["A","B"]))
        self.assertCountEqual(outcomes,["INSERT","CONFLICT"])
        self.assertEqual(self.count(),1)

    def test_lab05_failed_transaction_rolls_back_insert(self):
        with self.assertRaisesRegex(ValueError,"INJECTED_PRECOMMIT_CRASH"):
            post_event("tenant_a",self.instruction,"crash",inject_failure=True)
        self.assertEqual(self.count(),0)
        self.assertEqual(post_event("tenant_a",self.instruction,"crash")[0],"INSERT")
        self.assertEqual(self.count(),1)

    def test_lab06_cross_tenant_instruction_is_rejected_without_effect(self):
        with self.assertRaisesRegex(ValueError,"TENANT_INSTRUCTION_NOT_FOUND"):
            post_event("tenant_b",self.instruction,"foreign")
        self.assertEqual(self.count(),0)

    def test_lab12_conflicting_replay_payload_rejected(self):
        post_event("tenant_a",self.instruction,"same")
        with self.assertRaisesRegex(ValueError,"AMOUNT_MISMATCH"):
            post_event("tenant_a",self.instruction,"same",amount=999)
        with self.assertRaisesRegex(ValueError,"CONFLICTING_PROVIDER_REPLAY"):
            post_event("tenant_a",self.instruction,"same",source_hash="f"*64)
        self.assertEqual(self.count(),1)


if __name__ == "__main__":
    unittest.main()
