"""R1 invariants: legacy hash safety, real-like signed invoices, bank/cash proof."""
from dataclasses import replace
from random import Random

import pytest

from freight.canonical_schema import (
    ChargeLine, InvoiceAdjustment, build_record, record_payload, verify_record,
)
from freight.enterprise_adapters import canonical_record_from_api
from freight.financial_integrity import (
    FinancialMovement, financial_claim_gate, replay_financial_movements,
)
from freight.rate_authority import AuthorityBook
from freight.rating_engine import REVIEW_REQUIRED, rate_record
from freight.scoped_reconciliation import ScopedTxn, reconcile_scoped
from freight.test_phase0_recoveryos import ltl_authority, ltl_record
from recoveryworks.reconciliation_kernel import ReconTxn

PDF_SHA = "a" * 64
BANK_SHA = "b" * 64
COURT_SHA = "c" * 64


def adjusted(amount=28061):
    record = ltl_record()
    return build_record(
        buyer_id=record.buyer_id, business_unit=record.business_unit,
        invoice_id=record.invoice_id, invoice_date=record.invoice_date,
        customer_id=record.customer_id, currency=record.currency,
        shipment=record.shipment,
        charges=record.charges, sources=record.sources,
        adjustments=(InvoiceAdjustment("original-D1", "DISCOUNT", amount, PDF_SHA),),
    )


def movement(id_, kind, amount, verified=False, target=None, *,
             source=BANK_SHA, record=None):
    record = record or ltl_record()
    return FinancialMovement(
        id_, kind, amount, "2026-10-03", source,
        "BANK_CLEARED" if verified else "CUSTOMER_STATEMENT",
        verified, target, record.record_hash,
    )


def test_legacy_v1_empty_adjustments_keep_exact_canonical_hash_and_payload():
    original = ltl_record()
    same = build_record(
        buyer_id=original.buyer_id, business_unit=original.business_unit,
        invoice_id=original.invoice_id, invoice_date=original.invoice_date,
        customer_id=original.customer_id, currency=original.currency,
        shipment=original.shipment, charges=original.charges,
        sources=original.sources, adjustments=(),
    )
    assert same.record_hash == original.record_hash
    assert original.schema_version == same.schema_version == 1
    assert original.adjustments == ()
    assert "adjustments" not in record_payload(original)
    verify_record(original)


def test_original_discount_is_exact_and_v2_hash_bound():
    base = ltl_record()
    record = adjusted(2806)
    assert record.schema_version == 2
    assert record.gross_charge_cents == 18700
    assert record.adjustment_total_cents == 2806
    assert record.billed_total_cents == 15894
    assert record.record_hash != base.record_hash
    assert len(record_payload(record)["adjustments"]) == 1
    verify_record(record)
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_record(replace(record, adjustments=()))
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_record(replace(record, schema_version=1))


def test_original_globaltranz_sample_exact_negative_discount_in_ledger():
    original = ltl_record()
    r = build_record(
        buyer_id=original.buyer_id, business_unit=original.business_unit,
        invoice_id="30794056", invoice_date=original.invoice_date,
        customer_id=original.customer_id, currency="USD",
        shipment=original.shipment,
        charges=(ChargeLine("freight", "LINEHAUL", 54278),
                 ChargeLine("fuel", "FUEL", 7891)),
        adjustments=(InvoiceAdjustment("discount", "DISCOUNT", 28061, PDF_SHA),),
        sources=original.sources,
    )
    assert r.billed_total_cents == 34108
    assert replay_financial_movements(r, ()).original_invoice_net_cents == 34108


@pytest.mark.parametrize("mod,expression", [
    (lambda a: [replace(a[0], source_sha256="b"*64)], "source"),
    (lambda a: [replace(a[0], applies_to_charge_id="MISSING")], "charge_id"),
    (lambda a: [a[0], a[0]], "duplicate"),
    (lambda a: [replace(a[0], amount_cents=18701)], "exceed"),
])
def test_original_signed_adjustment_invalid_states_fail_closed(mod, expression):
    base = adjusted(100)
    with pytest.raises(ValueError, match=expression):
        build_record(
            buyer_id=base.buyer_id, business_unit=base.business_unit,
            invoice_id=base.invoice_id, invoice_date=base.invoice_date,
            customer_id=base.customer_id, currency=base.currency,
            shipment=base.shipment, charges=base.charges,
            sources=base.sources, adjustments=mod(base.adjustments),
        )


def test_arbitrary_negative_freight_charge_remains_illegal():
    with pytest.raises(ValueError, match="billed_cents"):
        ChargeLine("bad", "DISCOUNT", -10)
    with pytest.raises(ValueError, match="adjustment kind"):
        InvoiceAdjustment("bad", "PAYMENT", 100, PDF_SHA)
    with pytest.raises(ValueError, match="amount_cents"):
        InvoiceAdjustment("bad", "DISCOUNT", -100, PDF_SHA)


