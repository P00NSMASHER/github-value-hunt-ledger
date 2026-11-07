"""Private synthetic case desk. Operational events never publish or contact customers."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone

from ai_business_os.retally_group import WORKFLOW_IDS
from ai_business_os.retally_customer_register import validate_customer_register

REQUIRED = {
    "qualified": ("fit",),
    "scoped": ("agreement", "authorization"),
    "ready": ("manifest", "release"),
    "fulfillment": ("work_record",),
    "quality-reviewed": ("quality", "deliverable"),
    "delivered": ("delivery_receipt",),
    "closed": ("reconciliation",),
}
DISPOSITIONS = {"decline": "declined", "cancel": "canceled", "dispute": "disputed", "reopen": "active"}
NEXT_ACTIONS = {
    "inquiry": "Review the inquiry and record its fit for the service.",
    "qualified": "Document scope, agreement and authorization.",
    "scoped": "Verify the evidence manifest and release requirements.",
    "ready": "Start the scoped work and record its evidence.",
    "fulfillment": "Review the findings and private deliverable.",
    "quality-reviewed": "Inspect the private preview and outstanding delivery requirements.",
    "delivered": "Reconcile delivery, outstanding corrections and financial evidence.",
    "closed": "Review the completed engagement record.",
}
SCHEMA = """
CREATE TABLE IF NOT EXISTS revoked_desk_sessions (digest TEXT PRIMARY KEY, expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pilot_cases (
 reference TEXT PRIMARY KEY REFERENCES delivery(reference), account_ref TEXT NOT NULL,
 owner TEXT NOT NULL, due_date TEXT NOT NULL, stage TEXT NOT NULL DEFAULT 'inquiry',
 hold TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_artifacts (
 reference TEXT NOT NULL REFERENCES pilot_cases(reference), kind TEXT NOT NULL,
 digest TEXT NOT NULL, content TEXT NOT NULL, PRIMARY KEY(reference,kind,digest)
);
CREATE TABLE IF NOT EXISTS case_events (
 seq INTEGER PRIMARY KEY, reference TEXT NOT NULL REFERENCES pilot_cases(reference),
 occurred_at TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS case_events_reference_seq ON case_events(reference, seq);
"""


def now():
    return datetime.now(timezone.utc).isoformat()


def record(db, ref, action, detail):
    db.execute(
        "INSERT INTO case_events(reference,occurred_at,action,detail) VALUES(?,?,?,?)",
        (ref, now(), action, detail),
    )


def open_case(db, ref, account_ref, owner, due):
    """Account links are supplied explicitly by the pilot operator."""
    if not account_ref.startswith("account:") or not owner.strip() or len(owner) > 80:
        raise ValueError("an explicit account and owner are required")
    date.fromisoformat(due)
    with db:
        row = db.execute("SELECT phase FROM delivery WHERE reference=?", (ref,)).fetchone()
        if not row or row[0] != "done":
            raise ValueError("a reconciled CRM lead and task are required")
        existing = db.execute("SELECT account_ref FROM pilot_cases WHERE reference=?", (ref,)).fetchone()
        if existing:
            if existing[0] != account_ref:
                raise ValueError("conflicting account binding")
            return
        db.execute(
            "INSERT INTO pilot_cases(reference,account_ref,owner,due_date,created_at) VALUES(?,?,?,?,?)",
            (ref, account_ref, owner, due, now()),
        )
        record(db, ref, "opened", owner)


def update_task(db, ref, owner, due, hold):
    if not owner.strip() or len(owner) > 80 or len(hold) > 200:
        raise ValueError("invalid owner or hold reason")
    date.fromisoformat(due)
    with db:
        result = db.execute(
            "UPDATE pilot_cases SET owner=?,due_date=?,hold=? WHERE reference=?",
            (owner.strip(), due, hold.strip() or None, ref),
        )
        if not result.rowcount:
            raise ValueError("unknown case")
        record(db, ref, "triage", json.dumps({"owner": owner, "due": due, "hold": hold}))


def case_disposition(db, ref):
    row = db.execute(
        """SELECT action FROM case_events WHERE reference=? AND action IN ('decline','cancel','dispute','reopen')
           ORDER BY seq DESC LIMIT 1""",
        (ref,),
    ).fetchone()
    return DISPOSITIONS[row[0]] if row else "active"


def set_disposition(db, ref, action, reason, *, actor, expected):
    if action not in DISPOSITIONS or not isinstance(reason, str) or not isinstance(actor, str):
        raise ValueError("invalid operator disposition")
    reason, actor = reason.strip(), actor.strip()
    if not 1 <= len(reason) <= 200 or not 1 <= len(actor) <= 80:
        raise ValueError("an operator and bounded reason are required")
    with db:
        db.execute("BEGIN IMMEDIATE")
        case = db.execute(
            """SELECT c.stage FROM pilot_cases c JOIN identity i ON i.singleton=1
               WHERE c.reference=? AND i.namespace='synthetic'""", (ref,)
        ).fetchone()
        if not case or case[0] not in NEXT_ACTIONS or case[0] in {"delivered", "closed"}:
            raise ValueError("a current synthetic case is required")
        before = case_disposition(db, ref)
        if before != expected or (action == "reopen") != (before != "active"):
            raise ValueError("disposition changed or action unavailable")
        after = DISPOSITIONS[action]
        record(db, ref, action, json.dumps({"actor": actor, "reason": reason, "from": before,
                                            "to": after, "stage": case[0]}, sort_keys=True))
    return after


def next_action(stage, hold=None, disposition="active"):
    if disposition == "disputed":
        return "Review the dispute and record its resolution before reopening."
    if disposition in {"declined", "canceled"}:
        return "Review the disposition history before reopening."
    if disposition != "active":
        raise ValueError("unknown operator disposition")
    if hold:
        return "Resolve the recorded hold. " + hold
    if stage is None:
        return "Reconcile the CRM lead and qualification task."
    if stage not in NEXT_ACTIONS:
        raise ValueError("unknown case stage")
    return NEXT_ACTIONS[stage]


def collected_fee_cents(content):
    """There is no payment evidence adapter in this pilot."""
    if (
        not isinstance(content, dict)
        or type(content.get("collected_cents")) is not int
        or content["collected_cents"] != 0
        or content.get("currency") != "USD"
        or content.get("receipts") != []
    ):
        raise ValueError("unsupported fee collection evidence")
    return 0


def _validate_artifact(ref, kind, content):
    allowed = {name for names in REQUIRED.values() for name in names} | {"recovery_ledger", "fee_receipts"}
    if kind not in allowed or not isinstance(content, dict) or content.get("fixture") is not True:
        raise ValueError("evidence must be a labeled fixture")
    if content.get("reference") != ref:
        raise ValueError("case evidence does not match the inquiry")
    if kind in {"delivery_receipt", "reconciliation"}:
        raise ValueError("the preview pilot cannot attest customer delivery or close an engagement")
    if kind == "fee_receipts":
        collected_fee_cents(content)


def add_artifact(db, ref, kind, content):
    _validate_artifact(ref, kind, content)
    raw = json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(raw.encode()) > 2_000_000:
        raise ValueError("fixture evidence exceeds limit")
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with db:
        if db.execute("SELECT 1 FROM pilot_cases WHERE reference=?", (ref,)).fetchone() is None:
            raise ValueError("unknown case")
        db.execute("INSERT OR IGNORE INTO case_artifacts VALUES(?,?,?,?)", (ref, kind, digest, raw))
    return digest


def _verified_content(ref, kind, row):
    digest, raw = row
    if hashlib.sha256(raw.encode()).hexdigest() != digest:
        raise ValueError("evidence unavailable")
    content = json.loads(raw)
    _validate_artifact(ref, kind, content)
    return content


def case_artifact(db, account_ref, ref, kind, digest):
    row = db.execute(
        """SELECT a.digest,a.content FROM case_artifacts a JOIN pilot_cases c USING(reference)
        WHERE c.account_ref=? AND a.reference=? AND a.kind=? AND a.digest=?""",
        (account_ref, ref, kind, digest),
    ).fetchone()
    if row is None:
        raise ValueError("evidence unavailable")
    return _verified_content(ref, kind, row)


def case_evidence(db, account_ref, ref, kind):
    """Resolve an unversioned reference only when a single verified version exists."""
    rows = db.execute(
        """SELECT a.digest,a.content FROM case_artifacts a JOIN pilot_cases c USING(reference)
        WHERE c.account_ref=? AND a.reference=? AND a.kind=? LIMIT 2""",
        (account_ref, ref, kind),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError("missing or conflicting " + kind)
    return rows[0][0], _verified_content(ref, kind, rows[0])


def advance(db, ref, target):
    with db:
        db.execute("BEGIN IMMEDIATE")
        c = db.execute("SELECT * FROM pilot_cases WHERE reference=?", (ref,)).fetchone()
        if (
            not c
            or c["hold"]
            or case_disposition(db, ref) != "active"
            or target in {"delivered", "closed"}
            or target not in REQUIRED
            or WORKFLOW_IDS.index(target) != WORKFLOW_IDS.index(c["stage"]) + 1
        ):
            raise ValueError("case progression blocked")
        proofs = {}
        for kind in REQUIRED[target]:
            proofs[kind], _ = case_evidence(db, c["account_ref"], ref, kind)
        db.execute("UPDATE pilot_cases SET stage=? WHERE reference=?", (target, ref))
        record(db, ref, target, json.dumps(proofs, sort_keys=True))


def customer_register(db):
    data = {
        "schema_version": 1,
        "storage_authority": "ai_business_os_prod_and_approved_private_service_stores",
        "accounts": [],
        "engagements": [],
        "referrals": [],
    }
    for row in db.execute("SELECT account_ref,MIN(created_at) FROM pilot_cases GROUP BY account_ref"):
        data["accounts"].append({"account_ref": row[0], "private_contact_ref": None, "created_at": row[1]})
    for row in db.execute(
        "SELECT c.*,d.service FROM pilot_cases c JOIN delivery d USING(reference) ORDER BY c.reference"
    ):
        if row["stage"] in {"delivered", "closed"}:
            raise ValueError("stored terminal stage requires independent delivery evidence")
        if row["service"] not in {"freight", "capturebrief"}:
            raise ValueError("unmapped service")
        freight = row["service"] == "freight"
        engagement = {
            "engagement_ref": "engagement:" + row["reference"],
            "account_ref": row["account_ref"],
            "catalog_entry_id": "retally-recovery" if freight else "capturebrief",
            "service_ref": "freight" if freight else None,
            "owner_role": row["owner"],
            "stage": row["stage"],
            "payment_status": "UNKNOWN",
            "currency": "USD" if freight else None,
            "updated_at": db.execute(
                "SELECT MAX(occurred_at) FROM case_events WHERE reference=?", (row["reference"],)
            ).fetchone()[0],
        }
        for field, kind in (
            ("agreement_ref", "agreement"),
            ("customer_authorization_ref", "authorization"),
            ("release_approval_ref", "release"),
            ("input_manifest_ref", "manifest"),
            ("quality_review_ref", "quality"),
            ("delivery_receipt_ref", "delivery_receipt"),
            ("financial_reconciliation_ref", "reconciliation"),
            ("retention_policy_ref", None),
        ):
            present = db.execute(
                "SELECT 1 FROM case_artifacts WHERE reference=? AND kind=? LIMIT 1", (row["reference"], kind)
            ).fetchone()
            engagement[field] = None
            if present:
                digest, _ = case_evidence(db, row["account_ref"], row["reference"], kind)
                engagement[field] = "private:" + digest
        data["engagements"].append(engagement)
    validate_customer_register(data, observed_at=datetime.now(timezone.utc))
    return data
