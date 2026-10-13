"""M50 read-only admission check for finished two-SQLite backup bundles.

M49 checked self-hashed filenames, completion marker and raw bytes but never
reopened the ACTUAL published files to verify audited chains, financial
constraints, all-tenant content, scoped balances or restored generation.
This module makes an evidence-consistent candidate a prerequisite to treating
a bundle as an accepted local recovery file set.

All cryptographic hashes here are UNKEYED local receipts. An attacker who
controls every file AND report can rehash a false but internally consistent
history; no independent bank/provider authority is claimed.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

from freight.contracts import canonical_hash
from freight.audit_store_integrity_m48 import verify_audit_connection
from freight.settlement_semantic_guard_m44 import audit_connection as verify_settlement
from freight.settlement_file_identity_m47 import identity, assert_identity

SCOPE="RETALLY_M50_READ_ONLY_PUBLISHED_RECOVERY_ADMISSION_SYNTHETIC_SCOPE"

_TABLES={
    "audit":("audit_events",),
    "settlement":(
        "recovery_claims","review_claims","settlement_events",
        "allocations","counter_events","reversal_edges",
    ),
}
_PK={
    "recovery_claims":"claim_id",
    "review_claims":"claim_id",
    "settlement_events":"event_id",
    "allocations":"allocation_id",
    "counter_events":"counter_id",
    "reversal_edges":"reversal_id",
}


def _fail(reason:str)->None:
    raise ValueError("M50_RECOVERY_"+reason)


def _sha(value:object)->bool:
    return (type(value) is str and len(value)==64
            and all(x in "0123456789abcdef" for x in value))


def _read_candidate(file:Path, family:str)->dict:
    """Read local DB semantically and logically under ONE pinned transaction."""
    if family not in _TABLES:
        raise ValueError("M50_UNKNOWN_SQLITE_FAMILY")
    pinned=identity(file)
    con=None
    try:
        con=sqlite3.connect(file.absolute().as_uri()+"?mode=ro",uri=True)
        con.execute("PRAGMA query_only=ON")
        con.execute("BEGIN")
        if con.execute("PRAGMA integrity_check").fetchone()!=( "ok", ):
            _fail("SQLITE_PHYSICAL_INTEGRITY_FAILED")
        if con.execute("PRAGMA foreign_key_check").fetchone() is not None:
            _fail("SQLITE_FOREIGN_KEYS_INVALID")
        if family=="audit":
            check=verify_audit_connection(con,scope=None)
            if not check["all_tenant_chains_included"]:
                _fail("AUDIT_ALL_TENANT_VALIDATION_INCOMPLETE")
        else:
            check=verify_settlement(con,scope=None)
            if check["scoped_to_one_workspace"] is not False:
                _fail("SETTLEMENT_ALL_TENANT_VALIDATION_INCOMPLETE")
        full={}
        scoped={}
        for table in _TABLES[family]:
            cursor=con.execute("SELECT * FROM "+table)
            names=tuple(col[0] for col in cursor.description)
            rows=[tuple(row) for row in cursor]
            # Match M49's canonical all-tenant logical digest exactly.
            rows.sort(key=lambda row:json.dumps(
                row,sort_keys=True,separators=(",",":"),ensure_ascii=False,
            ))
            full[table]=rows
            scoped[table]=[dict(zip(names,row)) for row in rows]
        assert_identity(file,pinned)
        logical=canonical_hash({
            "schema":1,"family":family,"tables":full,
        })
        return {
            "logical_sha256":logical,
            "tables":scoped,
            "all_tenant_semantic_rows_verified":True,
        }
    except (sqlite3.Error,RuntimeError,TypeError,KeyError,IndexError) as exc:
        raise ValueError("M50_RECOVERY_SQLITE_SOURCE_OR_SEMANTICS_INVALID") from exc
    finally:
        if con is not None:
            try:
                con.rollback()
            finally:
                con.close()


def _scoped_summary(backup_audit:dict,backup_settlement:dict,
                    buyer_id:str,business_unit:str)->str:
    """Recompute current M49 workspace_semantic_hash from read-only tables."""
    if (type(buyer_id) is not str or not buyer_id
        or type(business_unit) is not str or not business_unit):
        _fail("INVALID_SOURCE_SCOPE")
    audit_events=[
        row for row in backup_audit["tables"]["audit_events"]
        if row["buyer_id"]==buyer_id and row["business_unit"]==business_unit
    ]
    audit_events.sort(key=lambda row:row["sequence"])
    scoped={}
    counts={}
    for table in _PK:
        rows=[
            row for row in backup_settlement["tables"][table]
            if row["buyer_id"]==buyer_id and row["business_unit"]==business_unit
        ]
        rows.sort(key=lambda row:json.dumps(
            row,sort_keys=True,separators=(",",":"),ensure_ascii=False
        ))
        scoped[table]=rows
        counts[table]=len(rows)
    reversed_by_id={}
    for row in scoped["reversal_edges"]:
        key=row["allocation_id"]
        reversed_by_id[key]=reversed_by_id.get(key,0)+row["amount_cents"]
    realized=sum(r["amount_cents"] for r in scoped["allocations"])-sum(
        r["amount_cents"] for r in scoped["reversal_edges"]
    )
    eligible=sum(
        max(0,r["fee_eligible_cents"]-reversed_by_id.get(r["allocation_id"],0))
        for r in scoped["allocations"]
        if r["fee_eligible_cents"]==r["amount_cents"]
    )
    body={
        "buyer_id":buyer_id,
        "business_unit":business_unit,
        "audit_record_count":len(audit_events),
        "audit_chain_head":audit_events[-1]["event_hash"] if audit_events else None,
        "recovery_claim_count":counts["recovery_claims"],
        "review_claim_count":counts["review_claims"],
        "settlement_event_count":counts["settlement_events"],
        "allocation_count":counts["allocations"],
        "counter_event_count":counts["counter_events"],
        "reversal_edge_count":counts["reversal_edges"],
        "realized_cents":realized,
        "fee_eligible_cents":eligible,
        "settlement_content_hash":canonical_hash({"schema":1,"tables":scoped}),
    }
    return canonical_hash({"schema":1,**body})


def verify_published_candidate(root:Path, result, manifest:dict)->dict:
    """All-tenant and scoped verification after M49 raw hashes match.

    Purposefully does NOT update a customer file or create SQLite sidecars.
    Every candidate is read under SQLite query_only / mode=ro.
    """
    from freight.backup_restore import _capture_files, _file_hash
    if root.is_symlink() or (root/"capture.complete.json").is_symlink():
        _fail("UNTRUSTED_BUNDLE_OR_COMPLETION_MARKER_SYMLINK")
    fields=(
        "source_semantic_hash","restored_semantic_hash",
        "audit_backup_sha256","settlement_backup_sha256",
        "audit_restore_sha256","settlement_restore_sha256",
        "proof_hash",
    )
    if manifest.get("schema")!=1 or any(
        manifest.get(key)!=getattr(result,key) for key in fields
    ):
        _fail("MANIFEST_SOURCE_RECEIPT_FIELDS_NOT_BOUND")
    if (manifest.get("original_sqlite_files_are_independently_versioned") is not True
        or manifest.get("stable_window_before_after_copy_verified") is not True
        or manifest.get("real_pilot_human_approvals_established") is not False):
        _fail("FALSE_RESTORE_PROVENANCE_OR_HUMAN_APPROVAL")
    fingerprints=manifest.get("full_file_logical_source_hashes")
    if (type(fingerprints) is not dict or set(fingerprints)!={"audit","settlement"}
        or any(not _sha(v) for v in fingerprints.values())):
        _fail("INVALID_LOGICAL_SOURCE_FINGERPRINTS")

    names=_capture_files()
    checks={}
    for name,family in zip(names,("audit","settlement","audit","settlement")):
        file=root/name
        before=_file_hash(file)
        info=_read_candidate(file,family)
        after=_file_hash(file)
        if before!=after:
            _fail("SQLITE_CHANGED_DURING_RECOVERY_VALIDATION")
        expected=(getattr(result,{
            "audit.backup.sqlite3":"audit_backup_sha256",
            "settlement.backup.sqlite3":"settlement_backup_sha256",
            "audit.restored.sqlite3":"audit_restore_sha256",
            "settlement.restored.sqlite3":"settlement_restore_sha256",
        }[name]))
        if before!=expected:
            _fail("SQLITE_REBOUND_DURING_RECOVERY_VALIDATION")
        if info["logical_sha256"]!=fingerprints[family]:
            if name.endswith("backup.sqlite3"):
                _fail("BACKUP_ALL_TENANT_SOURCE_GENERATION_MISMATCH")
            _fail("RESTORE_ALL_TENANT_SOURCE_GENERATION_MISMATCH")
        checks[name]=info

    scoped_before=_scoped_summary(
        checks[names[0]],checks[names[1]],result.buyer_id,result.business_unit
    )
    scoped_after=_scoped_summary(
        checks[names[2]],checks[names[3]],result.buyer_id,result.business_unit
    )
    if (scoped_before!=result.source_semantic_hash
        or scoped_after!=result.restored_semantic_hash
        or scoped_before!=scoped_after):
        _fail("SCOPED_AUDIT_OR_SETTLEMENT_RECEIPT_MISMATCH")
    return {
        "scope":SCOPE,
        "published_sqlite_images_inspected":4,
        "whole_file_audit_and_financial_semantics_validated":4,
        "all_tenant_logical_content_matches_frozen_manifest":4,
        "scoped_source_and_restored_financial_receipts_matched":True,
        "read_only_sqlite_query_mode_used":True,
        "m49_two_file_atomic_commit_not_established":True,
        "external_buyer_bank_carrier_authentication_established":False,
        "original_historical_findings_closed":0,
    }
