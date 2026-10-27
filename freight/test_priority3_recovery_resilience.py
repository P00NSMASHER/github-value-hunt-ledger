"""Priority 3 difficult recovery adversarial tests: entirely synthetic/offline.

No carrier contacts, signing, customer identities, provider credentials, bank
proof, legal outcome, money movement, or recoverable commercial value.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256

import pytest

from freight.recovery_resilience import (
    CustomerRequest, FeasibilityAssumptions, RecoveryEvent, RecoveryScenario,
    evaluate_recovery_scenario,
)
from freight.settlement_store import (
    RecoveryClaim, SettlementEventRecord,
    CounterEventRecord, SettlementStore,
)


def H(x: str) -> str:
    return sha256(x.encode("utf-8")).hexdigest()


def scenario(n=1, *, claim_cents=10000, currency="USD", **kwargs):
    return RecoveryScenario(
        case_id=f"SYN-C-{n}", claim_id=f"SYN-CLAIM-{n}",
        buyer_id="SYN-BUYER", business_unit="SYN-UNIT",
        payer_id="SYN-CARRIER", payee_id="SYN-BUYER",
        currency=currency, disputed_cents=claim_cents,
        issued_at="2026-09-01T10:00:00Z",
        source_invoice_sha256=H(f"invoice-{n}"),
        source_finding_sha256=H(f"finding-{n}"),
        **kwargs,
    )


def event(n: int, kind: str, *,
          when="2026-09-05T12:00:00Z", amount=None, ref=None, prefix="source"):
    return RecoveryEvent(
        event_id=f"SYN-E-{n}", kind=kind, observed_at=when,
        source_sha256=H(f"{prefix}-{n}"), amount_cents=amount, ref_event_id=ref,
    )


def request(n: int, kind: str, *, payee=None, when="2026-09-06T12:00:00Z"):
    return CustomerRequest(
        request_id=f"SYN-R-{n}", kind=kind, requested_at=when,
        source_sha256=H(f"request-{n}"), requested_payee_id=payee,
    )


def evaluate(c=None, *, events=(), requests=(), assumptions=None,
             as_of="2026-10-22", store=None):
    return evaluate_recovery_scenario(
        c or scenario(), events=events, customer_requests=requests,
        assumptions=assumptions, as_of=as_of, store=store,
    )


def assert_safe(out):
    assert out.externally_approved_case is False
    assert out.carrier_contact_attempts == 0
    assert out.payment_actions_performed == 0
    assert out.independently_verified_cash_cents == 0
    assert out.customer_fee_billable_cents == 0
    assert out.feasibility.no_billable_fee_authority
    assert all(x.no_money_movement and x.no_external_action for x in out.customer_request_triage)
    assert len(out.report_hash) == 64 and len(out.evidence_hash) == 64
    assert "NO_INDEPENDENT_FREIGHT_ADJUDICATION" in out.blockers


@pytest.mark.parametrize(("kind", "expected"), [
    ("CARRIER_DISPUTE", "DISPUTED_EVIDENCE_HOLD"),
    ("CARRIER_DENIAL", "DISPUTED_EVIDENCE_HOLD"),
    ("INSOLVENCY_NOTICE", "INSOLVENCY_LEGAL_HOLD"),
    ("CARRIER_OUT_OF_BUSINESS", "INSOLVENCY_LEGAL_HOLD"),
    ("CLAIM_TIME_BAR_CONCERN", "CONTRACTUAL_TIME_BAR_REVIEW_HOLD"),
    ("CUSTOMER_DISPUTE", "DISPUTED_EVIDENCE_HOLD"),
    ("CUSTOMER_WITHDRAWAL", "CUSTOMER_WITHDRAWAL_REVIEW_HOLD"),
    ("PAYMENT_REVERSAL_NOTICE", "RETURN_REVERSAL_REVIEW_HOLD"),
    ("DELAY_NOTICE", "DELAY_AND_AGING_REVIEW_HOLD"),
    ("PARTIAL_OFFER", "UNVERIFIED_CARRIER_OFFER_REVIEW"),
    ("ACCOUNT_CREDIT_OFFER", "UNVERIFIED_CARRIER_OFFER_REVIEW"),
])
def test_difficult_carrier_events_hold_without_claiming_recovery(kind, expected):
    kwargs={"amount":2500} if kind.endswith("_OFFER") else {}
    out=evaluate(events=(event(1, kind, **kwargs),))
    assert out.state == expected
    assert_safe(out)
    if kind in {"INSOLVENCY_NOTICE","CARRIER_OUT_OF_BUSINESS"}:
        assert "REFER_TO_AUTHORIZED_INSOLVENCY_AND_CONTRACT_COUNSEL" in out.next_safe_actions
    if kind.endswith("_OFFER"):
        assert "UNVERIFIED_OFFER_NOT_REAL_SETTLEMENT" in out.blockers


@pytest.mark.parametrize(("kind","payee","decision"), [
    ("GUARANTEED_RECOVERY",None,"DENY_UNSUPPORTED_FINANCIAL_CLAIM"),
    ("FORCE_RECOVERY_CLAIM",None,"DENY_UNSUPPORTED_FINANCIAL_CLAIM"),
    ("IMMEDIATE_SETTLEMENT",None,"HOLD_FOR_VALID_CUSTOMER_AUTHORIZATION"),
    ("FAST_TRACK_PROVIDER_PAYMENT",None,"HOLD_FOR_VALID_CUSTOMER_AUTHORIZATION"),
    ("PAY_AFFILIATE","SYN-AFFILIATE","REAUTHORIZE_NEW_VERIFIED_RECIPIENT"),
    ("NEW_PAYEE","SYN-NEW-RECIPIENT","REAUTHORIZE_NEW_VERIFIED_RECIPIENT"),
    ("CROSS_TENANT_MERGE",None,"DENY_CROSS_CUSTOMER_ACCESS"),
    ("CUSTOMER_DATA_EXPORT",None,"REQUIRE_PRIVATE_RIGHTS_REVIEW"),
    ("DELETE_ALL_EVIDENCE",None,"PRIVACY_AND_RETENTION_LEGAL_HOLD"),
    ("RETENTION_EXCEPTION",None,"PRIVACY_AND_RETENTION_LEGAL_HOLD"),
    ("FEE_WAIVER",None,"COMMERCIAL_TERMS_REVIEW_ONLY"),
    ("DISPUTE_FINDING",None,"SUSPEND_FINDING_FOR_SOURCE_ADJUDICATION"),
    ("CHANGE_CUSTOMER_SCOPE",None,"REJECT_SCOPE_REUSE_AND_RESTART"),
    ("WITHDRAW_CASE",None,"HOLD_CLAIM_FOR_AUTHENTICATED_WITHDRAWAL"),
    ("INVOICE_CORRECTION",None,"REQUIRE_PRIVATE_RIGHTS_REVIEW"),
    ("SANITIZED_READ_ONLY_SUMMARY",None,"PREVIEW_NONCUSTOMER_SYNTHETIC_SUMMARY"),
])
def test_customer_request_safety_triage_never_executes(kind, payee, decision):
    out=evaluate(requests=(request(1,kind,payee=payee),))
    assert out.customer_request_triage[0].decision==decision
    assert_safe(out)
    if kind=="DELETE_ALL_EVIDENCE":
        assert out.state=="RETENTION_PRIVACY_REVIEW_HOLD"
    if kind in {"PAY_AFFILIATE","NEW_PAYEE"}:
        assert "REQUIRE_NEW_INDEPENDENT_PAYEE_IDENTITY_AND_PAYMENT_APPROVAL" in out.next_safe_actions


def test_no_calibrated_probability_means_no_estimated_recovery_or_net_value():
    r=evaluate(assumptions=FeasibilityAssumptions(
        labor_hours=3,cost_per_hour_cents=5000,other_delivery_cost_cents=1000))
    assert r.feasibility.probabilities_empirically_calibrated is False
    assert r.feasibility.modeled_collectible_cents is None
    assert r.feasibility.modeled_contingency_fee_cents is None
    assert r.feasibility.modeled_net_fee_after_cost_cents is None
    assert r.feasibility.economic_route=="PROBABILITY_NOT_ESTABLISHED"
    assert_safe(r)


def test_modeled_probability_is_explicit_hypothesis_and_cash_stays_zero():
    c=scenario(claim_cents=100000)
    out=evaluate(c,assumptions=FeasibilityAssumptions(
        modeled_collection_probability_bps=5000,modeled_fee_rate_bps=3000,
        labor_hours=2,cost_per_hour_cents=3000,
        other_delivery_cost_cents=1000,
    ))
    assert out.feasibility.modeled_collectible_cents==50000
    assert out.feasibility.modeled_contingency_fee_cents==15000
    assert out.feasibility.modeled_delivery_cost_cents==7000
    assert out.feasibility.modeled_net_fee_after_cost_cents==8000
    assert out.feasibility.economic_route=="SOURCE_OR_DISPUTE_HOLD"
    assert_safe(out)


def test_high_cost_or_low_collectibility_raises_economic_hold():
    out=evaluate(scenario(claim_cents=10000),assumptions=FeasibilityAssumptions(
        modeled_collection_probability_bps=1000, modeled_fee_rate_bps=3000,
        labor_hours=3,cost_per_hour_cents=5000,
    ))
    assert out.feasibility.modeled_net_fee_after_cost_cents==-14700
    assert out.feasibility.economic_route=="ECONOMIC_HOLD_NEGATIVE_OR_ZERO"
    assert_safe(out)


def test_overdue_case_is_planning_alert_not_invented_legal_deadline():
    out=evaluate(events=(event(1,"DELAY_NOTICE"),),as_of="2026-12-01",
        assumptions=FeasibilityAssumptions(target_response_days=30,expected_delay_days=365))
    assert out.overdue_response_days>0
    assert "PLANNING_RESPONSE_TARGET_EXCEEDED_NOT_LEGAL_DEADLINE" in out.blockers
    assert "VERIFY_APPLICABLE_DEADLINE_WITH_AUTHORIZED_RIGHTS_REVIEW" in out.next_safe_actions
    assert_safe(out)


def test_appeal_requires_proven_dispute_reference_and_time_order():
    original=event(1,"CARRIER_DISPUTE",when="2026-09-05T12:00:00Z")
    appeal=event(2,"APPEAL_PREPARED",when="2026-09-06T12:00:00Z",ref=original.event_id)
    good=evaluate(events=(appeal,original))
    assert good.state=="DISPUTED_EVIDENCE_HOLD"
    assert good.events_seen==2
    assert_safe(good)
    with pytest.raises(ValueError,match="appeal"):
        evaluate(events=(appeal,))
    with pytest.raises(ValueError,match="appeal"):
        evaluate(events=(original,replace(appeal,observed_at="2026-09-04T12:00:00Z")))


def test_event_order_independent_receipts_detect_source_mutations():
    a=event(1,"CARRIER_DENIAL",when="2026-09-03T12:00:00Z")
    b=event(2,"CARRIER_EVIDENCE_REQUEST",when="2026-09-06T12:00:00Z")
    first=evaluate(events=(a,b),requests=(request(1,"FEE_WAIVER"),request(2,"GUARANTEED_RECOVERY")))
    second=evaluate(events=(b,a),requests=(request(2,"GUARANTEED_RECOVERY"),request(1,"FEE_WAIVER")))
    assert first.report_hash==second.report_hash
    changed=evaluate(events=(a,replace(b,source_sha256=H("updated-proof"))),
        requests=(request(1,"FEE_WAIVER"),request(2,"GUARANTEED_RECOVERY")))
    assert first.report_hash!=changed.report_hash
    assert_safe(first)


@pytest.mark.parametrize("bad", [None, -1, True, 1.2, 10001])
def test_probability_bounds_and_inputs_are_exact(bad):
    if bad is None:
        assert FeasibilityAssumptions(modeled_collection_probability_bps=None)
        assert FeasibilityAssumptions(modeled_collection_probability_bps=0)
    else:
        with pytest.raises(ValueError):
            FeasibilityAssumptions(modeled_collection_probability_bps=bad)


def test_reused_fake_source_or_duplicate_case_events_fail_closed():
    first=event(1,"CARRIER_DISPUTE")
    second=replace(event(2,"DELAY_NOTICE"),source_sha256=first.source_sha256)
    with pytest.raises(ValueError,match="reused"):
        evaluate(events=(first,second))
    with pytest.raises(ValueError,match="duplicate"):
        evaluate(events=(first,first))


@pytest.mark.parametrize("bad", [10001,0,-1,True,1.5,2**63])
def test_carrier_offer_amounts_fail_outside_claim_capacity(bad):
    if type(bad) is int and 0 < bad <= 2**63 - 1:
        with pytest.raises(ValueError,match="exceeds"):
            evaluate(events=(event(1,"PARTIAL_OFFER",amount=bad),))
    else:
        with pytest.raises(ValueError):
            event(1,"ACCOUNT_CREDIT_OFFER",amount=bad)


def test_nonfinancial_events_cannot_invent_dollars():
    with pytest.raises(ValueError,match="nonfinancial"):
        event(1,"CARRIER_DENIAL",amount=2000)


def test_unknown_requests_and_fake_customer_permissions_fail():
    with pytest.raises(ValueError,match="unsupported"):
        request(1,"DELETE_DATABASE")
    with pytest.raises(ValueError,match="synthetic-only"):
        replace(scenario(),simulation_only=False)
    with pytest.raises(ValueError):
        replace(scenario(),source_invoice_sha256="bad")
    with pytest.raises(ValueError,match="payee"):
        request(1,"PAY_AFFILIATE")


def test_cross_customer_store_rejected_and_does_not_mutate(tmp_path):
    s=SettlementStore(tmp_path/"scope.sqlite3",buyer_id="OTHER",business_unit="SYN-UNIT")
    before=s.report_snapshot_json()
    with pytest.raises(ValueError,match="scope"):
        evaluate(store=s)
    assert s.report_snapshot_json()==before


def populate_store(tmp_path, *, amount=10000, disqualified=False, no_alloc=False):
    c=scenario(claim_cents=amount)
    s=SettlementStore(tmp_path/"scoped.sqlite3",
        buyer_id=c.buyer_id,business_unit=c.business_unit)
    s.create_claim(RecoveryClaim(
        c.claim_id,c.case_id,c.payer_id,c.payee_id,c.currency,
        c.disputed_cents,c.issued_at,c.source_finding_sha256,
        disqualified,
    ))
    s.ingest_event(SettlementEventRecord(
        "SYN-CREDIT-1",c.case_id,c.payer_id,c.payee_id,c.currency,
        6000,"2026-09-02T12:00:00Z",H("settlement-1"),"SYNTHETIC_CREDIT_MEMO",
    ))
    if not no_alloc:
        s.review_allocate(allocation_id="SYN-ALLOC-1",claim_id=c.claim_id,
                          event_id="SYN-CREDIT-1",amount_cents=6000,
                          created_at="2026-09-03T12:00:00Z")
    return c,s


def test_partial_credit_in_existing_store_does_not_create_bank_truth(tmp_path):
    c,s=populate_store(tmp_path)
    before=s.report_snapshot_json()
    out=evaluate(c,store=s)
    assert out.state=="SOURCE_DECLARED_PARTIALLY_SETTLED_UNVERIFIED"
    assert out.settlement.source_declared_allocated_cents==6000
    assert out.settlement.source_declared_reversed_cents==0
    assert out.settlement.source_declared_net_cents==6000
    assert out.settlement.unallocated_claim_residual_cents==4000
    assert out.settlement.source_authenticated_payment_cents==0
    assert out.settlement.real_recovered_cash_cents==0
    assert before==s.report_snapshot_json()
    assert_safe(out)


def test_unapplied_return_blocks_recovery_and_stale_snapshot(tmp_path):
    c,s=populate_store(tmp_path)
    baseline=evaluate(c,store=s)
    frozen=replace(c,expected_settlement_snapshot_sha256=baseline.settlement.snapshot_sha256)
    s.ingest_counter(CounterEventRecord(
        "SYN-RETURN-1","SYN-CREDIT-1","USD",2000,
        "2026-09-04T12:00:00Z",H("return-1"),"SYNTHETIC_RETURN",
    ))
    held=evaluate(c,store=s)
    assert held.state=="RETURN_REVERSAL_REVIEW_HOLD"
    assert held.settlement.outstanding_return_cents==2000
    assert held.settlement.source_declared_net_cents==6000
    with pytest.raises(ValueError,match="snapshot changed"):
        evaluate(frozen,store=s)
    assert_safe(held)
    s.auto_apply_counter("SYN-RETURN-1",created_at="2026-09-05T12:00:00Z")
    after=evaluate(c,store=s)
    assert after.settlement.source_declared_net_cents==4000
    assert after.settlement.source_declared_reversed_cents==2000
    assert after.settlement.outstanding_return_cents==0
    assert_safe(after)


def test_full_account_credit_is_not_bank_verified_even_when_net_equals_claim(tmp_path):
    c,s=populate_store(tmp_path, amount=6000)
    out=evaluate(c,store=s)
    assert out.state=="SOURCE_DECLARED_FULLY_SETTLED_UNVERIFIED"
    assert out.settlement.source_declared_net_cents==6000
    assert out.independently_verified_cash_cents==0
    assert out.customer_fee_billable_cents==0
    assert_safe(out)


def test_recovery_fee_disqualification_stays_outside_client_fee(tmp_path):
    c,s=populate_store(tmp_path,disqualified=True)
    out=evaluate(c,store=s,assumptions=FeasibilityAssumptions(
        modeled_collection_probability_bps=8000,modeled_fee_rate_bps=3000))
    assert out.settlement.source_declared_candidate_fee_cents==0
    assert out.customer_fee_billable_cents==0
    # No contingency forecast from incumbent/fee-disqualified claims.
    assert out.feasibility.modeled_contingency_fee_cents==0
    assert out.feasibility.modeled_net_fee_after_cost_cents==0
    assert_safe(out)


def test_unrelated_finding_hash_is_rejected_even_when_case_amount_matches(tmp_path):
    c,s=populate_store(tmp_path)
    forged=replace(c,source_finding_sha256=H("different-finding"))
    with pytest.raises(ValueError,match="frozen recovery scenario"):
        evaluate(forged,store=s)


def test_claim_issuance_time_is_bound_to_snapshot_claim(tmp_path):
    c,s=populate_store(tmp_path)
    forged=replace(c,issued_at="2026-09-01T11:00:00Z")
    with pytest.raises(ValueError,match="frozen recovery scenario"):
        evaluate(forged,store=s)


def test_unknown_customer_payment_or_evidence_does_not_write_to_db(tmp_path):
    c,s=populate_store(tmp_path)
    initial=s.report_snapshot_json()
    out=evaluate(c,store=s,requests=(
        request(1,"PAY_AFFILIATE",payee="FAKE-AFFILIATE"),
        request(2,"IMMEDIATE_SETTLEMENT"),
        request(3,"DELETE_ALL_EVIDENCE"),
    ),events=(event(1,"CARRIER_DENIAL"),))
    assert out.state=="DISPUTED_EVIDENCE_HOLD"
    assert all(x.no_external_action for x in out.customer_request_triage)
    assert s.report_snapshot_json()==initial
    assert_safe(out)


def test_120_adversarial_combinations_and_source_counts_without_external_actions():
    family=[
        ("CARRIER_DISPUTE","GUARANTEED_RECOVERY"),
        ("CARRIER_DENIAL","IMMEDIATE_SETTLEMENT"),
        ("INSOLVENCY_NOTICE","PAY_AFFILIATE"),
        ("CARRIER_OUT_OF_BUSINESS","DELETE_ALL_EVIDENCE"),
        ("CLAIM_TIME_BAR_CONCERN","RETENTION_EXCEPTION"),
        ("CUSTOMER_DISPUTE","FEE_WAIVER"),
        ("CUSTOMER_WITHDRAWAL","WITHDRAW_CASE"),
        ("DELAY_NOTICE","CUSTOMER_DATA_EXPORT"),
        ("PAYMENT_REVERSAL_NOTICE","INVOICE_CORRECTION"),
        ("PARTIAL_OFFER","SANITIZED_READ_ONLY_SUMMARY"),
        ("ACCOUNT_CREDIT_OFFER","CHANGE_CUSTOMER_SCOPE"),
        ("CARRIER_EVIDENCE_REQUEST","CROSS_TENANT_MERGE"),
    ]
    receipts=set()
    for index in range(120):
        kind, ask=family[index % len(family)]
        c=scenario(index+100,claim_cents=10000+index)
        e=event(index+1,kind,amount=(3000+index if kind.endswith("_OFFER") else None))
        r=request(index+1,ask,payee="FAKE-AFFILIATE" if ask=="PAY_AFFILIATE" else None)
        assumptions=FeasibilityAssumptions(
            modeled_collection_probability_bps=1000+(index%10)*900,
            modeled_fee_rate_bps=3000,
            labor_hours=index%5+1, cost_per_hour_cents=3000,
            other_delivery_cost_cents=index*10,
            expected_delay_days=index%365,
            target_response_days=30,
        )
        out=evaluate(c,events=(e,),requests=(r,),assumptions=assumptions,
                     as_of="2026-12-31")
        assert out.state!="SOURCE_DECLARED_FULLY_SETTLED_UNVERIFIED"
        assert out.events_seen==out.requests_seen==1
        assert_safe(out)
        receipts.add(out.report_hash)
    assert len(receipts)==120


def test_parallel_read_only_evaluation_deterministic():
    c=scenario()
    e=event(1,"CARRIER_DISPUTE")
    def go(_): return evaluate(c,events=(e,)).report_hash
    with ThreadPoolExecutor(max_workers=8) as pool:
        hashes=list(pool.map(go,range(20)))
    assert len(set(hashes))==1
