"""Authorization-aware source classification for SHAQ rate evidence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


ALLOWED_KINDS = {
    "UNKNOWN",
    "SPOT_MARKET",
    "PUBLISHER_CARRIER_RATE",
    "CARRIER_CONTRACT",
}
ALLOWED_MATCH_FIELDS = {"source_label", "source_url_prefix"}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def record_dataset_authorization(
    conn: sqlite3.Connection,
    *,
    dataset_key: str,
    authorization_scope: str,
    evidence_note: str,
    asserted_by: str = "user",
    asserted_at: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO dataset_authorizations(
             dataset_key, authorization_scope, asserted_by, asserted_at, evidence_note
           ) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(dataset_key) DO UPDATE SET
             authorization_scope=excluded.authorization_scope,
             asserted_by=excluded.asserted_by,
             asserted_at=excluded.asserted_at,
             evidence_note=excluded.evidence_note""",
        (
            dataset_key,
            authorization_scope,
            asserted_by,
            asserted_at or utcnow(),
            evidence_note,
        ),
    )
    conn.commit()


def record_source_classification(
    conn: sqlite3.Connection,
    *,
    dataset_key: str | None,
    match_field: str,
    source_pattern: str,
    rate_kind: str,
    evidence: str,
    reviewed: bool = False,
    classification_method: str = "RESEARCH_REVIEW",
) -> int:
    if rate_kind not in ALLOWED_KINDS:
        raise ValueError(f"invalid rate_kind: {rate_kind}")
    if match_field not in ALLOWED_MATCH_FIELDS:
        raise ValueError(f"invalid match_field: {match_field}")
    conn.execute(
        """INSERT INTO shaq_source_classification(
             dataset_key, match_field, source_pattern, rate_kind,
             classification_method, reviewed, evidence, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(match_field, source_pattern) DO UPDATE SET
             dataset_key=excluded.dataset_key,
             rate_kind=excluded.rate_kind,
             classification_method=excluded.classification_method,
             reviewed=excluded.reviewed,
             evidence=excluded.evidence""",
        (
            dataset_key,
            match_field,
            source_pattern,
            rate_kind,
            classification_method,
            int(reviewed),
            evidence,
            utcnow(),
        ),
    )
    row = conn.execute(
        """SELECT id FROM shaq_source_classification
           WHERE match_field=? AND source_pattern=?""",
        (match_field, source_pattern),
    ).fetchone()
    conn.commit()
    assert row
    return int(row[0])


def _classification(conn: sqlite3.Connection, classification_id: int) -> sqlite3.Row:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM shaq_source_classification WHERE id=?",
        (classification_id,),
    ).fetchone()
    if row is None:
        raise ValueError("classification not found")
    return row


def _where_for(row: sqlite3.Row) -> tuple[str, tuple[Any, ...]]:
    if row["match_field"] == "source_label":
        return "source_label=?", (row["source_pattern"],)
    if row["match_field"] == "source_url_prefix":
        return "source_url LIKE ?", (row["source_pattern"].rstrip("%") + "%",)
    raise ValueError("unsupported classification match field")


def preview_classification(
    conn: sqlite3.Connection,
    classification_id: int,
) -> dict[str, Any]:
    row = _classification(conn, classification_id)
    where, params = _where_for(row)
    matches = conn.execute(
        f"""SELECT rate_kind, COUNT(*) c
            FROM shaq_rates WHERE {where}
            GROUP BY rate_kind ORDER BY c DESC""",
        params,
    ).fetchall()
    auth = None
    if row["dataset_key"]:
        auth = conn.execute(
            "SELECT * FROM dataset_authorizations WHERE dataset_key=?",
            (row["dataset_key"],),
        ).fetchone()

    blockers = []
    if not row["reviewed"]:
        blockers.append("CLASSIFICATION_NOT_REVIEWED")
    if row["rate_kind"] == "CARRIER_CONTRACT":
        if not row["dataset_key"]:
            blockers.append("CONTRACT_CLASSIFICATION_MISSING_DATASET_KEY")
        elif auth is None:
            blockers.append("DATASET_AUTHORIZATION_NOT_RECORDED")

    return {
        "classification_id": classification_id,
        "dataset_key": row["dataset_key"],
        "match_field": row["match_field"],
        "source_pattern": row["source_pattern"],
        "rate_kind": row["rate_kind"],
        "reviewed": bool(row["reviewed"]),
        "matching_rows_by_current_kind": [
            {"rate_kind": x[0], "count": x[1]} for x in matches
        ],
        "authorization_recorded": auth is not None,
        "blockers": blockers,
        "ready_to_apply": not blockers,
    }


def apply_classification(
    conn: sqlite3.Connection,
    classification_id: int,
) -> dict[str, Any]:
    preview = preview_classification(conn, classification_id)
    if preview["blockers"]:
        return {**preview, "status": "BLOCKED", "updated_rows": 0}

    row = _classification(conn, classification_id)
    where, params = _where_for(row)
    prior = {
        x[0]: x[1]
        for x in conn.execute(
            f"SELECT rate_kind, COUNT(*) FROM shaq_rates WHERE {where} GROUP BY rate_kind",
            params,
        ).fetchall()
    }
    matching = sum(prior.values())
    before = conn.total_changes
    conn.execute(
        f"UPDATE shaq_rates SET rate_kind=? WHERE {where}",
        (row["rate_kind"], *params),
    )
    updated = conn.total_changes - before
    conn.execute(
        """INSERT INTO shaq_classification_applications(
             classification_id, applied_at, matching_rate_rows,
             updated_rate_rows, prior_kinds_json, evidence
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        (
            classification_id,
            utcnow(),
            matching,
            updated,
            json.dumps(prior, sort_keys=True),
            row["evidence"],
        ),
    )
    conn.commit()
    return {
        **preview,
        "status": "APPLIED",
        "updated_rows": updated,
        "matching_rows": matching,
        "prior_kinds": prior,
    }
