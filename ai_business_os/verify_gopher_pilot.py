"""Run the actual server and reproduce a lost response for each write, using only fixtures."""

import argparse
from contextlib import contextmanager
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from threading import Thread
import time

from gopher_crm import GopherCRM, CRMAmbiguousWrite, CRMHold
from gopher_pilot import rotate_restored_key


@contextmanager
def pilot(args, state):
    cmd = [sys.executable, str(Path(__file__).with_name("gopher_pilot.py")), "--binary", args.binary,
           "--admin-binary", args.admin_binary, "--state", str(state), "--port", str(args.port)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    try:
        import select
        if not select.select([proc.stdout], [], [], 30)[0] or "Private sales pilot ready" not in proc.stdout.readline():
            raise RuntimeError("pilot boot failed")
        yield json.loads((state / "client.json").read_text())
    finally:
        proc.terminate()
        proc.wait(timeout=15)


@contextmanager
def lost_post_response(port):
    """Forward the actual HTTP request. After a confirmed 201, close without an HTTP response."""
    commits = []

    class Relay(BaseHTTPRequestHandler):
        def forward(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                conn.request(self.command, self.path, body or None, {"Authorization": self.headers["Authorization"],
                                                                    "Content-Type": "application/json"})
                response = conn.getresponse()
                raw = response.read()
                if self.command == "POST" and response.status == 201:
                    commits.append((self.path, json.loads(raw)["data"]["id"]))
                    self.close_connection = True
                    return
                self.send_response(response.status)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            finally:
                conn.close()

        do_GET = do_POST = forward

        def log_message(self, *_):
            pass

    with HTTPServer(("127.0.0.1", 0), Relay) as relay:
        thread = Thread(target=relay.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{relay.server_port}", commits
        finally:
            relay.shutdown()
            thread.join()


def expected_error(kind, function, *args):
    try:
        function(*args)
    except kind:
        return
    raise AssertionError(f"expected {kind.__name__}")


def verify(args):
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix="retally-gopher-check-") as tmp:
        state = Path(tmp) / "pilot"
        state.mkdir(mode=0o700)
        external_id = "retally:synthetic:RA-commit-loss"
        fields = {"first_name": "Synthetic", "last_name": "Freight", "email": "freight@example.invalid",
                  "company": "Fixture Freight", "source": "RETALLY freight"}
        with pilot(args, state) as settings, lost_post_response(args.port) as (relay, commits):
            crm = GopherCRM(**settings)
            proxied = GopherCRM(**dict(settings, base_url=relay))
            expected_error(CRMHold, GopherCRM(**dict(settings, owner_id=settings["owner_id"] + 1)).verify_identity)
            assert crm.find_lead(external_id) is None
            expected_error(CRMAmbiguousWrite, proxied.create_lead, external_id, fields)
            lead = crm.find_lead(external_id)
            assert lead and crm.find_task(external_id, lead) is None
            expected_error(CRMAmbiguousWrite, proxied.create_task, external_id, lead)
            task = crm.find_task(external_id, lead)
            assert task and commits == [("/api/v1/leads", lead), ("/api/v1/tasks", task)]
        # Clean shutdown checkpoints the WAL. Restore the *entire* private fixture into a fresh path.
        restored = Path(tmp) / "restored"
        shutil.copytree(state, restored)
        with pilot(args, restored) as settings:
            fresh = GopherCRM(**settings)
            assert fresh.find_lead(external_id) == lead and fresh.find_task(external_id, lead) == task
            rotated = GopherCRM(**rotate_restored_key(restored, settings))
            expected_error(CRMHold, fresh.verify_identity)
            assert rotated.find_lead(external_id) == lead and rotated.find_task(external_id, lead) == task
        with sqlite3.connect(restored / "gopher.sqlite") as db:
            counts = {name: db.execute("SELECT COUNT(*) FROM " + name).fetchone()[0] for name in ("leads", "tasks")}
            assert counts == {"leads": 1, "tasks": 1}
            # Simulate an owner reassignment between delivery and recovery, on the disposable restore.
            db.execute("UPDATE leads SET owner_id=1 WHERE id=?", (lead,))
        with pilot(args, restored) as settings:
            restricted = GopherCRM(**settings)
            assert restricted.find_lead(external_id) is None
            # The restrictive sales user cannot see the now-hidden ID. SQLite still rejects duplicate writes.
            expected_error(CRMAmbiguousWrite, restricted.create_lead, external_id, fields)
            expected_error(CRMHold, restricted.find_task, external_id, lead)
        with sqlite3.connect(restored / "gopher.sqlite") as db:
            assert db.execute("SELECT COUNT(*) FROM leads").fetchone() == (1,)
        with open(args.binary, "rb") as binary:
            binary_sha = hashlib.file_digest(binary, "sha256").hexdigest()
        return {"environment": "disposable local SQLite", "binary_sha256": binary_sha, "sales_user_id": settings["owner_id"],
                "committed_responses_dropped": len(commits), "lead_id": lead, "task_id": task,
                "verified_after_restart_and_restore": counts, "wrong_identity_held": True, "restored_key_rotated_old_key_401": True,
                "hidden_lead_filtered_and_duplicate_rejected": True, "redacted_task_link_held": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--admin-binary", required=True)
    parser.add_argument("--port", type=int, default=19823)
    print(json.dumps(verify(parser.parse_args()), indent=2))
