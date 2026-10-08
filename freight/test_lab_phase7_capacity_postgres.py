"""RETALLY Phase 7 PostgreSQL capacity conservation (existing Labs 01/05/06/11).

Tests real ephemeral PostgreSQL under the Phase 6 CI service. The SQL
implements the same fail-closed tenant lock, source-currency, reservation and
idempotency invariants as the unpublished Floot payment_prepare_POST endpoint.
This is NOT direct execution of the hosted HTTP handler, source attestation,
currency conversion, or proof that a carrier has paid.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
import time
import unittest
from uuid import uuid4

try:
    import psycopg
except ModuleNotFoundError:
    psycopg = None

DB = os.environ.get("RETALLY_PHASE6_TEST_DATABASE_URL")
NS = "phase7_test_capacity"


def connect():
    if not DB or psycopg is None:
        raise RuntimeError("Isolated Phase 7 PostgreSQL driver and database required")
    return psycopg.connect(DB, autocommit=True)


def prepare(tenant, finding, key, digest, currency="USD", amount=1000, fail_after_insert=False):
    with connect() as c:
        with c.transaction():
            # Same tenant-wide lock used by the unpublished Floot endpoint.
            locked = c.execute(f"SELECT id FROM {NS}.tenants WHERE id=%s FOR UPDATE",
                               (tenant,)).fetchone()
            if not locked:
                raise ValueError("TENANT_UNKNOWN")
            old = c.execute(
                f"SELECT id,request_hash FROM {NS}.instructions "
                "WHERE tenant_id=%s AND idempotency_key=%s", (tenant, key),
            ).fetchone()
            if old:
                if old[1] != digest:
                    raise ValueError("IDEMPOTENCY_CONFLICT")
                return "REPLAY", old[0]
            source = c.execute(
                f"SELECT capacity_cents,currency,confirmed FROM {NS}.findings "
                "WHERE tenant_id=%s AND id=%s FOR UPDATE", (tenant, finding),
            ).fetchone()
            if not source:
                raise ValueError("WRONG_TENANT_OR_SOURCE")
            cap, source_currency, confirmed = source
            if not confirmed:
                raise ValueError("NOT_CONFIRMED")
            if currency != source_currency:
                raise ValueError("CURRENCY_MISMATCH")
            if amount <= 0 or amount > cap:
                raise ValueError("CAPACITY_EXCEEDED")
            reserved = c.execute(
                f"SELECT id FROM {NS}.instructions "
                "WHERE tenant_id=%s AND finding_ids ? %s",
                (tenant, finding),
            ).fetchone()
            if reserved:
                raise ValueError("ALREADY_RESERVED")
            ident = "p7_" + uuid4().hex
            c.execute(f"INSERT INTO {NS}.instructions "
                      "(id,tenant_id,idempotency_key,request_hash,amount_cents,currency,finding_ids)"
                      " VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)",
                      (ident, tenant, key, digest, amount, currency, json.dumps([finding])))
            if fail_after_insert:
                raise ValueError("PRE_COMMIT_FAULT")
            return "INSERT", ident


class ExistingLaboratoryCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DB:
            raise unittest.SkipTest("Dedicated PostgreSQL CI job owns this integration suite")
        if psycopg is None:
            raise RuntimeError("PostgreSQL CI URL set but psycopg driver missing")
        with connect() as c:
            c.execute(f"CREATE SCHEMA IF NOT EXISTS {NS}")
            c.execute(f"CREATE TABLE {NS}.tenants(id text PRIMARY KEY)")
            c.execute(f"CREATE TABLE {NS}.findings("
                      "id text PRIMARY KEY, tenant_id text NOT NULL, currency text NOT NULL,"
                      "capacity_cents bigint NOT NULL, confirmed boolean NOT NULL)")
            c.execute(f"CREATE TABLE {NS}.instructions("
                      "id text PRIMARY KEY, tenant_id text NOT NULL, idempotency_key text NOT NULL,"
                      "request_hash text NOT NULL, amount_cents bigint NOT NULL CHECK(amount_cents>0),"
                      "currency text NOT NULL, finding_ids jsonb NOT NULL,"
                      "UNIQUE(tenant_id,idempotency_key))")

    @classmethod
    def tearDownClass(cls):
        with connect() as c:
            c.execute(f"DROP SCHEMA {NS} CASCADE")

    def setUp(self):
        self.a = "tenant_" + uuid4().hex
        self.b = "tenant_" + uuid4().hex
        self.usd = "finding_" + uuid4().hex
        self.eur = "finding_" + uuid4().hex
        with connect() as c:
            c.execute(f"INSERT INTO {NS}.tenants(id) VALUES(%s),(%s)", (self.a,self.b))
            c.execute(f"INSERT INTO {NS}.findings VALUES "
                      "(%s,%s,'USD',1000,true),(%s,%s,'EUR',900,true)",
                      (self.usd,self.a,self.eur,self.a))

    def used(self,finding=None):
        with connect() as c:
            row = c.execute(
                f"SELECT count(*)::int,COALESCE(sum(amount_cents),0)::bigint "
                f"FROM {NS}.instructions WHERE tenant_id=%s AND finding_ids ? %s",
                (self.a,finding or self.usd),
            ).fetchone()
            return tuple(row)

    def test_lab05_unreserved_baseline_reproduces_double_capacity(self):
        """Old per-request capacity check allows two sequential overcommitments."""
        with connect() as c:
            for i in (1,2):
                available=c.execute(
                    f"SELECT capacity_cents FROM {NS}.findings WHERE id=%s",
                    (self.usd,),
                ).fetchone()[0]
                self.assertGreaterEqual(available,1000)
                c.execute(
                    f"INSERT INTO {NS}.instructions VALUES "
                    "(%s,%s,%s,%s,1000,'USD',%s::jsonb)",
                    (f"legacy_{uuid4().hex}",self.a,f"key{i}_{uuid4().hex}",
                     f"hash{i}",json.dumps([self.usd])),
                )
        self.assertEqual(self.used(),(2,2000))

    def test_lab05_second_instruction_cannot_reserve_same_finding(self):
        self.assertEqual(prepare(self.a,self.usd,"key-a","hash-a")[0],"INSERT")
        with self.assertRaisesRegex(ValueError,"ALREADY_RESERVED"):
            prepare(self.a,self.usd,"key-b","hash-b")
        self.assertEqual(self.used(),(1,1000))

    def test_lab11_100_identical_concurrent_preparations_one_insert(self):
        begun=time.monotonic()
        with ThreadPoolExecutor(max_workers=32) as pool:
            replies=list(pool.map(
                lambda i:prepare(self.a,self.usd,"shared-key","shared-hash"),
                range(100)))
        self.assertEqual(sum(x[0]=="INSERT" for x in replies),1)
        self.assertEqual(sum(x[0]=="REPLAY" for x in replies),99)
        self.assertEqual(len({x[1] for x in replies}),1)
        self.assertEqual(self.used(),(1,1000))
        print(f"PHASE7_POSTGRES attempts=100 inserted=1 replay=99 "
              f"reserved_cents=1000 duration_seconds={time.monotonic()-begun:.3f}")

    def test_lab11_conflicting_parallel_preparations_one_blocked(self):
        def attempt(key):
            try:
                return prepare(self.a,self.usd,key,key)[0]
            except ValueError as e:
                return str(e)
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(attempt,["a","b"]))
        self.assertCountEqual(result,["INSERT","ALREADY_RESERVED"])
        self.assertEqual(self.used(),(1,1000))

    def test_lab01_source_currency_mismatch(self):
        with self.assertRaisesRegex(ValueError,"CURRENCY_MISMATCH"):
            prepare(self.a,self.eur,"currency-key","hash",currency="USD",amount=900)
        self.assertEqual(self.used(self.eur),(0,0))

    def test_lab06_tenant_scope(self):
        with self.assertRaisesRegex(ValueError,"WRONG_TENANT_OR_SOURCE"):
            prepare(self.b,self.usd,"foreign-key","hash")
        self.assertEqual(self.used(),(0,0))

    def test_lab05_idempotency_key_cannot_change_terms(self):
        first=prepare(self.a,self.usd,"key","original-hash")
        self.assertEqual(prepare(self.a,self.usd,"key","original-hash"),
                         ("REPLAY",first[1]))
        with self.assertRaisesRegex(ValueError,"IDEMPOTENCY_CONFLICT"):
            prepare(self.a,self.usd,"key","changed-hash",amount=500)
        self.assertEqual(self.used(),(1,1000))

    def test_lab11_precommit_failure_rolls_back_reservation(self):
        with self.assertRaisesRegex(ValueError,"PRE_COMMIT_FAULT"):
            prepare(self.a,self.usd,"crash","hash",fail_after_insert=True)
        self.assertEqual(self.used(),(0,0))
        self.assertEqual(prepare(self.a,self.usd,"crash","hash")[0],"INSERT")
        self.assertEqual(self.used(),(1,1000))


if __name__=="__main__":
    unittest.main()
