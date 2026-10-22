"""Priority 1 financial invariants: synthetic fixtures, no real bank/contract rights."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json

import pytest

from freight.canonical_schema import ChargeLine, InvoiceAdjustment, build_record, verify_record
from freight.financial_assurance import (
    SourceAttestation, FeeTerms, quote_contingent_fee, parse_major_exact,
    require_exact_cents, require_cent_currency, receipt_message, verify_source_attestation,
)
from freight.currency_reporting import (
    build_currency_settlement_report, assert_currency_report_current, render_currency_report,
)
from freight.payment_orchestration import (
    PaymentOrchestrator, prepare_payment_instruction, authorize_payment, verify_payment_snapshot,
)
from freight.settlement_store import (
    ALLOCATED, REVERSED, ALREADY_ALLOCATED, SettlementStore, RecoveryClaim,
    SettlementEventRecord, CounterEventRecord,
)
from freight.financial_integrity import replay_financial_movements
from freight.test_financial_integrity_r1 import adjusted, movement


def H(s):
    return sha256(s.encode()).hexdigest()


def attestation(subject, scope, purpose, key=b"synthetic-key-not-a-real-credential", issuer="TEST_ISSUER"):
    data = SourceAttestation(
        issuer_id=issuer, purpose=purpose, scope_hash=scope,
        subject_sha256=subject, issued_at="2026-10-22T12:00:00Z",
        mac_sha256="0"*64,
    )
    return replace(data, mac_sha256=hmac.new(key, receipt_message(data), "sha256").hexdigest())


def instruction():
    return prepare_payment_instruction(
        instruction_id="SYN-I", buyer_id="SYN-B", business_unit="SYN-U",
        payer_id="SYN-C", payee_id="SYN-BUYER", currency="USD",
        amount_cents=101, purpose="SYNTHETIC_TEST",
        finding_proof_hashes=(H("synthetic-finding"),), idempotency_key="SYN-K",
    )


def authority(i):
    return authorize_payment(i, authorized_by="SIMULATED_REVIEWER_ONLY",
                             reason="no real buyer approval",
                             authorized_at="2026-10-22T12:00:00Z")


def bound_scope(i):
    from freight.contracts import canonical_hash
    return canonical_hash({
        "buyer_id": i.buyer_id, "business_unit": i.business_unit,
        "payee_id": i.payee_id, "payer_id": i.payer_id,
    })


def store(tmp_path):
    return SettlementStore(tmp_path / "priority1.sqlite3",
                           buyer_id="SYN-B", business_unit="SYN-U")


def claim(cid, amt=10000, currency="USD", disq=False):
    return RecoveryClaim(cid, cid, "SYN-CARRIER", "SYN-BUYER",
                         currency, amt, "2026-09-01T00:00:00Z",
                         H("claim-"+cid), disq)


def event(eid, cid, amt=10000, currency="USD"):
    return SettlementEventRecord(eid, cid, "SYN-CARRIER", "SYN-BUYER",
                                 currency, amt, "2026-09-02T00:00:00Z",
                                 H("event-"+eid), "SYNTHETIC_DECLARATION")


def reversal(rid, eid, amt, currency="USD"):
    return CounterEventRecord(rid, eid, currency, amt,
                              "2026-09-04T00:00:00Z", H("reversal-"+rid),
                              "SYNTHETIC_RETURN")


@pytest.mark.parametrize("currency,value,minor", [
    ("USD", "12.34", 1234), ("EUR", "0.01", 1),
    ("GBP", "200", 20000), ("JPY", "103", 103),
    ("KWD", "12.345", 12345), ("USD", "0.00", 0),
])
def test_precise_currency_amounts_have_explicit_minor_units(currency, value, minor):
    money = parse_major_exact(value, currency)
    assert money.minor == minor and money.currency == currency


@pytest.mark.parametrize("value", [
    "1e3", "NaN", "Infinity", "12,34", "12.345", "１２.３４",
    "١٢.٣٤", "", "+1.00", " 1.00 ", "1,000.00",
])
def test_noncanonical_money_is_rejected(value):
    with pytest.raises(ValueError):
        parse_major_exact(value, "USD")


def test_exact_cents_rejects_boolean_float_overflow_and_negative():
    for bad in (True, 1.5, -1, 2**63):
        with pytest.raises(ValueError):
            require_exact_cents("amount", bad, positive=False)
    assert require_exact_cents("amount", 0) == 0
    with pytest.raises(ValueError):
        require_exact_cents("amount", 0, positive=True)


def test_cent_based_engine_rejects_zero_and_three_decimal_currencies():
    assert require_cent_currency("usd") == "USD"
    for c in ("JPY", "KWD", "ZZZ"):
        with pytest.raises(ValueError):
            require_cent_currency(c)
    with pytest.raises(ValueError):
        prepare_payment_instruction(
            instruction_id="SYN", buyer_id="B", business_unit="U",
            payer_id="P", payee_id="Q", currency="JPY", amount_cents=10,
            purpose="SYNTHETIC", finding_proof_hashes=(H("x"),),
            idempotency_key="key",
        )


def test_trusted_approval_is_fail_closed_without_attestation():
    i = instruction()
    p = PaymentOrchestrator(i, require_trusted_approval=True,
                            trusted_issuers={"TEST_ISSUER": b"synthetic-key-not-a-real-credential"})
    with pytest.raises(ValueError, match="attestation"):
        p.authorize(authority(i))
    assert p.authorization is None


def test_trusted_approval_binds_exact_scope_and_authorization():
    i=instruction()
    p=PaymentOrchestrator(i, require_trusted_approval=True,
                          trusted_issuers={"TEST_ISSUER": b"synthetic-key-not-a-real-credential"})
    signed=attestation(authority(i).authorization_hash, bound_scope(i), "APPROVAL")
    p.authorize(authority(i), attestation=signed)
    e=p.record_provider_event(state="SUBMITTED", provider="SYN",
                              provider_reference="R", amount_cents=101,
                              source_hash=H("submitted"),
                              occurred_at="2026-10-22T12:01:00Z")
    assert e.state=="SUBMITTED"
    with pytest.raises(ValueError):
        verify_source_attestation(
            signed, trusted_issuers={"TEST_ISSUER":b"synthetic-key-not-a-real-credential"},
            purpose="BANK_CLEARED", scope_hash=bound_scope(i),
            subject_sha256=authority(i).authorization_hash,
        )
    with pytest.raises(ValueError):
        verify_source_attestation(
            replace(signed, issued_at="2026-10-23T12:00:00Z"),
            trusted_issuers={"TEST_ISSUER":b"synthetic-key-not-a-real-credential"},
            purpose="APPROVAL", scope_hash=bound_scope(i),
            subject_sha256=authority(i).authorization_hash,
        )


def test_changed_recipient_and_unknown_issuer_cannot_pass_approval():
    i=instruction()
    signed=attestation(authority(i).authorization_hash, bound_scope(i), "APPROVAL")
    with pytest.raises(ValueError):
        PaymentOrchestrator(replace(i, payee_id="SYN-OTHER"),
                            require_trusted_approval=True)
    p=PaymentOrchestrator(i, require_trusted_approval=True,
                          trusted_issuers={"OTHER":b"key"})
    with pytest.raises(ValueError):
        p.authorize(authority(i), attestation=signed)


def test_duplicate_provider_receipt_is_idempotent_and_conflict_rejected():
    i=instruction()
    p=PaymentOrchestrator(i)
    p.authorize(authority(i))
    data=dict(state="SUBMITTED", provider="SYN",provider_reference="R",
              amount_cents=101,source_hash=H("src"),
              occurred_at="2026-10-22T12:01:00Z")
    first=p.record_provider_event(**data)
    assert p.record_provider_event(**data)==first
    assert len(p.events)==1
    with pytest.raises(ValueError, match="collision"):
        p.record_provider_event(**{**data,"source_hash":H("tampered")})
    assert len(p.events)==1


def test_fee_terms_are_estimates_not_billable_payment_authority():
    terms=FeeTerms(buyer_id="SYN-B",business_unit="SYN-U",currency="USD",
                   rate_bps=3000,cap_cents=2000,
                   signed_terms_sha256=H("not-an-actual-signed-contract"))
    q=quote_contingent_fee(terms,net_declared_cents=10000,
                           reversed_cents=1000,incumbent_cents=1000,
                           disputed_cents=1000)
    assert q.eligible_cents==7000 and q.estimated_fee_cents==2000
    assert q.billable_cents==0 and "NO_AUTHENTICATED_CUSTOMER_SETTLEMENT" in q.blockers
    signed=attestation(terms.terms_hash,H("SYN-B|SYN-U"),"FEE_TERMS")
    validated=quote_contingent_fee(
        terms,net_declared_cents=10000,reversed_cents=1000,
        incumbent_cents=1000,disputed_cents=1000,
        terms_attestation=signed,
        trusted_issuers={"TEST_ISSUER":b"synthetic-key-not-a-real-credential"},
    )
    assert validated.estimated_fee_cents==2000 and validated.billable_cents==0


def test_fee_terms_negative_exclusions_or_unsigned_terms_cannot_bill():
    terms=FeeTerms(buyer_id="SYN-B",business_unit="SYN-U",currency="USD",
                   rate_bps=3000,cap_cents=1000,
                   signed_terms_sha256=H("synthetic"))
    for options in (
        {"net_declared_cents":100,"reversed_cents":101},
        {"net_declared_cents":100,"disputed_cents":101},
        {"net_declared_cents":100,"incumbent_cents":101},
    ):
        with pytest.raises(ValueError):
            quote_contingent_fee(terms, **options)
    no_fee=quote_contingent_fee(terms, net_declared_cents=100, disqualified=True)
    assert no_fee.eligible_cents==0 and no_fee.billable_cents==0


def test_settlement_currency_reporting_is_separate_and_reversal_aware(tmp_path):
    s=store(tmp_path)
    for c,amt,ccy in (("usd",10000,"USD"),("eur",12345,"EUR"),("gbp",3000,"GBP")):
        s.create_claim(claim(c,amt,ccy))
        s.ingest_event(event(c+"-e",c,amt,ccy))
        assert s.auto_allocate(c+"-e",created_at="2026-09-03T00:00:00Z").status==ALLOCATED
    initial=build_currency_settlement_report(s)
    assert [(x.currency,x.declared_net_allocated_cents)
            for x in initial.by_currency]==[("EUR",12345),("GBP",3000),("USD",10000)]
    assert initial.external_settlement_verified is False
    assert initial.single_aggregated_total_cents is None
    assert "EUR 123.45" in render_currency_report(initial)
    assert "USD 100.00" in render_currency_report(initial)
    assert_currency_report_current(initial,s)
    s.ingest_counter(reversal("usd-r","usd-e",2500))
    assert s.auto_apply_counter("usd-r",created_at="2026-09-05T00:00:00Z").status==REVERSED
    with pytest.raises(ValueError,match="changed"):
        assert_currency_report_current(initial,s)
    latest=build_currency_settlement_report(s)
    assert next(x for x in latest.by_currency if x.currency=="USD").declared_net_allocated_cents==7500
    assert latest.report_hash!=initial.report_hash


def test_partial_settlement_is_conserved_under_simultaneous_allocation(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("partial",10000))
    s.ingest_event(event("p1","partial",4000))
    s.ingest_event(event("p2","partial",6000))
    def run(i):
        return s.review_allocate(allocation_id="synthetic-a"+str(i),
                                 claim_id="partial",event_id="p1" if i==0 else "p2",
                                 amount_cents=4000 if i==0 else 6000,
                                 created_at="2026-09-03T00:00:00Z")
    with ThreadPoolExecutor(max_workers=2) as pool:
        outputs=list(pool.map(run,(0,1)))
    assert outputs==["ALLOCATED","ALLOCATED"]
    assert s.realized_cents()==10000 and s.claim_residual("partial")==0
    assert s.count("allocations")==2
    s.ingest_counter(reversal("r1","p1",4000))
    assert s.auto_apply_counter("r1",created_at="2026-09-05T00:00:00Z").status==REVERSED
    assert s.realized_cents()==6000 and s.claim_residual("partial")==4000


def test_concurrent_duplicate_provider_credit_reuses_one_row(tmp_path):
    s=store(tmp_path)
    s.create_claim(claim("single",100))
    s.ingest_event(event("one","single",100))
    def consume(_):
        return s.auto_allocate("one",created_at="2026-09-03T00:00:00Z").status
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses=list(pool.map(consume,range(8)))
    assert statuses.count(ALLOCATED)==1 and statuses.count(ALREADY_ALLOCATED)==7
    assert s.realized_cents()==100 and s.count("allocations")==1


def test_original_signed_discount_stays_separate_from_post_invoice_cash():
    record=adjusted(2806)
    assert record.billed_total_cents==15894
    verify_record(record)
    with pytest.raises(ValueError):
        verify_record(replace(record, adjustments=()))
    balance=replay_financial_movements(record,())
    assert balance.original_invoice_net_cents==15894
    assert balance.verified_net_cash_cents==0
    assert "INDEPENDENT_SETTLEMENT_AUTHENTICATION_NOT_IMPLEMENTED" in balance.blockers
