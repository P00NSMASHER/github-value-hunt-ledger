"""Persistent HTTP contract fixture. No real provider, subscriptions or Redis key cache."""
import hashlib
import json
import socket
import sqlite3
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

try:
    from . import retally_postmill as social
except ImportError:
    import retally_postmill as social


@contextmanager
def fixture(path, *, lose_response=False, disabled=True):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS posts(id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, data, code=200):
            raw = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Length",str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self.assert_auth()
            route = urlsplit(self.path).path
            if route == "/public/v1/integrations":
                self.reply([{"id":social.ACCOUNT,"identifier":social.CHANNEL,"disabled":disabled}])
            elif route == "/public/v1/posts":
                with sqlite3.connect(path) as db:
                    rows = [json.loads(s[0]) for s in db.execute("SELECT payload FROM posts")]
                self.reply({"posts":rows,"cursor":None})
            else:
                self.reply({},404)

        def assert_auth(self):
            assert self.headers["Authorization"] == "local-fixture-memory"
            calls.append((self.command, urlsplit(self.path).path))

        def do_POST(self):
            self.assert_auth()
            if self.path != "/public/v1/posts":
                return self.reply({},404)
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            part, = payload["posts"]
            assert payload["type"] == part["type"] == "draft"
            content, = part["value"]
            with sqlite3.connect(path) as db:
                post_id = content.get("id") or f"http-fixture-{db.execute('select count(*) from posts').fetchone()[0]+1}"
                post = {"id":post_id, "content":content["content"], "state":"DRAFT",
                        "publishDate":payload["date"], "integration":{"id":social.ACCOUNT,"providerIdentifier":social.CHANNEL}}
                db.execute("INSERT OR REPLACE INTO posts VALUES(?,?)",(post_id,json.dumps(post)))
            if lose_response:
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            self.reply([{"postId":post_id,"integration":social.ACCOUNT}],201)
    server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
    try:
        yield social.PrivateDraftPort(server.server_port,"local-fixture-memory"), calls
    finally:
        server.shutdown(); worker.join(); server.server_close()


class DraftProof(unittest.TestCase):
    def setUp(self):
        self.dir = TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        self.db = social.open_calendar(self.root/"calendar.sqlite")
        self.addCleanup(self.db.close)
        social.seed_calendar(self.db)
        self.slug = "liftgate_evidence"

    def test_three_drafts_verified_after_restart_and_ambiguous_commit(self):
        server_db = self.root/"http.sqlite"
        with fixture(server_db, lose_response=True) as (port, calls):
            ids = {s:social.sync_draft(self.db,s,port) for s in social.CATALOG}
            self.assertEqual(sum(c[0] == "POST" for c in calls), 3)
        self.db.close()
        self.db = social.open_calendar(self.root/"calendar.sqlite")
        self.addCleanup(self.db.close)
        with fixture(server_db) as (port,calls):
            self.assertEqual(ids, {s:social.sync_draft(self.db,s,port) for s in social.CATALOG})
            self.assertEqual(sum(c[0]=="POST" for c in calls),0)
        self.assertEqual(len(set(ids.values())),3)

    def test_approval_binds_copy_media_account_time_and_destination(self):
        social.review(self.db,self.slug); social.review(self.db,self.slug,approve=True)
        row = social.current(self.db,self.slug)
        seal = row["approval"]
        snap = social.snapshot(row)
        for field in ("media","copy","channel","account","time","destination"):
            self.assertNotEqual(seal,social.digest({**snap,field:"changed"}))
        with self.assertRaisesRegex(PermissionError, "no publishing transport"):
            social.check_publish(self.db,self.slug,seal)
        server_db = self.root/"http.sqlite"
        with fixture(server_db) as (port,calls):
            original = social.sync_draft(self.db,self.slug,port)
            social.revise(self.db,self.slug,2)
            with self.assertRaisesRegex(PermissionError, "Approval expired"):
                social.check_publish(self.db,self.slug,seal)
            self.assertEqual(original, social.sync_draft(self.db,self.slug,port))
            self.assertEqual(len(calls),sum(route in {"/public/v1/integrations","/public/v1/posts"} for _,route in calls))
        with sqlite3.connect(server_db) as db:
            self.assertEqual(db.execute("select count(*) from posts").fetchone()[0],1)

    def test_transport_rejects_alternate_routes_and_active_channels(self):
        with fixture(self.root/"http.sqlite",disabled=False) as (port,calls):
            for method,route in (("PUT","posts/id/status"),("POST","integration-trigger/id"),("GET","social/instagram"),
                                 ("POST","../api/inngest"),("POST","posts")):
                with self.assertRaises(PermissionError): port._call(method,route,{"type":"now"})
            self.assertEqual(calls,[])
            with self.assertRaises(PermissionError): social.sync_draft(self.db,self.slug,port)
            self.assertFalse(any(m=="POST" for m,_ in calls))

    def test_ambiguous_readback_and_lost_prewrite_claim_never_retry(self):
        class Ambiguous:
            def assert_isolated(self): pass
            def matching_ids(self,row): return ["1","2"]
        class Missing(Ambiguous):
            def matching_ids(self,row): return []
        with self.assertRaisesRegex(RuntimeError,"ambiguous"): social.sync_draft(self.db,self.slug,Ambiguous())
        with self.assertRaisesRegex(RuntimeError,"absent"): social.sync_draft(self.db,self.slug,Missing())
        self.assertEqual(tuple(self.db.execute("SELECT status,attempts FROM social_dispatch").fetchone()),("hold",0))

    def test_readback_is_exact_repeatable_and_preserves_edits(self):
        with self.assertRaisesRegex(ValueError, "Existing draft differs"):
            social.import_readback(self.db)
        from contextlib import closing
        with closing(social.open_calendar(":memory:")) as db:
            self.assertEqual(social.import_readback(db), 3)
            self.assertEqual(social.import_readback(db), 3)
            saved = json.loads(Path(social.__file__).with_name("postmill-draft-readback.json").read_text())
            self.assertEqual(social.checkpoint_drafts(db), saved["drafts"])
            social.revise(db,self.slug,1)
            with self.assertRaisesRegex(ValueError, "Existing draft differs"):
                social.import_readback(db)
            self.assertEqual(social.current(db,self.slug)["version"], 1)
            edited = next(r for r in social.growth_rows(db) if r["slug"] == self.slug)
            self.assertIsNone(edited["remote_id"])

    def test_seed_source_and_tracking(self):
        rows=social.growth_rows(self.db)
        self.assertEqual(len(rows),3)
        for row in rows:
            self.assertIn("utm_campaign="+social.CAMPAIGN,row["destination"])
            self.assertTrue(row["synthetic"])
            self.assertIsNone(row["publication_id"])
        repo=Path(__file__).resolve().parent.parent
        asset=repo/social.MEDIA
        if asset.exists():
            self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(),social.MEDIA_SHA)
            self.assertTrue((repo/social.CALENDAR).is_file())


if __name__ == "__main__":
    unittest.main()
