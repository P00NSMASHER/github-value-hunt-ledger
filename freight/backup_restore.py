"""Semantic backup/restore drill for Freight Recovery pilot evidence.

The drill backs up scoped audit + settlement SQLite stores using SQLite's backup
API, restores them into fresh files, then compares business semantics after
restore. A copied file alone is not accepted as recovery proof.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from freight.audit_store import AuditStore
from freight.contracts import canonical_hash
from freight.settlement_store import SettlementStore


@dataclass(frozen=True)
class WorkspaceSemanticSummary:
    buyer_id: str
    business_unit: str
    audit_record_count: int
    audit_chain_head: str | None
    recovery_claim_count: int
    review_claim_count: int
    settlement_event_count: int
    allocation_count: int
    counter_event_count: int
    reversal_edge_count: int
    realized_cents: int
    fee_eligible_cents: int
    settlement_content_hash: str
    semantic_hash: str


@dataclass(frozen=True)
class BackupRestoreResult:
    buyer_id: str
    business_unit: str
    source_semantic_hash: str
    restored_semantic_hash: str
    audit_backup_sha256: str
    settlement_backup_sha256: str
    audit_restore_sha256: str
    settlement_restore_sha256: str
    proof_hash: str


def _file_hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def _sqlite_backup(source: Path, destination: Path) -> None:
    """Make a bounded SQLite-level copy without replacing existing artifacts.

    The caller supplies a private staging destination. SOURCE uses mode=ro,
    so a missing database cannot silently become an empty "backup".
    """
    destination.parent.mkdir(parents=True,exist_ok=True)
    if os.path.lexists(destination):
        raise RuntimeError("M49_BACKUP_STAGE_DESTINATION_ALREADY_EXISTS")
    from freight.settlement_file_identity_m47 import identity, assert_identity
    pinned=identity(source)
    src=sqlite3.connect(source.absolute().as_uri()+"?mode=ro",uri=True)
    try:
        assert_identity(source,pinned)
        dst=sqlite3.connect(str(destination))
        try:
            src.backup(dst)
            dst.commit()
            assert_identity(source,pinned)
        finally:
            dst.close()
    finally:
        src.close()


def _restore_copy(source_backup: Path, destination: Path) -> None:
    """Verify a fresh independent SQLite restore without destroying a file."""
    _sqlite_backup(source_backup,destination)


def _logical_sqlite_hash(source: Path, family: str) -> str:
    """Fingerprint ALL tenant rows under ONE SQLite read transaction.

    WAL page bytes are not a stable semantic hash; a concurrent checkpoint
    can change file SHA with unchanged records. This whole-file logical
    digest is local-only evidence of a stable two-file capture window.
    """
    tables = {
        "audit": ("audit_events",),
        "settlement": (
            "recovery_claims", "review_claims", "settlement_events",
            "allocations", "counter_events", "reversal_edges",
        ),
    }
    if family not in tables:
        raise ValueError("M49_UNSUPPORTED_SQLITE_CAPTURE_FAMILY")
    from freight.settlement_file_identity_m47 import identity, assert_identity
    pinned = identity(source)
    conn = sqlite3.connect(source.absolute().as_uri()+"?mode=ro",uri=True)
    try:
        conn.execute("BEGIN")
        content = {}
        for table in tables[family]:
            # All SQL identifiers come from the fixed table allowlist.
            rows=[tuple(row) for row in conn.execute("SELECT * FROM " + table)]
            rows.sort(key=lambda row: json.dumps(
                row,sort_keys=True,separators=(",",":"),ensure_ascii=False))
            content[table]=rows
        assert_identity(source,pinned)
        return canonical_hash({
            "schema":1, "family":family, "tables":content,
        })
    finally:
        conn.rollback()
        conn.close()


def _capture_files() -> tuple[str, ...]:
    return (
        "audit.backup.sqlite3",
        "settlement.backup.sqlite3",
        "audit.restored.sqlite3",
        "settlement.restored.sqlite3",
    )


def _bundle_record(result: BackupRestoreResult, logical_hashes: dict) -> dict:
    body={
        "schema":1,
        "scope":"M49_SCOPED_TWO_SQLITE_STABLE_WINDOW_NOT_ATOMIC_CROSS_FILE",
        "source_semantic_hash":result.source_semantic_hash,
        "restored_semantic_hash":result.restored_semantic_hash,
        "audit_backup_sha256":result.audit_backup_sha256,
        "settlement_backup_sha256":result.settlement_backup_sha256,
        "audit_restore_sha256":result.audit_restore_sha256,
        "settlement_restore_sha256":result.settlement_restore_sha256,
        "proof_hash":result.proof_hash,
        "full_file_logical_source_hashes":logical_hashes,
        "original_sqlite_files_are_independently_versioned":True,
        "stable_window_before_after_copy_verified":True,
        "separate_two_file_atomic_database_commit_established":False,
        "real_customer_bank_or_carrier_source_verified":False,
        "original_26_historical_findings_closed":0,
        "real_pilot_human_approvals_established":False,
    }
    body["manifest_sha256"]=canonical_hash(body)
    return body


def verify_backup_bundle(root: str | Path,
                         result: BackupRestoreResult) -> dict:
    """Check completion marker, typed proof and all FOUR artifact hashes.

    A directory containing partial SQLite files but no final completion
    marker is NEVER accepted as a recoverable dual-ledger backup.
    """
    verify_backup_restore_result(result)
    base=Path(root)
    try:
        record=json.loads((base/"capture.complete.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("M49_MISSING_OR_INVALID_CAPTURE_COMPLETION_MARKER") from exc
    if type(record) is not dict:
        raise ValueError("M49_INVALID_CAPTURE_MANIFEST_TYPE")
    receipt=record.get("manifest_sha256")
    if (type(receipt) is not str
        or receipt!=canonical_hash({
            k:v for k,v in record.items() if k!="manifest_sha256"
        })
        or record.get("scope")!="M49_SCOPED_TWO_SQLITE_STABLE_WINDOW_NOT_ATOMIC_CROSS_FILE"
        or record.get("proof_hash")!=result.proof_hash
        or record.get("original_26_historical_findings_closed")!=0
        or record.get("real_customer_bank_or_carrier_source_verified") is not False
        or record.get("separate_two_file_atomic_database_commit_established") is not False):
        raise ValueError("M49_BUNDLE_COMPLETION_MANIFEST_NOT_TRUSTWORTHY")
    expected=(
        result.audit_backup_sha256,
        result.settlement_backup_sha256,
        result.audit_restore_sha256,
        result.settlement_restore_sha256,
    )
    for name, sha in zip(_capture_files(), expected):
        if (os.path.islink(base/name)
            or not (base/name).is_file()
            or _file_hash(base/name)!=sha):
            raise ValueError("M49_BUNDLE_SQLITE_FILE_MISSING_OR_CHANGED")
    # M50: matching local SHA receipts cannot independently establish
    # that the *published files* have sound audit chains, schema/counter
    # constraints, scope-bound money or matching restored generations.
    # Validate every original-source and restore image in read-only mode.
    from freight.restore_admission_m50 import verify_published_candidate
    verify_published_candidate(base,result,record)
    return record



def verify_witnessed_recovery_bundle(
    root: str | Path,
    result: BackupRestoreResult,
    *,
    trust_registry: dict,
    witness_receipts: object,
    expected_restore_request_id: str,
    expected_audience: str,
    as_of_utc,
) -> dict:
    """Require two caller-provisioned Ed25519 technical witnesses for review.

    The existing verify_backup_bundle stays a LOCAL data-integrity check.
    It must never be confused with authorization for a real customer restore.
    This additional API is deliberately fail-closed when review receipts,
    external trust roots, audience or request binding are missing. It never
    issues a restore command, changes a ledger or grants legal permission.
    """
    # Always validate all four actual published SQLite images BEFORE
    # considering attestations. Valid signatures on corrupted data are
    # insufficient and cannot override M49/M50 source rejection.
    manifest=verify_backup_bundle(root,result)
    from freight.recovery_witness_m51 import validate_technical_witnesses
    return validate_technical_witnesses(
        manifest=manifest,
        result=result,
        trust_registry=trust_registry,
        witness_receipts=witness_receipts,
        expected_restore_request_id=expected_restore_request_id,
        expected_audience=expected_audience,
        as_of_utc=as_of_utc,
    )


def _settlement_content(settlement: SettlementStore) -> dict:
    """Guard then summarize ONE scoped SQLite revision.

    Prior code queried six tables and accounting totals through separate
    connections without a common read transaction. A concurrent return could
    produce contradictory counts, cash totals and a valid-looking digest.
    """
    snapshot=json.loads(settlement.report_snapshot_json())
    if (snapshot["buyer_id"],snapshot["business_unit"]) != (
        settlement.buyer_id,settlement.business_unit
    ):
        raise RuntimeError("M44_SETTLEMENT_SNAPSHOT_SCOPE_CHANGED")
    tables = snapshot["tables"]
    expected = (
        "recovery_claims", "review_claims", "settlement_events",
        "allocations", "counter_events", "reversal_edges",
    )
    if set(tables) != set(expected):
        raise RuntimeError("M44_SETTLEMENT_SNAPSHOT_MISSING_TABLES")
    payload = {}
    counts = {}
    for table in expected:
        normalized = list(tables[table])
        normalized.sort(
            key=lambda row: json.dumps(
                row, sort_keys=True, separators=(",",":"), ensure_ascii=False
            )
        )
        payload[table] = normalized
        counts[table] = len(normalized)
    reversed_by_id = {}
    for row in tables["reversal_edges"]:
        key = row["allocation_id"]
        reversed_by_id[key] = reversed_by_id.get(key,0)+row["amount_cents"]
    realized = sum(row["amount_cents"] for row in tables["allocations"]) - sum(
        row["amount_cents"] for row in tables["reversal_edges"]
    )
    eligible = sum(
        max(0,row["fee_eligible_cents"]-reversed_by_id.get(row["allocation_id"],0))
        for row in tables["allocations"]
        if row["fee_eligible_cents"] == row["amount_cents"]
    )
    return {
        "counts": counts,
        "settlement_content_hash":
            canonical_hash({"schema":1,"tables":payload}),
        "realized_cents": realized,
        "fee_eligible_cents": eligible,
    }


def workspace_summary(
    audit: AuditStore,
    settlement: SettlementStore,
) -> WorkspaceSemanticSummary:
    if (audit.buyer_id,audit.business_unit)!=(settlement.buyer_id,settlement.business_unit):
        raise ValueError("audit/settlement workspace scope mismatch")
    # One consistent audit chain/count/head revision. The former verify(),
    # count() and head() calls ran as THREE unrelated read transactions.
    audit_state=audit.semantic_summary()
    # All settlement counts and cents are derived from the exact SAME
    # semantically validated source snapshot, not six independent read views.
    settlement_state=_settlement_content(settlement)
    counts=settlement_state["counts"]
    body={
        "buyer_id":audit.buyer_id,
        "business_unit":audit.business_unit,
        "audit_record_count":audit_state["record_count"],
        "audit_chain_head":audit_state["chain_head"],
        "recovery_claim_count":counts["recovery_claims"],
        "review_claim_count":counts["review_claims"],
        "settlement_event_count":counts["settlement_events"],
        "allocation_count":counts["allocations"],
        "counter_event_count":counts["counter_events"],
        "reversal_edge_count":counts["reversal_edges"],
        "realized_cents":settlement_state["realized_cents"],
        "fee_eligible_cents":settlement_state["fee_eligible_cents"],
        "settlement_content_hash":settlement_state["settlement_content_hash"],
    }
    return WorkspaceSemanticSummary(
        **body,
        semantic_hash=canonical_hash({"schema":1,**body}),
    )


def run_backup_restore_drill(
    audit: AuditStore,
    settlement: SettlementStore,
    *,
    work_dir: str | Path,
) -> BackupRestoreResult:
    """Publish complete 2-file backup only after stable-window acceptance.

    This is NOT a distributed transaction. Two independent SQLite files do
    not share a commit clock or snapshot; the original and restored
    ALL-tenant semantic bytes are checked both before and after capture.
    Concurrent writes trigger fail-closed rejection, not a false success
    report. A publication marker is written LAST.
    """
    if (audit.buyer_id,audit.business_unit)!=(settlement.buyer_id,settlement.business_unit):
        raise ValueError("audit/settlement workspace scope mismatch")

    root=Path(work_dir).absolute()
    parent=root.parent
    parent.mkdir(parents=True,exist_ok=True)
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise RuntimeError("M49_BACKUP_OUTPUT_DIRECTORY_NOT_TRUSTWORTHY")
    files=(*_capture_files(),"capture.complete.json")
    if any(os.path.lexists(root/name) for name in files):
        raise RuntimeError("M49_EXISTING_BACKUP_ARTIFACT_MUST_NOT_BE_OVERWRITTEN")

    # Source preflight remains READ ONLY (no files or records published).
    audit._assert_source_identity()
    settlement._assert_path_identity()
    before=workspace_summary(audit,settlement)
    original_full={
        "audit":_logical_sqlite_hash(Path(audit.path),"audit"),
        "settlement":_logical_sqlite_hash(Path(settlement.path),"settlement"),
    }
    published=[]
    newly_created_directory=False
    with tempfile.TemporaryDirectory(prefix=".retally-m49-stage-",dir=parent) as stage_dir:
        staged=Path(stage_dir)
        ab=staged/"audit.backup.sqlite3"
        sb=staged/"settlement.backup.sqlite3"
        ar=staged/"audit.restored.sqlite3"
        sr=staged/"settlement.restored.sqlite3"
        _sqlite_backup(Path(audit.path),ab)
        audit._assert_source_identity()
        _sqlite_backup(Path(settlement.path),sb)
        settlement._assert_path_identity()
        # Both copies must match the ORIGINAL first-window all-tenant
        # content, not merely scoped totals or original file byte hashes.
        backed={
            "audit":_logical_sqlite_hash(ab,"audit"),
            "settlement":_logical_sqlite_hash(sb,"settlement"),
        }
        if backed!=original_full:
            raise RuntimeError("M49_CAPTURE_CHANGED_BETWEEN_SOURCE_AND_BACKUP")
        _restore_copy(ab,ar)
        _restore_copy(sb,sr)

        restored_audit=AuditStore(
            ar,buyer_id=audit.buyer_id,business_unit=audit.business_unit)
        restored_settlement=SettlementStore(
            sr,buyer_id=settlement.buyer_id,business_unit=settlement.business_unit)
        after=workspace_summary(restored_audit,restored_settlement)
        restored_full={
            "audit":_logical_sqlite_hash(ar,"audit"),
            "settlement":_logical_sqlite_hash(sr,"settlement"),
        }
        if asdict(before)!=asdict(after) or restored_full!=original_full:
            raise RuntimeError("M49_RESTORED_DUAL_LEDGER_SNAPSHOT_NOT_EQUIVALENT")

        # Repeat ORIGINAL audit and settlement checks *after* both copies
        # and restores. A writer racing the backup must invalidate it,
        # including changes by OTHER tenant scopes in either database.
        audit._assert_source_identity()
        settlement._assert_path_identity()
        final_summary=workspace_summary(audit,settlement)
        final_full={
            "audit":_logical_sqlite_hash(Path(audit.path),"audit"),
            "settlement":_logical_sqlite_hash(Path(settlement.path),"settlement"),
        }
        if asdict(before)!=asdict(final_summary) or final_full!=original_full:
            raise RuntimeError("M49_SOURCE_CHANGED_DURING_DUAL_LEDGER_CAPTURE")
        body={
            "schema":1,
            "buyer_id":audit.buyer_id,
            "business_unit":audit.business_unit,
            "source_semantic_hash":before.semantic_hash,
            "restored_semantic_hash":after.semantic_hash,
            "audit_backup_sha256":_file_hash(ab),
            "settlement_backup_sha256":_file_hash(sb),
            "audit_restore_sha256":_file_hash(ar),
            "settlement_restore_sha256":_file_hash(sr),
        }
        result=BackupRestoreResult(
            **{k:v for k,v in body.items() if k!="schema"},
            proof_hash=canonical_hash(body),
        )
        _manifest=_bundle_record(result,original_full)
        (staged/"capture.complete.json").write_text(
            json.dumps(_manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        # Publish only now. os.link uses exclusive create and never
        # overwrites existing unrelated customer artifacts. Linking the
        # completion marker LAST marks a complete recoverable bundle.
        # Failure rolls back only OUR links; staging is auto-discarded.
        try:
            if root.is_symlink():
                raise RuntimeError("M49_BACKUP_OUTPUT_DIRECTORY_NOT_TRUSTWORTHY")
            if not root.exists():
                root.mkdir()
                newly_created_directory=True
            for name in files:
                dest=root/name
                if os.path.lexists(dest):
                    raise RuntimeError("M49_EXISTING_BACKUP_ARTIFACT_MUST_NOT_BE_OVERWRITTEN")
                os.link(staged/name,dest)
                published.append(dest)
            verify_backup_bundle(root,result)
        except BaseException:
            for dest in reversed(published):
                dest.unlink(missing_ok=True)
            if newly_created_directory:
                try:
                    root.rmdir()
                except OSError:
                    pass
            raise
        return result


def verify_backup_restore_result(result: BackupRestoreResult) -> None:
    if type(result) is not BackupRestoreResult:
        raise ValueError("M49_INVALID_DUAL_LEDGER_RESULT_TYPE")
    if result.source_semantic_hash!=result.restored_semantic_hash:
        raise ValueError("backup/restore semantic hashes differ")
    from freight.settlement_schema_guard_m46 import SCHEMA_GIT_BLOB_SHA1
    # Retain prior public return type but verify its LOCAL receipt semantic
    # body, not just the lengths of arbitrarily supplied hash strings.
    body={"schema":1,**{
        k:v for k,v in asdict(result).items() if k!="proof_hash"
    }}
    for field in (
        result.audit_backup_sha256,
        result.settlement_backup_sha256,
        result.audit_restore_sha256,
        result.settlement_restore_sha256,
        result.proof_hash,
        result.source_semantic_hash,
        result.restored_semantic_hash,
    ):
        if (type(field) is not str or len(field)!=64
            or any(c not in "0123456789abcdef" for c in field)):
            raise ValueError("M49_INVALID_PROOF_HASH_FORMAT")
    if canonical_hash(body)!=result.proof_hash:
        raise ValueError("M49_REHASHED_OR_MISMATCHED_LOCAL_BACKUP_RESULT")
