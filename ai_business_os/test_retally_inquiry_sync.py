import json
import os
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ai_business_os.gopher_crm import CRMUnavailable, CRMAmbiguousWrite, CRMThrottled
from ai_business_os.retally_inquiry_sync import sync


class FixtureCRM:
    base_url = "http://127.0.0.1:18000"
    owner_id = 7

    def __init__(self):
        self.rows = {"lead": {}, "task": {}}
        self.posts = {"lead": 0, "task": 0}
        self.fault = None
        self.read_fault = None

    def verify_identity(self):
        pass

    def create(self, kind, key):
        fault = None
        if self.fault and self.fault[0] == kind:
            _, fault = self.fault
            self.fault = None
        if fault == "preflight":
            raise CRMUnavailable("identity read timed out before POST")
        if fault == "throttle":
            raise CRMThrottled("429 before handler")
        self.posts[kind] += 1
        if fault == "unknown":
            raise CRMAmbiguousWrite("request outcome unavailable")
        record = self.posts[kind]
        self.rows[kind][key] = record
        if fault == "committed":
            raise CRMAmbiguousWrite("connection lost after commit")
        if fault == "readback":
            self.read_fault = kind
        return record

    def lookup(self, kind, key):
        if self.read_fault == kind:
            self.read_fault = None
            raise CRMUnavailable("GET timed out")
        return self.rows[kind].get(key)

    def find_lead(self, external):
        return self.lookup("lead", external)

    def create_lead(self, external, fields):
        return self.create("lead", external)

    def find_task(self, external, lead):
        return self.lookup("task", (external, lead))

    def create_task(self, external, lead):
        return self.create("task", (external, lead))


class InquirySyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.crm = FixtureCRM()
        self.source = self.make_source("source-a")
        self.state = self.root / "ledger.sqlite"

    def make_source(self, source_id, service="freight"):
        source = self.root / (source_id + ".sqlite")
        details = {} if service == "freight" else {"inquiryKind": "group_contact", "consent": True, "business": service}
        with sqlite3.connect(source) as db:
            db.executescript("""
                CREATE TABLE inquiries(reference TEXT PRIMARY KEY, fingerprint TEXT, details_json TEXT,
                    accepted_at INTEGER, full_name TEXT, work_email TEXT, company_name TEXT);
                CREATE TABLE inquiry_qa_registry(reference TEXT PRIMARY KEY);
                CREATE TABLE retally_fixture_identity(singleton INTEGER PRIMARY KEY, source_id TEXT);
            """)
            db.executescript(Path(__file__).with_name("retally_inquiry_feed.sql").read_text())
            db.execute("INSERT INTO retally_fixture_identity VALUES(1,?)", (source_id,))
            db.execute("INSERT INTO inquiries VALUES('same-ref','hash',?,1,'Test Person','a@example.invalid','Same Co')",
                       (json.dumps(details),))
        return source

    def run_sync(self, **kwargs):
        return sync(kwargs.get("source", self.source), kwargs.get("state", self.state), self.crm,
                    namespace="synthetic", destination=kwargs.get("destination", FixtureCRM.base_url), owner=7)

    def snapshot(self):
        with sqlite3.connect(self.state) as db:
            return db.execute("SELECT phase,reason FROM delivery").fetchone()

    def test_preflight_read_timeout_allows_a_real_first_post(self):
        for kind in ("lead", "task"):
            with self.subTest(kind=kind):
                self.state = self.root / (kind + ".sqlite")
                self.crm = FixtureCRM()
                self.crm.fault = kind, "preflight"
                self.run_sync()
                self.assertEqual(self.snapshot(), (kind, "destination_unavailable"))
                self.assertEqual(self.run_sync(), {"done": 1})
                self.assertEqual(self.crm.posts, {"lead": 1, "task": 1})

    def test_lost_response_and_readback_timeout_reconcile_without_repost(self):
        for kind in ("lead", "task"):
            for fault in ("committed", "readback", "unknown"):
                with self.subTest(kind=kind, fault=fault):
                    self.state = self.root / (kind + fault + ".sqlite")
                    self.crm = FixtureCRM()
                    self.crm.fault = kind, fault
                    self.run_sync()
                    self.assertEqual(self.snapshot()[0], kind + "_intent")
                    expected = "hold" if fault == "unknown" else "done"
                    self.assertEqual(self.run_sync(), {expected: 1})
                    self.assertEqual(self.run_sync(), {expected: 1})
                    self.assertEqual(self.crm.posts[kind], 1)

    def test_throttled_write_resumes_without_losing_cause(self):
        for kind in ("lead", "task"):
            with self.subTest(kind=kind):
                self.state = self.root / (kind + ".sqlite")
                self.crm = FixtureCRM()
                self.crm.fault = kind, "throttle"
                self.run_sync()
                self.assertEqual(self.snapshot(), (kind, "destination_throttled"))
                self.assertEqual(self.run_sync(), {"done": 1})
                self.assertEqual(self.crm.posts, {"lead": 1, "task": 1})

    def test_replaced_record_after_readback_failure_requires_review(self):
        for kind in ("lead", "task"):
            with self.subTest(kind=kind):
                self.state = self.root / (kind + ".sqlite")
                self.crm = FixtureCRM()
                self.crm.fault = kind, "readback"
                self.run_sync()
                key, = self.crm.rows[kind]
                self.crm.rows[kind][key] = 99
                self.assertEqual(self.run_sync(), {"hold": 1})
                self.assertEqual(self.crm.posts[kind], 1)

    def test_ledger_rejects_source_or_destination_rebinding(self):
        self.run_sync()
        other = self.make_source("source-b")
        with self.assertRaises(ValueError):
            self.run_sync(source=other)
        with self.assertRaises(ValueError):
            self.run_sync(destination="http://127.0.0.1:18001")
        self.crm.owner_id = 8
        with self.assertRaises(ValueError):
            self.run_sync()
        self.assertEqual(self.crm.posts, {"lead": 1, "task": 1})

    def test_qa_only_page_advances_cursor_and_never_creates_a_delivery(self):
        with sqlite3.connect(self.source) as db:
            db.execute("INSERT INTO inquiry_qa_registry VALUES('same-ref')")
            db.execute("INSERT INTO inquiries SELECT 'next-ref',fingerprint,details_json,accepted_at,"
                       "full_name,work_email,company_name FROM inquiries WHERE reference='same-ref'")
        def page():
            return sync(self.source, self.state, self.crm, namespace="synthetic",
                        destination=self.crm.base_url, owner=7, limit=1)
        self.assertEqual(page(), {})
        with sqlite3.connect(self.state) as db:
            self.assertEqual(db.execute("SELECT last_seq FROM source_cursor").fetchone(), (1,))
        self.assertEqual(page(), {"done": 1})
        self.assertEqual(page(), {"done": 1})
        with sqlite3.connect(self.state) as db:
            self.assertEqual(db.execute("SELECT last_seq FROM source_cursor").fetchone(), (2,))
            self.assertEqual(db.execute("SELECT reference FROM delivery").fetchall(), [("next-ref",)])

    def test_source_hardlink_cannot_be_opened_as_writable_state(self):
        os.link(self.source, self.state)
        with self.assertRaises(ValueError):
            self.run_sync()
        with sqlite3.connect(self.source) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_schema WHERE name='delivery'").fetchone())

    def test_same_ref_from_distinct_sources_and_services_has_separate_ids(self):
        other = self.make_source("source-b", "capturebrief")
        self.assertEqual(self.run_sync(), {"done": 1})
        self.assertEqual(self.run_sync(source=other, state=self.root / "second.sqlite"), {"done": 1})
        self.assertEqual(self.crm.posts, {"lead": 2, "task": 2})

    def test_concurrent_workers_cannot_both_cross_the_create_boundary(self):
        entered, release = threading.Event(), threading.Event()
        create = self.crm.create_lead

        def paused(key, fields):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("concurrency fixture timed out")
            return create(key, fields)

        self.crm.create_lead = paused
        with ThreadPoolExecutor(1) as pool:
            first = pool.submit(self.run_sync)
            self.assertTrue(entered.wait(5))
            try:
                # Alternate names for one ledger inode must contend on the same lock.
                alias = self.root / "state-alias.sqlite"
                os.link(self.state, alias)
                with self.assertRaises(BlockingIOError):
                    self.run_sync(state=alias)
            finally:
                release.set()
            self.assertEqual(first.result(timeout=5), {"done": 1})
        self.assertEqual(self.run_sync(), {"done": 1})
        self.assertEqual(self.crm.posts, {"lead": 1, "task": 1})


if __name__ == "__main__":
    unittest.main()