def test_api_accepts_typed_adjustments_and_rejects_untyped_negative_lines():
    original = ltl_record()
    payload = {
        "buyer_id": original.buyer_id, "business_unit": original.business_unit,
        "invoice_id": original.invoice_id, "invoice_date": original.invoice_date,
        "customer_id": original.customer_id, "currency": original.currency,
        "shipment": {
            "shipment_id": original.shipment.shipment_id,
            "carrier_id": original.shipment.carrier_id,
            "mode": original.shipment.mode,
            "service_date": original.shipment.service_date,
            "origin_postal": original.shipment.origin_postal,
            "destination_postal": original.shipment.destination_postal,
            "actual_weight_grams": original.shipment.actual_weight_grams,
            "package_count": original.shipment.package_count,
            "freight_class": original.shipment.freight_class,
        },
        "charges": [
            {"charge_id": x.charge_id, "charge_code": x.charge_code,
             "billed_cents": x.billed_cents} for x in original.charges
        ],
        "sources": [{
            "source_id": s.source_id, "kind": s.kind,
            "sha256": s.sha256, "observed_at": s.observed_at,
            "transport": s.transport, "filename": s.filename,
        } for s in original.sources],
        "adjustments": [{
            "adjustment_id": "D1", "kind": "DISCOUNT",
            "amount_cents": 250, "source_sha256": PDF_SHA,
        }],
    }
    actual = canonical_record_from_api(payload)
    assert actual.schema_version == 2
    assert actual.billed_total_cents == 18450
    payload["charges"][0]["billed_cents"] = -100
    with pytest.raises(ValueError, match="billed_cents"):
        canonical_record_from_api(payload)


def test_cash_credit_and_reversal_conservation_without_invented_refunds():
    r = adjusted(100)
    cash = movement("P1", "PAYMENT", 10000, True, record=r)
    credit = FinancialMovement(
        "C1", "CREDIT_APPLIED", 1200, "2026-10-03", COURT_SHA,
        "CARRIER_CREDIT", True, None, r.record_hash)
    refund = movement("R1", "REFUND", 300, True, record=r)
    before = replay_financial_movements(r, (cash, credit, refund))
    assert before.declared_net_cash_cents == 9700
    assert before.verified_net_cash_cents == 0
    assert before.source_attested_net_cash_cents == 9700
    assert before.status == 'REVIEW_REQUIRED'
    assert 'INDEPENDENT_SETTLEMENT_AUTHENTICATION_NOT_IMPLEMENTED' in before.blockers
    assert before.declared_net_postinvoice_credits_cents == 1200
    assert before.remaining_balance_cents == r.billed_total_cents - 10900
    reverse = movement("REVP", "PAYMENT_REVERSAL", 10000, True, "P1", record=r)
    after = replay_financial_movements(r, (cash, credit, refund, reverse))
    assert after.verified_net_cash_cents == 0
    assert after.source_attested_net_cash_cents == -300
    assert after.declared_net_postinvoice_credits_cents == 1200
    assert after.remaining_balance_cents == r.billed_total_cents - 900
    assert before.receipt_hash != after.receipt_hash


def test_financial_ledger_guards_duplicate_reverse_and_unverified_original():
    record = ltl_record()
    pay = movement("P", "PAYMENT", 1000, True)
    rev = movement("R", "PAYMENT_REVERSAL", 1000, True, "P")
    with pytest.raises(ValueError, match="duplicate"):
        replay_financial_movements(record, (pay, pay))
    with pytest.raises(ValueError, match="already been reversed"):
        replay_financial_movements(record, (pay, rev, movement("R2", "PAYMENT_REVERSAL", 1000, True, "P")))
    with pytest.raises(ValueError, match="earlier"):
        replay_financial_movements(record, (rev,))
    with pytest.raises(ValueError, match="invoice cannot independently prove"):
        replay_financial_movements(
            record, (movement("self", "PAYMENT", 1000, True, source=PDF_SHA),))
    with pytest.raises(ValueError, match="independently verified"):
        FinancialMovement("P", "PAYMENT", 1000, "2026-10-03", PDF_SHA,
                          "CUSTOMER_STATEMENT", True, None, record.record_hash)


def test_financial_release_review_and_no_cash_recovery_without_refund_proof():
    record = ltl_record()
    rating = rate_record(record, AuthorityBook([ltl_authority()]))
    declared = replay_financial_movements(record, (movement("P", "PAYMENT", 18700),))
    review = financial_claim_gate(
        record, rating, declared,
        independent_adjudication_sha256=COURT_SHA,
        human_release_approved=True)
    assert review.validated_discrepancy_cents == 0
    assert review.realized_recovery_cents == 0
    assert "NO_INDEPENDENT_BANK_CLEARED_PAYMENT" in review.blockers
    cleared = replay_financial_movements(record, (movement("P", "PAYMENT", 18700, True),))
    approved = financial_claim_gate(
        record, rating, cleared, independent_adjudication_sha256=COURT_SHA,
        human_release_approved=True)
    assert approved.rated_discrepancy_cents == 2700
    assert approved.validated_discrepancy_cents == 0
    assert "GOVERNED_BUYER_AUDIT_ACCEPTANCE_NOT_COMPLETED" in approved.blockers
    assert 'NO_INDEPENDENT_BANK_CLEARED_PAYMENT' in approved.blockers
    assert cleared.verified_net_cash_cents == 0
    assert cleared.source_attested_net_cash_cents == 18700
    assert approved.realized_recovery_cents == 0
    held = financial_claim_gate(record, rating, cleared, human_release_approved=False)
    assert held.validated_discrepancy_cents == 0
    assert held.realized_recovery_cents == 0
    unverified = rate_record(record, AuthorityBook([ltl_authority(verified=False)]))
    assert unverified.status == REVIEW_REQUIRED
    assert financial_claim_gate(record, unverified, cleared).validated_discrepancy_cents == 0


