"""Deterministic negative isolation rehearsal for Freight Recovery persistence.

This is repository/internal evidence for FRT-SEC-001. It proves the current
scope-bound SQLite stores isolate buyer + business-unit data under adversarial
same-ID and cross-scope conditions. It is not a substitute for deployed pilot
service logs or deployed multi-tenant authorization evidence.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from freight.audit_ledger import AuditEventType
from freight.audit_store import AuditStore
from freight.contracts import canonical_hash
from freight.settlement_store import (
    ALLOCATED,
    REVIEW,
    RecoveryClaim,
    SettlementEventRecord,
    SettlementStore,
)


@dataclass(frozen=True)
class IsolationCheck:
    check_id: str
    passed: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class TenantIsolationEvidence:
    schema_version: int
    gap_id: str
    scope_model: str
    tested_scopes: tuple[str, ...]
    check_count: int
    passed_count: int
    checks: tuple[IsolationCheck, ...]
    deployed_multi_tenant_claimed: bool
    denied_attempt_audit_log_claimed: bool
    remaining_evidence: tuple[str, ...]
    evidence_hash: str


def _claim(
    claim_id: str = "same-claim",
    reference: str = "INV-SAME",
    amount_cents: int = 2500,
) -> RecoveryClaim:
    return RecoveryClaim(
        claim_id,
        reference,
        "carrier",
        "customer",
        "USD",
        amount_cents,
        "2026-09-21T09:00:00Z",
        "same-claim-source",
        False,
    )


def _event(
    event_id: str = "same-event",
    reference: str = "INV-SAME",
    amount_cents: int = 2500,
) -> SettlementEventRecord:
    return SettlementEventRecord(
        event_id,
        reference,
        "carrier",
        "customer",
        "USD",
        amount_cents,
        "2026-09-21T10:00:00Z",
        "same-settlement-source",
        "SYNTHETIC-EVIDENCE",
    )


def _check(check_id: str, passed: bool, *evidence: str) -> IsolationCheck:
    if not passed:
        raise AssertionError(check_id + " failed")
    return IsolationCheck(check_id, True, tuple(evidence))


def run_tenant_isolation_rehearsal() -> TenantIsolationEvidence:
    scopes = (
        ("BUYER-A", "OPS"),
        ("BUYER-A", "FIN"),
        ("BUYER-B", "OPS"),
    )
    checks: list[IsolationCheck] = []

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        settlement_path = root / "shared-settlement.sqlite3"
        audit_path = root / "shared-audit.sqlite3"

        settlement = {
            scope: SettlementStore(
                settlement_path,
                buyer_id=scope[0],
                business_unit=scope[1],
            )
            for scope in scopes
        }

        # Same local IDs and source hashes are intentionally reused in all
        # scopes. Scope must be part of durable identity.
        for store in settlement.values():
            assert store.create_claim(_claim())
            assert store.ingest_event(_event())
            assert store.auto_allocate(
                "same-event",
                created_at="2026-09-21T10:01:00Z",
            ).status == ALLOCATED

        checks.append(_check(
            "SETTLEMENT_SAME_LOCAL_IDS_COEXIST",
            all(store.count("recovery_claims") == 1 for store in settlement.values())
            and all(store.count("settlement_events") == 1 for store in settlement.values())
            and all(store.count("allocations") == 1 for store in settlement.values()),
            "same claim_id/event_id/source hashes inserted independently",
            "three buyer/business-unit scopes retain one local row each",
        ))
        checks.append(_check(
            "SETTLEMENT_SCOPE_BOUND_TOTALS",
            all(store.realized_cents() == 2500 for store in settlement.values()),
            "each scope reports only its own 2500-cent allocation",
        ))

        # A new buyer-B event must not match a claim that exists only in
        # buyer-A/OPS even when the business reference is identical.
        cross_claim = _claim("cross-claim", "INV-CROSS", 4000)
        cross_event = _event("cross-event", "INV-CROSS", 4000)
        assert settlement[("BUYER-A", "OPS")].create_claim(cross_claim)
        assert settlement[("BUYER-B", "OPS")].ingest_event(cross_event)
        decision = settlement[("BUYER-B", "OPS")].auto_allocate(
            "cross-event",
            created_at="2026-09-21T10:02:00Z",
        )
        checks.append(_check(
            "SETTLEMENT_CROSS_BUYER_MATCH_DENIED",
            decision.status == REVIEW
            and "count=0" in decision.reason
            and settlement[("BUYER-A", "OPS")].realized_cents("cross-claim") == 0,
            "buyer-B settlement cannot discover buyer-A claim by reference",
        ))
        try:
            settlement[("BUYER-B", "OPS")].review_allocate(
                allocation_id="cross-allocation",
                claim_id="cross-claim",
                event_id="cross-event",
                amount_cents=4000,
                created_at="2026-09-21T10:03:00Z",
            )
        except ValueError as exc:
            review_denied = "existing claim and settlement event" in str(exc)
        else:
            review_denied = False
        checks.append(_check(
            "SETTLEMENT_CROSS_BUYER_REVIEW_DENIED",
            review_denied,
            "manual review allocation cannot bind another buyer's claim",
        ))

        # Same buyer, different BU must be isolated too.
        bu_claim = _claim("bu-only", "INV-BU", 3000)
        assert settlement[("BUYER-A", "OPS")].create_claim(bu_claim)
        try:
            settlement[("BUYER-A", "FIN")].claim_residual("bu-only")
        except ValueError as exc:
            bu_read_denied = "unknown recovery claim" in str(exc)
        else:
            bu_read_denied = False
        checks.append(_check(
            "SETTLEMENT_CROSS_BU_READ_DENIED",
            bu_read_denied,
            "BUYER-A/FIN cannot read BUYER-A/OPS claim",
        ))

        # Database foreign keys include buyer+BU; even direct SQL cannot bind a
        # claim from one scope to an event from another under a forged scope.
        sql_cross_denied = False
        conn = sqlite3.connect(settlement_path)
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            conn.execute(
                """INSERT INTO allocations
                   (buyer_id,business_unit,allocation_id,claim_id,event_id,
                    amount_cents,mode,fee_eligible_cents,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    "BUYER-B",
                    "OPS",
                    "sql-cross",
                    "cross-claim",
                    "cross-event",
                    4000,
                    "REVIEW",
                    4000,
                    "2026-09-21T10:04:00Z",
                ),
            )
        except sqlite3.IntegrityError as exc:
            sql_cross_denied = "FOREIGN KEY constraint failed" in str(exc)
        finally:
            conn.rollback()
            conn.close()
        checks.append(_check(
            "SETTLEMENT_DIRECT_SQL_CROSS_SCOPE_DENIED",
            sql_cross_denied,
            "composite foreign keys reject cross-scope claim/event binding",
        ))

        settlement_snapshots = tuple(
            settlement[scope].snapshot_hash() for scope in scopes
        )
        checks.append(_check(
            "SETTLEMENT_SCOPE_SNAPSHOTS_DISTINCT",
            len(set(settlement_snapshots)) == 3,
            "scope-bound snapshots differ after scope-specific adversarial rows",
        ))

        audits = {
            scope: AuditStore(
                audit_path,
                buyer_id=scope[0],
                business_unit=scope[1],
            )
            for scope in scopes
        }
        for store in audits.values():
            store.append(
                event_type=AuditEventType.SOURCE_PRESENT,
                object_id="same-object",
                occurred_at="2026-09-21T11:00:00Z",
                evidence_hash="a" * 64,
            )
            store.verify()

        checks.append(_check(
            "AUDIT_SAME_LOCAL_OBJECT_COEXISTS",
            all(store.count() == 1 for store in audits.values()),
            "same object ID/evidence hash recorded independently in three scopes",
        ))
        checks.append(_check(
            "AUDIT_SCOPE_BOUND_RECORDS",
            all(
                tuple((record.buyer_id, record.business_unit) for record in store.records())
                == (scope,)
                for scope, store in audits.items()
            ),
            "each AuditStore read returns only its constructor scope",
        ))
        audit_heads = tuple(audits[scope].head() for scope in scopes)
        checks.append(_check(
            "AUDIT_CHAINS_SCOPE_BOUND",
            len(set(audit_heads)) == 3,
            "buyer/business-unit identity is included in independent audit chains",
        ))

        # A raw database query confirms all three scope rows coexist physically,
        # while every service read above remained scoped.
        conn = sqlite3.connect(audit_path)
        scope_rows = tuple(
            conn.execute(
                """SELECT buyer_id,business_unit,COUNT(*)
                   FROM audit_events
                   GROUP BY buyer_id,business_unit
                   ORDER BY buyer_id,business_unit"""
            ).fetchall()
        )
        conn.close()
        checks.append(_check(
            "AUDIT_SHARED_DB_CONTAINS_SEPARATE_SCOPES",
            scope_rows
            == (
                ("BUYER-A", "FIN", 1),
                ("BUYER-A", "OPS", 1),
                ("BUYER-B", "OPS", 1),
            ),
            "shared DB physically contains all scopes without service-layer leakage",
        ))

    checks_tuple = tuple(checks)
    body = {
        "schema_version": 1,
        "gap_id": "FRT-SEC-001",
        "scope_model": "buyer_id + business_unit",
        "tested_scopes": tuple(f"{buyer}/{bu}" for buyer, bu in scopes),
        "check_count": len(checks_tuple),
        "passed_count": len(checks_tuple),
        "checks": [asdict(check) for check in checks_tuple],
        "deployed_multi_tenant_claimed": False,
        "denied_attempt_audit_log_claimed": False,
        "remaining_evidence": (
            "Run equivalent negative cross-scope attempts against the actual pilot data service.",
            "Capture deployed authorization/tenant context for those attempts.",
            "Capture audit/security logs proving denied cross-scope attempts.",
        ),
    }
    return TenantIsolationEvidence(
        schema_version=1,
        gap_id="FRT-SEC-001",
        scope_model="buyer_id + business_unit",
        tested_scopes=body["tested_scopes"],
        check_count=len(checks_tuple),
        passed_count=len(checks_tuple),
        checks=checks_tuple,
        deployed_multi_tenant_claimed=False,
        denied_attempt_audit_log_claimed=False,
        remaining_evidence=body["remaining_evidence"],
        evidence_hash=canonical_hash(body),
    )


if __name__ == "__main__":
    print(json.dumps(asdict(run_tenant_isolation_rehearsal()), indent=2))
