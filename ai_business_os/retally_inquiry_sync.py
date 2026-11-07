"""Single-host, private pilot bridge from a committed inquiry feed into GopherCRM."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ai_business_os.gopher_crm import GopherCRM, CRMHold, CRMUnavailable, CRMAmbiguousWrite, CRMThrottled

SCHEMA = """
CREATE TABLE IF NOT EXISTS delivery (
  seq INTEGER PRIMARY KEY, reference TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
  service TEXT NOT NULL, campaign TEXT, accepted_at INTEGER NOT NULL,
  phase TEXT NOT NULL DEFAULT 'lead', lead_id INTEGER, task_id INTEGER,
  reason TEXT, checked_at TEXT, external_id TEXT
);
CREATE TABLE IF NOT EXISTS source_cursor (singleton INTEGER PRIMARY KEY CHECK(singleton=1), last_seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS identity (singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  namespace TEXT NOT NULL, source_id TEXT NOT NULL, destination TEXT NOT NULL, owner INTEGER NOT NULL);
"""


@contextmanager
def private_db(path, *, readonly=False):
    path = Path(path).resolve()
    if not readonly and path.parent.stat().st_mode & 0o077:
        raise ValueError("state requires a private directory (0700)")
    mode = "ro" if readonly else "rwc"
    with closing(sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        if not readonly:
            db.executescript(SCHEMA)
        yield db


def source_page(source, after, limit):
    return source.execute("""
        SELECT f.seq,f.reference,i.fingerprint,i.details_json,i.accepted_at,q.reference IS NOT NULL AS excluded
        FROM retally_inquiry_feed f
        LEFT JOIN inquiry_qa_registry q ON q.reference=f.reference
        LEFT JOIN inquiries i ON i.reference=f.reference AND q.reference IS NULL
        WHERE f.seq>? ORDER BY f.seq LIMIT ?
    """, (after, limit)).fetchall()


def external_reference(source_id, reference):
    # A local source restored from backup retains its ID. Independent fixtures can reuse receipt strings.
    scope = hashlib.sha256(source_id.encode()).hexdigest()
    return f"retally:synthetic:{scope}:{reference}"


def collect(db, source, limit, source_id):
    last = db.execute("SELECT COALESCE((SELECT last_seq FROM source_cursor WHERE singleton=1),"
                      "(SELECT MAX(seq) FROM delivery),0)").fetchone()[0]
    page = source_page(source, last, limit)
    with db:
        for row in page:
            if row["excluded"]:
                continue
            details = json.loads(row["details_json"])
            group = details.get("inquiryKind") == "group_contact"
            if group and details.get("consent") is not True:
                raise ValueError("group consent is missing")
            service = details["business"] if group else "freight"
            campaign = (details.get("campaign") or {}).get("utm_campaign")
            db.execute("""INSERT INTO delivery(seq,reference,fingerprint,service,campaign,accepted_at,external_id)
                          VALUES(?,?,?,?,?,?,?)""", (row["seq"], row["reference"], row["fingerprint"],
                          service, campaign, row["accepted_at"], external_reference(source_id, row["reference"])))
        if page:
            db.execute("INSERT OR REPLACE INTO source_cursor(singleton,last_seq) VALUES(1,?)", (page[-1]["seq"],))


def mark(db, reference, **values):
    values["checked_at"] = datetime.now(timezone.utc).isoformat()
    fields = ",".join(key + "=?" for key in values)
    with db:
        db.execute("UPDATE delivery SET " + fields + " WHERE reference=?", (*values.values(), reference))


def deliver(db, source, crm, row):
    ref = row["reference"]
    item = source.execute("""SELECT i.full_name,i.work_email,i.company_name,i.fingerprint
        FROM inquiries i LEFT JOIN inquiry_qa_registry q ON q.reference=i.reference
        WHERE i.reference=? AND q.reference IS NULL""", (ref,)).fetchone()
    if not item or item["fingerprint"] != row["fingerprint"] or not item["work_email"].endswith("@example.invalid"):
        mark(db, ref, phase="hold", reason="missing_or_changed_source")
        return
    external = row["external_id"]
    phase, lead_id = row["phase"], row["lead_id"]
    if phase.startswith("lead"):
        lead_id = crm.find_lead(external)
        if row["lead_id"] is not None and lead_id != row["lead_id"]:
            raise CRMHold("acknowledged lead changed before readback")
        if lead_id is None:
            if phase == "lead_intent":
                mark(db, ref, phase="hold", reason="lead_write_outcome_unknown")
                return
            # Commit intent before crossing the network. After a crash only reconcile.
            mark(db, ref, phase="lead_intent", reason=None)
            first, _, last = item["full_name"].partition(" ")
            fields = dict(first_name=first, last_name=last or "(not supplied)", email=item["work_email"],
                          company=item["company_name"], source="RETALLY " + row["service"])
            try:
                created = crm.create_lead(external, fields)
            except CRMUnavailable:
                # A create call reports CRMUnavailable only for its preflight GET or pre-handler 429.
                # An uncertain POST raises CRMAmbiguousWrite and leaves its intent in place.
                mark(db, ref, phase="lead")
                raise
            mark(db, ref, lead_id=created)
            lead_id = crm.find_lead(external)
            if lead_id != created:
                raise CRMHold("created lead did not match readback")
        mark(db, ref, phase="task", lead_id=lead_id, reason=None)
        phase = "task"
    if crm.find_lead(external) != lead_id:
        raise CRMHold("lead identity changed")
    task = crm.find_task(external, lead_id)
    if row["task_id"] is not None and task != row["task_id"]:
        raise CRMHold("acknowledged task changed before readback")
    if task is None:
        if phase == "task_intent":
            mark(db, ref, phase="hold", reason="task_write_outcome_unknown")
            return
        mark(db, ref, phase="task_intent", reason=None)
        try:
            created = crm.create_task(external, lead_id)
        except CRMUnavailable:
            mark(db, ref, phase="task")
            raise
        mark(db, ref, task_id=created)
        task = crm.find_task(external, lead_id)
        if task != created:
            raise CRMHold("created task did not match readback")
    mark(db, ref, phase="done", task_id=task, reason=None)


def sync(source_path, state_path, crm, *, namespace, destination, owner, limit=25):
    if namespace != "synthetic" or not 1 <= limit <= 100:
        raise ValueError("this pilot accepts only the synthetic namespace and batches of 1 to 100")
    if destination != crm.base_url or owner != crm.owner_id:
        raise ValueError("client does not match the configured CRM origin and owner")
    if Path(state_path).exists() and os.path.samefile(source_path, state_path):
        raise ValueError("source and private delivery state must use separate files")
    with private_db(state_path) as db, private_db(source_path, readonly=True) as source:
        # One writer for this ledger; OS releases the lock if the worker dies.
        with open(state_path, "rb") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fixture = source.execute("SELECT source_id FROM retally_fixture_identity WHERE singleton=1").fetchone()
            if not fixture or not isinstance(fixture["source_id"], str) or not fixture["source_id"].strip():
                raise ValueError("synthetic source provenance is missing")
            expected = (namespace, fixture["source_id"], destination, owner)
            with db:
                db.execute("INSERT OR IGNORE INTO identity VALUES(1,?,?,?,?)", expected)
            binding = tuple(db.execute("SELECT namespace,source_id,destination,owner FROM identity").fetchone())
            if binding != expected:
                raise ValueError("source, destination or integration owner changed")
            # Preserve IDs already issued by the first local pilot when resuming its ledger.
            if "external_id" not in {column[1] for column in db.execute("PRAGMA table_info(delivery)")}:
                with db:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("ALTER TABLE delivery ADD COLUMN external_id TEXT")
                    db.execute("UPDATE delivery SET external_id='retally:synthetic:' || reference")
            collect(db, source, limit, fixture["source_id"])
            rows = db.execute("""SELECT * FROM delivery WHERE phase NOT IN ('done','hold')
                ORDER BY checked_at IS NOT NULL, checked_at, seq LIMIT ?""", (limit,)).fetchall()
            if rows:
                crm.verify_identity()
            for row in rows:
                try:
                    deliver(db, source, crm, row)
                except CRMAmbiguousWrite:
                    mark(db, row["reference"], reason="awaiting_write_reconciliation")
                except CRMHold:
                    mark(db, row["reference"], phase="hold", reason="ambiguous_or_denied")
                except CRMThrottled:
                    mark(db, row["reference"], reason="destination_throttled")
                    break
                except CRMUnavailable:
                    mark(db, row["reference"], reason="destination_unavailable")
                    break
            return dict(db.execute("SELECT phase,count(*) FROM delivery GROUP BY phase").fetchall())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    base = os.environ["RETALLY_CRM_URL"]
    owner = int(os.environ["RETALLY_CRM_OWNER"])
    client = GopherCRM(base, os.environ["RETALLY_CRM_KEY"], owner)
    print(json.dumps(sync(args.source, args.state, client, namespace="synthetic",
                         destination=client.base_url, owner=owner, limit=args.limit)))


if __name__ == "__main__":
    main()