def _scoped(identifier, amount, ref, origin="ORIGINAL_INVOICE", *,
            buyer="B1", vendor="V1", date="2026-07-01", currency="GBP"):
    return ScopedTxn(
        ReconTxn(identifier, amount, date, currency, ref),
        buyer_id=buyer, business_unit="BU", counterparty_id=vendor,
        origin=origin)


def test_reference_scoped_matching_for_real_pennine_distribution():
    sizes = [1] * 178 + [2] * 32 + [3] * 4 + [4] + [7] + [8]
    assert len(sizes) == 217 and sum(sizes) == 273
    invoices, counterpart = [], []
    n = 0
    for group, size in enumerate(sizes):
        ref = f"P{group:04d}"
        for offset in range(size):
            invoices.append(_scoped(f"I{n}", "100.00", ref))
            n += 1
        counterpart.append(_scoped(f"B{group}", f"{size*100}.00", ref, "CUSTOMER_DECLARATION"))
    result = reconcile_scoped(invoices, counterpart, date_window_days=0)
    assert (result.matched_internal, result.matched_counterparts) == (273, 217)
    assert result.unmatched_internal == result.unmatched_counterparts == 0
    assert result.mismatched_references == result.proven_cleared_payment_count == 0
    assert result.independent_payment_accuracy is None
    seed = Random(42)
    seed.shuffle(invoices)
    seed.shuffle(counterpart)
    shuffled = reconcile_scoped(invoices, counterpart, date_window_days=0)
    assert shuffled.result_hash == result.result_hash
    assert shuffled.matched_internal == 273


def test_money_proof_cannot_be_reused_for_another_invoice():
    original = ltl_record()
    valid = movement("B1", "PAYMENT", 1000, True, record=original)
    replay = replay_financial_movements(original, (valid,))
    assert replay.verified_net_cash_cents == 0
    assert replay.source_attested_net_cash_cents == 1000
    mismatch_invoice = build_record(
        buyer_id=original.buyer_id, business_unit=original.business_unit,
        invoice_id="a second invoice", invoice_date=original.invoice_date,
        customer_id=original.customer_id, currency=original.currency,
        shipment=original.shipment, charges=original.charges,
        sources=original.sources)
    with pytest.raises(ValueError, match="different invoice hash"):
        replay_financial_movements(mismatch_invoice, (valid,))
    with pytest.raises(ValueError, match="exact original invoice"):
        financial_claim_gate(
            mismatch_invoice,
            rate_record(mismatch_invoice, AuthorityBook(())),
            replay,
        )

def test_reference_scope_does_not_match_reused_ids_across_buyers_or_suppliers():
    inv = [_scoped("I1", "10.00", "ABC", buyer="B1", vendor="V1")]
    pay = [_scoped("S1", "10.00", "ABC", "BANK_CLEARED", buyer="B2", vendor="V1")]
    result = reconcile_scoped(inv, pay)
    assert result.matched_internal == 0
    assert result.unmatched_internal == 1
    assert result.unmatched_counterparts == 1
    assert result.independent_payment_accuracy is None


def test_scoped_kernel_corruption_and_bounded_review():
    invoices = [_scoped("I1", "12.00", "PAY-1"), _scoped("I2", "9.00", "PAY-1")]
    correct = _scoped("B1", "21.00", "PAY-1", "BANK_CLEARED")
    baseline = reconcile_scoped(invoices, [correct])
    assert baseline.matched_internal == 2
    assert baseline.bank_labeled_counterpart_matches == 1
    assert baseline.proven_cleared_payment_count == 0
    for corrupted in [
        replace(correct, txn=replace(correct.txn, amount="21.01")),
        replace(correct, txn=replace(correct.txn, reference="PAY-2")),
        replace(correct, txn=replace(correct.txn, currency="USD")),
    ]:
        report = reconcile_scoped(invoices, [corrupted])
        assert report.matched_internal == 0
    with pytest.raises(ValueError, match="duplicate transaction"):
        reconcile_scoped(invoices, [correct, correct])
    cap = reconcile_scoped(
        [_scoped(f"I{i}", "1.00", "BIG") for i in range(33)],
        [_scoped("B", "33.00", "BIG", "BANK_CLEARED")],
        group_size_limit=32)
    assert cap.bound_exceeded_groups == 1
    assert cap.matched_internal == 0
    assert cap.unmatched_internal == 33
