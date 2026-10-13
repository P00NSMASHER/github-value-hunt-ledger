"""M46: enforce the approved SettlementStore SQLite structural policy.

M44/45 validate row values and transaction consistency but a file whose
append-only or capacity triggers were removed with no existing bad rows can
still pass a semantic scan. This guard detects schema drift (including
tampered trigger bodies, missing constraints, or added unreviewed tables) on
the SAME SQLite revision as the current operation. Read-only verification,
no database repair, no migration, no external signing/authentication.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha1
from pathlib import Path
import sqlite3

SCOPE = "RETALLY_M46_PINNED_SQLITE_SCHEMA_AND_TRIGGERS_CURRENT_LOCAL_ONLY"
SCHEMA_PATH = Path(__file__).with_name("settlement_schema.sql")
# This policy pins the reviewed original committed schema source. Changing
# supported schema requires a reviewed migration/policy update, never silently
# relaxing triggers or redefining a CREATE statement in a recovered DB.
SCHEMA_GIT_BLOB_SHA1 = "85585df4b382a421b55c477649ac9ab3a7573b2f"
CATALOG_TYPES = ("table", "index", "trigger", "view")


def _fail(code: str) -> None:
    # Never put raw SQL, tenant IDs, filename or customer rows in an error.
    raise RuntimeError("M46_SQLITE_" + code)


def _git_blob_sha1(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _catalog(conn: sqlite3.Connection) -> dict[tuple[str, str], str]:
    # sqlite_autoindex_* have no source SQL; they are already implied by
    # exact pinned CREATE TABLE definitions. Exclude SQLite's internal
    # objects, but reject *all* user-created catalog extras.
    rows=conn.execute(
        "SELECT type,name,sql FROM sqlite_master "
        "WHERE type IN ('table','index','trigger','view') "
        "AND name NOT LIKE 'sqlite_%' "
        "ORDER BY type,name"
    ).fetchall()
    out={}
    for kind,name,definition in rows:
        if (type(kind) is not str or type(name) is not str or not name
            or type(definition) is not str):
            _fail("SCHEMA_MALFORMED_OBJECT")
        key=(kind,name)
        if key in out:
            _fail("SCHEMA_DUPLICATE_OBJECT")
        out[key]=definition
    return out


@lru_cache(maxsize=1)
def _expected() -> dict[tuple[str,str], str]:
    raw=SCHEMA_PATH.read_bytes()
    if _git_blob_sha1(raw)!=SCHEMA_GIT_BLOB_SHA1:
        _fail("APPROVED_SCHEMA_SOURCE_CHANGED")
    conn=sqlite3.connect(":memory:")
    try:
        conn.executescript(raw.decode("utf-8"))
        expected=_catalog(conn)
    finally:
        conn.close()
    if (len([k for k in expected if k[0]=="table"])!=6
        or len([k for k in expected if k[0]=="trigger"])!=30
        or len([k for k in expected if k[0]=="index"])!=4
        or any(k[0]=="view" for k in expected)):
        _fail("APPROVED_SCHEMA_POLICY_INCOMPLETE")
    return expected


def assert_sqlite_schema(conn: sqlite3.Connection) -> dict:
    """Reject schema drift without executing or recreating missing DDL."""
    expected=_expected()
    actual=_catalog(conn)
    if set(actual)!=set(expected):
        _fail("CATALOG_OBJECTS_CHANGED")
    if any(actual[key]!=expected[key] for key in expected):
        _fail("DEFINITION_CHANGED")
    return {
        "scope": SCOPE,
        "schema_policy_blob_sha1": SCHEMA_GIT_BLOB_SHA1,
        "six_original_tables_intact": True,
        "thirty_original_triggers_intact": True,
        "four_original_explicit_indexes_intact": True,
        "all_view_or_extra_object_injection_rejected": True,
        "trigger_and_unique_constraint_policy_matches_source": True,
        "not_external_bank_carrier_or_customer_evidence": True,
    }
