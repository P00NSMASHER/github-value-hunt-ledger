"""RT05: source-declared dispute holds must be binding financial controls.

Everything here is synthetic. A ledger-side dispute hold is NOT proof that a
customer authorized an action, a carrier legally owes money, or a bank cleared
cash. No live interactions or real buyer/contract data.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import sqlite3

import pytest

from freight.settlement_store import (
    SettlementStore, RecoveryClaim, SettlementEventRecord,
    ALLOCATED, REVIEW,
)
from freight.recovery_resilience import (
    RecoveryScenario, RecoveryEvent, evaluate_recovery_scenario,
    record_recovery_dispute_notice,
)
from freight.currency_reporting import (
    build_currency_settlement_report, assert_currency_report_current,
)
from freight.settlement_review_workflow import (
    build_settlement_review_case, apply_settlement_review_decision,
    SettlementReviewDecisionInput,
)
from freight.settlement_report import (
    build_persistent_pilot_report, assert_report_current,
)
from freight import test_settlement_report as reference_case


def sha(s: str) -> str:
    return sha256(s.encode("ascii")).hexdigest()


def store(tmp_path, *, tenant="SYN-BUYER", unit="SYN-UNIT"):
    return SettlementStore(tmp_path / "settle.sqlite3", buyer_id=tenant, business_unit=unit)


def claim(name="SYN-CLAIM", *, amount=10000, ref="SYN-INVOICE", disqualified=False):
    return RecoveryClaim(
        name, ref, "SYN-CARRIER", "SYN-CUSTOMER", "USD", amount,
        "2026-09-01T12:00:00Z", sha("finding:"+name), disqualified,
    )


def credit(name="SYN-CREDIT", *, amount=10000, ref="SYN-INVOICE"):
    return SettlementEventRecord(
        name, ref, "SYN-CARRIER", "SYN-CUSTOMER", "USD",
        amount, "2026-09-02T12:00:00Z", sha("credit:"+name),
        "SYNTHETIC_CREDIT_DECLARATION",
    )


def scenario(name="SYN-CLAIM", *, amount=10000, ref="SYN-INVOICE"):
    return RecoveryScenario(
        case_id=ref, buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
        claim_id=name, payer_id="SYN-CARRIER", payee_id="SYN-CUSTOMER",
        currency="USD", disputed_cents=amount,
        issued_at="2026-09-01T12:00:00.000000Z",
        source_invoice_sha256=sha("original:"+name),
        source_finding_sha256=sha("finding:"+name),
    )


def notice(i=1, kind="CARRIER_DENIAL", *, day=3):
    return RecoveryEvent(
        event_id=f"SYN-NOTICE-{i}",
        kind=kind,
        observed_at=f"2026-09-{day:02}T12:00:00Z",
        source_sha256=sha("fake-letter:"+str(i)),
    )


def bind_notice(s, *, event=None, sc=None):
    return record_recovery_dispute_notice(
        s, scenario=sc or scenario(), notice=event or notice(),
    )


def test_01_carrier_denial_is_persisted_and_blocks_auto_allocation(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    assert bind_notice(s) is True
    s.ingest_event(credit())
    out=s.auto_allocate("SYN-CREDIT",created_at="2026-09-03T13:00:00Z")
    assert out.status == REVIEW
    assert "dispute" in out.reason.lower()
    assert s.count("allocations")==0
    assert s.count("settlement_events")==1
    assert s.fee_eligible_cents()==0
    assert s.dispute_hold_active("SYN-CLAIM") is True
    snapshot=json.loads(s.report_snapshot_json())
    assert len(snapshot["tables"]["claim_dispute_holds"])==1
    assert snapshot["tables"]["claim_dispute_holds"][0]["kind"]=="CARRIER_DENIAL"
    status=evaluate_recovery_scenario(scenario(),as_of="2026-10-22",store=s)
    assert status.state=="DISPUTED_EVIDENCE_HOLD"
    assert status.settlement.dispute_hold_active is True
    assert status.customer_fee_billable_cents==0
    assert status.independently_verified_cash_cents==0


def test_02_disputed_credit_refuses_reviewed_and_manual_case_allocation(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.create_claim(claim("SYN-SECOND"))  # two exact candidates force manual review
    s.ingest_event(credit())
    case=build_settlement_review_case(s,event_id="SYN-CREDIT")
    assert bind_notice(s)
    with pytest.raises(ValueError,match="dispute"):
        s.review_allocate(
            allocation_id="SYN-ALLOC",claim_id="SYN-CLAIM",
            event_id="SYN-CREDIT",amount_cents=10000,
            created_at="2026-09-03T13:00:00Z",
        )
    with pytest.raises(ValueError):
        apply_settlement_review_decision(s,case=case,decision=SettlementReviewDecisionInput(
            case_hash=case.case_hash,claim_id="SYN-CLAIM",
            reviewer_role="SYNTHETIC_REVIEWER_NOT_APPROVAL",
            reviewed_at="2026-09-03T13:00:00Z",rationale="fake review",
        ))
    assert s.count("allocations")==0


def test_03_direct_sql_legacy_writer_cannot_bypass_disputed_claim_hold(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.ingest_event(credit())
    bind_notice(s)
    before=s.report_snapshot_json()
    with sqlite3.connect(s.path) as conn:
        with pytest.raises(sqlite3.IntegrityError,match="dispute"):
            conn.execute(
                "INSERT INTO allocations "
                "(buyer_id,business_unit,allocation_id,claim_id,event_id,"
                "amount_cents,mode,fee_eligible_cents,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("SYN-BUYER","SYN-UNIT","SYN-RAW-ALLOC","SYN-CLAIM",
                 "SYN-CREDIT",10000,"REVIEW",10000,
                 "2026-09-03T13:00:00.000000Z"),
            )
    assert before==s.report_snapshot_json()


def test_04_dispute_arriving_after_credit_removes_fee_eligibility_without_erasure(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    s.ingest_event(credit())
    assert s.auto_allocate("SYN-CREDIT",created_at="2026-09-02T13:00:00Z").status==ALLOCATED
    assert s.realized_cents()==10000 and s.fee_eligible_cents()==10000
    before=build_currency_settlement_report(s)
    assert before.by_currency[0].declared_fee_eligible_net_cents==10000
    assert bind_notice(s) is True
    assert s.realized_cents()==10000  # source-declared accounting remains
    assert s.fee_eligible_cents()==0
    after=build_currency_settlement_report(s)
    assert after.by_currency[0].declared_net_allocated_cents==10000
    assert after.by_currency[0].declared_fee_eligible_net_cents==0
    assert after.report_hash != before.report_hash
    with pytest.raises(ValueError,match="changed"):
        assert_currency_report_current(before,s)
    response=evaluate_recovery_scenario(scenario(),store=s,as_of="2026-10-22")
    assert response.state=="DISPUTED_EVIDENCE_HOLD"
    assert response.settlement.source_declared_net_cents==10000
    assert response.settlement.source_declared_candidate_fee_cents==0
    assert response.feasibility.modeled_contingency_fee_cents is None
    assert response.customer_fee_billable_cents==0


def test_05_original_truth_report_cannot_certify_bound_disputed_claim(tmp_path):
    truth,incumbent,s=reference_case.case(tmp_path)
    finding=truth.findings[0]
    bound=reference_case.add_claim(s,finding)
    reference_case.pay(s,finding)
    before=build_persistent_pilot_report(truth,incumbent,s,(bound,))
    assert before.metrics.fee_eligible_realized_cents==2500
    assert s.place_claim_dispute_hold(
        claim_id="claim-"+finding.finding_id,
        kind="CUSTOMER_DISPUTE",
        source_hash=sha("separate-claim-hold"),
        observed_at="2026-09-03T00:00:00Z",
        expected_claim_source_sha256=finding.proof_hash,
    )
    with pytest.raises(ValueError,match="dispute"):
        build_persistent_pilot_report(truth,incumbent,s,(bound,))
    with pytest.raises(ValueError,match="snapshot changed"):
        assert_report_current(before,s)
    assert s.fee_eligible_cents()==0


def test_06_duplicate_dispute_is_idempotent_and_conflicting_source_fails(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    first=notice()
    assert bind_notice(s,event=first) is True
    assert bind_notice(s,event=first) is False
    modified=replace(first,kind="CUSTOMER_DISPUTE")
    with pytest.raises(ValueError):
        bind_notice(s,event=modified)
    assert s.count("claim_dispute_holds")==1


def test_07_cross_tenant_and_mismatched_claim_source_cannot_be_held(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    foreign=replace(scenario(),buyer_id="OTHER-TENANT")
    with pytest.raises(ValueError,match="scope"):
        bind_notice(s,sc=foreign)
    forged=replace(scenario(),source_finding_sha256=sha("forged"))
    with pytest.raises(ValueError,match="source"):
        bind_notice(s,sc=forged)
    other=store(tmp_path,tenant="OTHER-TENANT")
    with pytest.raises(ValueError,match="unknown"):
        other.place_claim_dispute_hold(
            claim_id="SYN-CLAIM",kind="CARRIER_DENIAL",
            source_hash=sha("fake-other"),observed_at="2026-09-03T12:00:00Z",
            expected_claim_source_sha256=sha("finding:SYN-CLAIM"),
        )


def test_08_ineligible_fake_source_and_preissue_disputes_fail(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    with pytest.raises(ValueError):
        s.place_claim_dispute_hold(
            claim_id="SYN-CLAIM",kind="UNKNOWN_EVENT",
            source_hash=sha("fake-1"),
            observed_at="2026-09-03T12:00:00Z",
            expected_claim_source_sha256=sha("finding:SYN-CLAIM"),
        )
    with pytest.raises(ValueError,match="predate"):
        bind_notice(s,event=replace(notice(day=1),observed_at="2026-09-01T11:59:59Z"))
    with pytest.raises(ValueError,match="independent"):
        s.place_claim_dispute_hold(
            claim_id="SYN-CLAIM",kind="CARRIER_DENIAL",
            source_hash=sha("finding:SYN-CLAIM"),
            observed_at="2026-09-03T12:00:00Z",
            expected_claim_source_sha256=sha("finding:SYN-CLAIM"),
        )
    assert s.count("claim_dispute_holds")==0


def test_09_hold_survives_restart_and_missing_release_auth_cannot_clear(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim())
    bind_notice(s)
    saved=s.report_snapshot_json()
    again=store(tmp_path)
    assert again.report_snapshot_json()==saved
    assert again.dispute_hold_active("SYN-CLAIM")
    # Intentional fail-closed: there is NO synthetic role-string release API.
    assert not hasattr(again,"release_claim_dispute_hold")
    assert again.count("claim_dispute_holds")==1


def test_10_concurrent_dispute_intake_vs_allocation_is_serialized(tmp_path):
    for i in range(12):
        directory=tmp_path/f"iteration-{i}"
        directory.mkdir()
        s=store(directory)
        s.create_claim(claim())
        s.ingest_event(credit())
        bind_notice(s,event=notice(i+1))
        def allocate(_):
            return s.auto_allocate("SYN-CREDIT",created_at="2026-09-03T13:00:00Z")
        with ThreadPoolExecutor(max_workers=8) as executor:
            states=list(executor.map(allocate,range(6)))
        assert all(x.status == REVIEW for x in states)
        assert s.count("allocations")==0


def test_11_multiple_claims_one_denied_no_cross_claim_dispute_spread(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("A",amount=5000,ref="SYN-A"))
    s.create_claim(claim("B",amount=5000,ref="SYN-B"))
    s.ingest_event(credit("SYN-CREDIT-A",amount=5000,ref="SYN-A"))
    s.ingest_event(credit("SYN-CREDIT-B",amount=5000,ref="SYN-B"))
    s.place_claim_dispute_hold(
        claim_id="A",kind="CARRIER_DENIAL",source_hash=sha("denial-A"),
        observed_at="2026-09-03T12:00:00Z",
        expected_claim_source_sha256=sha("finding:A"),
    )
    assert s.auto_allocate("SYN-CREDIT-A",created_at="2026-09-03T13:00:00Z").status==REVIEW
    assert s.auto_allocate("SYN-CREDIT-B",created_at="2026-09-03T13:00:00Z").status==ALLOCATED
    assert s.realized_cents("A")==0
    assert s.realized_cents("B")==5000
    assert s.fee_eligible_cents("A")==0
    assert s.fee_eligible_cents("B")==5000


def test_12_synthetic_stress_100_source_denials_never_approve_cash(tmp_path):
    kinds=("CARRIER_DISPUTE","CARRIER_DENIAL","CUSTOMER_DISPUTE",
           "INSOLVENCY_NOTICE","CUSTOMER_WITHDRAWAL")
    for i in range(100):
        p=tmp_path/f"stress-{i}"
        p.mkdir()
        s=store(p)
        s.create_claim(claim(amount=10000+i))
        s.ingest_event(credit(amount=10000+i))
        event=notice(i+5,kind=kinds[i%len(kinds)])
        assert bind_notice(s,event=event,sc=scenario(amount=10000+i)) is True
        assert s.auto_allocate("SYN-CREDIT",created_at="2026-09-03T13:00:00Z").status==REVIEW
        with pytest.raises(ValueError):
            s.review_allocate(
                allocation_id="M"+str(i),claim_id="SYN-CLAIM",
                event_id="SYN-CREDIT",amount_cents=10000+i,
                created_at="2026-09-03T13:00:00Z",
            )
        audit=evaluate_recovery_scenario(scenario(amount=10000+i),
                                         as_of="2026-10-22",store=s)
        assert audit.state in ("DISPUTED_EVIDENCE_HOLD","INSOLVENCY_LEGAL_HOLD",
                               "CUSTOMER_WITHDRAWAL_REVIEW_HOLD")
        assert audit.customer_fee_billable_cents==0
        assert audit.independently_verified_cash_cents==0
