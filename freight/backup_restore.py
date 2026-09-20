"""Semantic backup/restore drill for Freight Recovery pilot evidence.

The drill backs up scoped audit + settlement SQLite stores using SQLite's backup
API, restores them into fresh files, then compares business semantics after
restore. A copied file alone is not accepted as recovery proof.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
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
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        destination.unlink()
    src=sqlite3.connect(str(source))
    dst=sqlite3.connect(str(destination))
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()


def _restore_copy(source_backup: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        destination.unlink()
    # Restore through SQLite backup rather than filesystem copy so the restored
    # database is a fresh SQLite image.
    _sqlite_backup(source_backup,destination)


def _settlement_content(settlement: SettlementStore) -> tuple[int, int, str]:
    tables=(
        "recovery_claims",
        "review_claims",
        "settlement_events",
        "allocations",
        "counter_events",
        "reversal_edges",
    )
    conn=sqlite3.connect(settlement.path)
    conn.row_factory=sqlite3.Row
    try:
        payload={}
        counts={}
        for table in tables:
            rows=conn.execute(
                f"SELECT * FROM {table} WHERE buyer_id=? AND business_unit=?",
                (settlement.buyer_id,settlement.business_unit),
            ).fetchall()
            normalized=[dict(row) for row in rows]
            normalized.sort(
                key=lambda row: json.dumps(
                    row,sort_keys=True,separators=(",",":"),ensure_ascii=False
                )
            )
            payload[table]=normalized
            counts[table]=len(normalized)
    finally:
        conn.close()
    return (
        counts["recovery_claims"],
        counts["review_claims"],
        canonical_hash({"schema":1,"tables":payload}),
    )


def workspace_summary(
    audit: AuditStore,
    settlement: SettlementStore,
) -> WorkspaceSemanticSummary:
    if (audit.buyer_id,audit.business_unit)!=(settlement.buyer_id,settlement.business_unit):
        raise ValueError("audit/settlement workspace scope mismatch")
    audit.verify()
    recovery_claim_count,review_claim_count,settlement_content_hash=_settlement_content(
        settlement
    )
    body={
        "buyer_id":audit.buyer_id,
        "business_unit":audit.business_unit,
        "audit_record_count":audit.count(),
        "audit_chain_head":audit.head(),
        "recovery_claim_count":recovery_claim_count,
        "review_claim_count":review_claim_count,
        "settlement_event_count":settlement.count("settlement_events"),
        "allocation_count":settlement.count("allocations"),
        "counter_event_count":settlement.count("counter_events"),
        "reversal_edge_count":settlement.count("reversal_edges"),
        "realized_cents":settlement.realized_cents(),
        "fee_eligible_cents":settlement.fee_eligible_cents(),
        "settlement_content_hash":settlement_content_hash,
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
    if (audit.buyer_id,audit.business_unit)!=(settlement.buyer_id,settlement.business_unit):
        raise ValueError("audit/settlement workspace scope mismatch")

    root=Path(work_dir)
    root.mkdir(parents=True,exist_ok=True)
    audit_backup=root/"audit.backup.sqlite3"
    settlement_backup=root/"settlement.backup.sqlite3"
    audit_restore=root/"audit.restored.sqlite3"
    settlement_restore=root/"settlement.restored.sqlite3"

    before=workspace_summary(audit,settlement)

    _sqlite_backup(Path(audit.path),audit_backup)
    _sqlite_backup(Path(settlement.path),settlement_backup)
    audit_backup_hash=_file_hash(audit_backup)
    settlement_backup_hash=_file_hash(settlement_backup)

    _restore_copy(audit_backup,audit_restore)
    _restore_copy(settlement_backup,settlement_restore)

    restored_audit=AuditStore(
        audit_restore,
        buyer_id=audit.buyer_id,
        business_unit=audit.business_unit,
    )
    restored_settlement=SettlementStore(
        settlement_restore,
        buyer_id=settlement.buyer_id,
        business_unit=settlement.business_unit,
    )
    after=workspace_summary(restored_audit,restored_settlement)
    if asdict(before)!=asdict(after):
        raise ValueError("restored workspace semantic mismatch")

    body={
        "schema":1,
        "buyer_id":audit.buyer_id,
        "business_unit":audit.business_unit,
        "source_semantic_hash":before.semantic_hash,
        "restored_semantic_hash":after.semantic_hash,
        "audit_backup_sha256":audit_backup_hash,
        "settlement_backup_sha256":settlement_backup_hash,
        "audit_restore_sha256":_file_hash(audit_restore),
        "settlement_restore_sha256":_file_hash(settlement_restore),
    }
    return BackupRestoreResult(
        buyer_id=body["buyer_id"],
        business_unit=body["business_unit"],
        source_semantic_hash=body["source_semantic_hash"],
        restored_semantic_hash=body["restored_semantic_hash"],
        audit_backup_sha256=body["audit_backup_sha256"],
        settlement_backup_sha256=body["settlement_backup_sha256"],
        audit_restore_sha256=body["audit_restore_sha256"],
        settlement_restore_sha256=body["settlement_restore_sha256"],
        proof_hash=canonical_hash(body),
    )


def verify_backup_restore_result(result: BackupRestoreResult) -> None:
    if result.source_semantic_hash!=result.restored_semantic_hash:
        raise ValueError("backup/restore semantic hashes differ")
    for field in (
        result.audit_backup_sha256,
        result.settlement_backup_sha256,
        result.audit_restore_sha256,
        result.settlement_restore_sha256,
        result.proof_hash,
    ):
        if len(field)!=64:
            raise ValueError("backup/restore proof contains invalid SHA-256")
