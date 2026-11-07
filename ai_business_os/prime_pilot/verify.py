"""Trusted local oracle for the timeout fixture. Receives a proposed diff on stdin."""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "create_lead.sql"
GIT_ENV = {
    "PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_AUTHOR_NAME": "Fixture", "GIT_COMMITTER_NAME": "Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
}


def git(cwd, *args, data=None):
    return subprocess.run(["git", *args], cwd=cwd, input=data, capture_output=True,
                          env=GIT_ENV, check=True, timeout=5).stdout


def observed(sql):
    """One local CRM commit survives a lost response. Reconnect, retry and deliver another inquiry."""
    with tempfile.TemporaryDirectory() as state:
        db = Path(state) / "crm.sqlite"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE leads (external_id TEXT NOT NULL)")
        for reference in ["fixture-A", "fixture-A", "fixture-B"]:
            conn = sqlite3.connect(db, isolation_level=None)
            try:
                conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 4096)
                conn.set_progress_handler(lambda: 1, 1000)
                def allow(op, table, column, schema, trigger):
                    permitted = (op == sqlite3.SQLITE_SELECT or
                                 (schema == "main" and table == "leads" and trigger is None and
                                  (op == sqlite3.SQLITE_INSERT or
                                   (op == sqlite3.SQLITE_READ and column == "external_id"))))
                    return sqlite3.SQLITE_OK if permitted else sqlite3.SQLITE_DENY
                conn.set_authorizer(allow)
                conn.execute(sql, {"reference": reference})
            finally:
                conn.close()
        with sqlite3.connect(db) as reader:
            return reader.execute("SELECT external_id, count(*) FROM leads GROUP BY 1 ORDER BY 1").fetchall()


def init_fixture(base):
    base.mkdir()
    git(base, "init", "-q", "--initial-branch=fixture", "--object-format=sha1", "--template=")
    shutil.copyfile(HERE / NAME, base / NAME)
    git(base, "add", NAME)
    git(base, "commit", "-qm", "Synthetic timeout fixture")
    sha = git(base, "rev-parse", "HEAD").decode().strip()
    return sha


def verify(diff):
    if not 0 < len(diff) <= 8192 or b"\0" in diff:
        raise ValueError("missing or oversized patch")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"
        sha = init_fixture(base)
        clean = Path(tmp) / "verifier"
        git(base, "clone", "-q", "--no-local", "--", str(base), str(clean))
        before = observed((clean / NAME).read_text())
        if before != [("fixture-A", 2), ("fixture-B", 1)]:
            raise ValueError("base did not reproduce double creation")
        paths = git(clean, "apply", "--numstat", "-z", "-", data=diff)
        fields = paths.split(b"\t", 2)
        if len(fields) != 3 or fields[2] != NAME.encode() + b"\0":
            raise ValueError("patch is outside allowed path")
        git(clean, "apply", "--cached", "--whitespace=error", "-", data=diff)
        # Read bytes from the index, never follow filesystem links or execute candidate code.
        if not git(clean, "ls-files", "--stage", NAME).startswith(b"100644 "):
            raise ValueError("patch must retain a regular non-executable file")
        sql = git(clean, "show", ":" + NAME).decode()
        after = observed(sql)
        if after != [("fixture-A", 1), ("fixture-B", 1)]:
            raise ValueError("retry did not preserve distinct inquiries")
        return {"fixture_base_sha": sha, "verified_tree": git(clean, "write-tree").decode().strip(),
                "changed_paths": [NAME], "diff_sha256": hashlib.sha256(diff).hexdigest(),
                "base_counts": dict(before), "patched_counts": dict(after), "test_command": "python3 verify.py"}


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--init-fixture":
        print(init_fixture(Path(sys.argv[2])))
    else:
        print(json.dumps(verify(sys.stdin.buffer.read(8193))))
