"""M48: verify real AuditStore catalogue and hash chains under ONE SQLite revision.

Current settlement M46/47 guarded persistent money, while the separate audit
file still allowed silently repaired missing triggers and unpinned file paths.

This guard checks LOCAL application event chain and approved SQL structure, not
independently authenticated original timestamps, external bank/provider data,
or a trusted remote append-only log. A privileged attacker can still rewrite
a whole chain and source policy; no such authority is claimed.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha1
from itertools import groupby
from pathlib import Path
import sqlite3

from freight.audit_ledger import (
    AuditEventType, AuditRecord, verify_chain,
)

SCOPE = "RETALLY_M48_PERSISTENT_AUDIT_FILE_SCHEMA_AND_CHAIN_CURRENT_ONLY"
SCHEMA_PATH = Path(__file__).with_name("audit_store_schema_m48.sql")
APPROVED_SCHEMA_GIT_BLOB_SHA1 = "6eabc1b9d9dd25994d30a8fb3b418dbd7afdeab5"


def _fail(code: str) -> None:
    # Never echo tenant, invoice, filename, proof hash, or SQL in user errors.
    raise RuntimeError("M48_AUDIT_" + code)


def _git_blob_sha1(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _catalog(connection: sqlite3.Connection) -> dict[tuple[str, str], str]:
    records = connection.execute(
        "SELECT type,name,sql FROM sqlite_master "
        "WHERE type IN ('table','index','trigger','view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY type,name"
    )
    result = {}
    for kind, name, sql in records:
        if (type(kind) is not str or type(name) is not str
            or type(sql) is not str or not name):
            _fail("INVALID_CATALOG_OBJECT")
        key = (kind, name)
        if key in result:
            _fail("DUPLICATE_CATALOG_OBJECT")
        result[key] = sql
    return result


@lru_cache(maxsize=1)
def _expected_catalog() -> dict[tuple[str, str], str]:
    raw = SCHEMA_PATH.read_bytes()
    if _git_blob_sha1(raw) != APPROVED_SCHEMA_GIT_BLOB_SHA1:
        _fail("APPROVED_SCHEMA_SOURCE_CHANGED")
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(raw.decode("utf-8"))
        expected = _catalog(con)
    finally:
        con.close()
    if (len(expected) != 4
        or set(expected) != {
            ("table", "audit_events"),
            ("trigger", "audit_events_immutable_update"),
            ("trigger", "audit_events_immutable_delete"),
            ("trigger", "audit_events_input_guard"),
        }):
        _fail("APPROVED_SCHEMA_MISSING_EXPECTED_PROTECTIONS")
    return expected


def verify_audit_connection(connection: sqlite3.Connection, *,
                            scope: tuple[str, str] | None = None) -> dict:
    """Fail closed, without mutation, on signed-in scope or whole audit file.

    Caller owns BEGIN or BEGIN IMMEDIATE. For reopen, scope=None validates
    all tenant chains. For reads/writes, scope is trusted instance scope.
    """
    if scope is not None and (
        type(scope) is not tuple or len(scope) != 2
        or any(type(s) is not str or not s for s in scope)
    ):
        raise ValueError("M48_INVALID_AUDIT_SCOPE")

    if _catalog(connection) != _expected_catalog():
        _fail("SCHEMA_CATALOG_DRIFT")
    try:
        if scope is None:
            rows = connection.execute(
                "SELECT buyer_id,business_unit,sequence,event_type,object_id,"
                "occurred_at,evidence_hash,previous_hash,event_hash "
                "FROM audit_events ORDER BY buyer_id,business_unit,sequence"
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT buyer_id,business_unit,sequence,event_type,object_id,"
                "occurred_at,evidence_hash,previous_hash,event_hash "
                "FROM audit_events WHERE buyer_id=? AND business_unit=? "
                "ORDER BY buyer_id,business_unit,sequence", scope
            ).fetchall()
    except sqlite3.Error:
        _fail("SOURCE_ROWS_UNREADABLE")

    try:
        records = [
            AuditRecord(
                sequence=row[2],
                buyer_id=row[0],
                business_unit=row[1],
                event_type=AuditEventType(row[3]),
                object_id=row[4],
                occurred_at=row[5],
                evidence_hash=row[6],
                previous_hash=row[7],
                event_hash=row[8],
            )
            for row in rows
        ]
        tenants = 0
        for key, group in groupby(
            records, key=lambda r: (r.buyer_id, r.business_unit)
        ):
            if type(key[0]) is not str or type(key[1]) is not str:
                _fail("INVALID_RECORD_SCOPE")
            verify_chain(group, buyer_id=key[0], business_unit=key[1])
            tenants += 1
    except (ValueError, TypeError, KeyError):
        _fail("CHAIN_INVALID")

    return {
        "scope": SCOPE,
        "approved_audit_schema_source_sha1": APPROVED_SCHEMA_GIT_BLOB_SHA1,
        "original_one_table_and_three_triggers_intact": True,
        "validated_scoped_audit_events": len(records),
        "validated_nonempty_tenant_chains": tenants,
        "all_tenant_chains_included": scope is None,
        "no_independent_original_customer_or_bank_proof": True,
        "not_externally_anchored_or_third_party_timestamped": True,
    }
