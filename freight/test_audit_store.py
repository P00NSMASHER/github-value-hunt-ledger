from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore


def S(tmp_path, buyer="BUYER-A", bu="OPS"):
    return AuditStore(
        tmp_path / "audit.sqlite3",
        buyer_id=buyer,
        business_unit=bu,
    )


def test_persistent_audit_roundtrip_and_scope(tmp_path):
    s=S(tmp_path)
    s.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="source-1",
        occurred_at="2026-09-20T12:00:00Z",
        evidence_hash="a" * 64,
    )
    s.append(
        event_type=AuditEventType.TRUTH_FROZEN,
        object_id="truth-1",
        occurred_at="2026-09-20T12:01:00Z",
        evidence_hash="b" * 64,
    )
    summary=s.semantic_summary()
    assert summary["record_count"]==2
    assert summary["chain_head"]==s.records()[-1].event_hash

    reopened=AuditStore(
        tmp_path / "audit.sqlite3",
        buyer_id="BUYER-A",
        business_unit="OPS",
    )
    assert reopened.semantic_summary()==summary


def test_same_database_isolated_by_buyer_scope(tmp_path):
    path=tmp_path/"shared.sqlite3"
    a=AuditStore(path,buyer_id="BUYER-A",business_unit="OPS")
    b=AuditStore(path,buyer_id="BUYER-B",business_unit="OPS")
    a.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="same",
        occurred_at="2026-09-20T12:00:00Z",
    )
    b.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="same",
        occurred_at="2026-09-20T12:00:00Z",
    )
    assert a.count()==1 and b.count()==1
    assert a.records()[0].buyer_id=="BUYER-A"
    assert b.records()[0].buyer_id=="BUYER-B"


def test_direct_sql_update_and_delete_are_blocked(tmp_path):
    s=S(tmp_path)
    s.append(
        event_type=AuditEventType.SOURCE_PRESENT,
        object_id="source-1",
        occurred_at="2026-09-20T12:00:00Z",
    )
    conn=sqlite3.connect(s.path)
    with pytest.raises(sqlite3.IntegrityError,match="immutable"):
        conn.execute(
            "UPDATE audit_events SET object_id='tamper' "
            "WHERE buyer_id='BUYER-A' AND business_unit='OPS' AND sequence=1"
        )
    with pytest.raises(sqlite3.IntegrityError,match="immutable"):
        conn.execute(
            "DELETE FROM audit_events "
            "WHERE buyer_id='BUYER-A' AND business_unit='OPS' AND sequence=1"
        )
    conn.close()


def test_concurrent_appends_preserve_one_monotonic_chain(tmp_path):
    path=tmp_path/"audit.sqlite3"
    def worker(i):
        store=AuditStore(path,buyer_id="BUYER-A",business_unit="OPS")
        return store.append(
            event_type=AuditEventType.SOURCE_PRESENT,
            object_id=f"source-{i}",
            occurred_at=f"2026-09-20T12:{i:02d}:00Z",
        ).sequence

    with ThreadPoolExecutor(max_workers=8) as pool:
        sequences=list(pool.map(worker,range(20)))

    store=AuditStore(path,buyer_id="BUYER-A",business_unit="OPS")
    store.verify()
    assert sorted(sequences)==list(range(1,21))
    assert store.count()==20
