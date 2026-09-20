from pathlib import Path

import pytest

from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore
from freight.backup_restore import (
    run_backup_restore_drill,
    verify_backup_restore_result,
    workspace_summary,
)
from freight.settlement_store import (
    ALLOCATED,
    RecoveryClaim,
    SettlementEventRecord,
    SettlementStore,
)


BUYER="BUYER-A"
BU="OPS"


def populated(tmp_path):
    audit=AuditStore(
        tmp_path/"audit.sqlite3",
        buyer_id=BUYER,
        business_unit=BU,
    )
    audit.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="invoice-source",
        occurred_at="2026-09-20T12:00:00Z",
        evidence_hash="a"*64,
    )
    audit.append(
        event_type=AuditEventType.TRUTH_FROZEN,
        object_id="truth",
        occurred_at="2026-09-20T12:01:00Z",
        evidence_hash="b"*64,
    )

    settlement=SettlementStore(
        tmp_path/"settlement.sqlite3",
        buyer_id=BUYER,
        business_unit=BU,
    )
    settlement.create_claim(
        RecoveryClaim(
            "c1","INV-1","carrier","buyer","USD",50000,
            "2026-09-20T10:00:00Z","claim-src",False,
        )
    )
    settlement.ingest_event(
        SettlementEventRecord(
            "e1","INV-1","carrier","buyer","USD",50000,
            "2026-09-21T10:00:00Z","settle-src","CREDIT-MEMO",
        )
    )
    assert settlement.auto_allocate(
        "e1",created_at="2026-09-21T11:00:00Z"
    ).status==ALLOCATED
    return audit,settlement


def test_backup_restore_proves_semantic_equivalence(tmp_path):
    audit,settlement=populated(tmp_path)
    before=workspace_summary(audit,settlement)
    result=run_backup_restore_drill(
        audit,
        settlement,
        work_dir=tmp_path/"drill",
    )
    verify_backup_restore_result(result)
    assert result.source_semantic_hash==before.semantic_hash
    assert result.source_semantic_hash==result.restored_semantic_hash


def test_wrong_scope_workspace_is_rejected(tmp_path):
    audit,settlement=populated(tmp_path)
    other=SettlementStore(
        tmp_path/"other.sqlite3",
        buyer_id="BUYER-B",
        business_unit=BU,
    )
    with pytest.raises(ValueError,match="scope mismatch"):
        workspace_summary(audit,other)


def test_backup_artifacts_are_real_sqlite_files(tmp_path):
    audit,settlement=populated(tmp_path)
    run_backup_restore_drill(
        audit,
        settlement,
        work_dir=tmp_path/"drill",
    )
    assert (tmp_path/"drill"/"audit.backup.sqlite3").read_bytes().startswith(b"SQLite format 3")
    assert (tmp_path/"drill"/"settlement.backup.sqlite3").read_bytes().startswith(b"SQLite format 3")
