"""R4 property and performance checks; never use private billing data."""
from dataclasses import replace
from random import Random

import pytest

from freight.canonical_schema import ChargeLine, InvoiceAdjustment, build_record
from freight.reliability_dashboard import (
    acceptance_snapshot, html_dashboard,
    synthetic_population, run_deterministic_throughput,
)
from freight.scoped_reconciliation import reconcile_scoped
from freight.test_phase0_recoveryos import ltl_record


def _real_hold():
    return acceptance_snapshot(
        invoices_extracted=110, invoices_exact=110, pinned_source_files=7,
        accounting_invoice_population=273, accounting_matched=273,
        accounting_cross_scope_errors=0, freight_labeled=0, freight_unknown=110,
        precision=None,
        rights_approved=False, independent_review_approved=False,
        production_approved=False,
    )


def test_original_real_document_status_remains_hold():
    state = _real_hold()
    assert state.release_status == "RELEASE_HOLD"
    assert state.real_freight_precision is None
    assert state.independently_verified_cash_recovery_cents == 0
    assert state.distinct_invoice_disclosures == 273
    assert "REAL_FREIGHT_ACCURACY_UNPROVEN" in state.blockers
    assert "INDEPENDENT_RELEASE_REVIEW_MISSING" in state.blockers
    assert len(state.manifest_hash) == 64
    assert state == _real_hold()


def test_dashboard_aggregate_only_and_no_public_money_claim():
    doc = html_dashboard(_real_hold())
    assert "110" in doc and "273" in doc
    assert "RELEASE_HOLD" in doc
    assert "NOT ESTIMABLE" in doc
    assert "noindex,nofollow" in doc
    assert "recovered dollars: 0" not in doc
    for sensitive in ("30794056", "051894063", "GlobalTranz", "Pennine Care"):
        assert sensitive not in doc


@pytest.mark.parametrize("input_key,value", [
    ("invoices_exact", 111),
    ("accounting_matched", 274),
    ("accounting_cross_scope_errors", -1),
    ("freight_labeled", 1.0),
    ("precision", 1.5),
    ("production_approved", "yes"),
])
def test_invalid_release_signals_fail_closed(input_key, value):
    data = dict(
        invoices_extracted=110, invoices_exact=110, pinned_source_files=7,
        accounting_invoice_population=273, accounting_matched=273,
        accounting_cross_scope_errors=0, freight_labeled=0, freight_unknown=110,
        precision=None, rights_approved=False, independent_review_approved=False,
        production_approved=False)
    data[input_key] = value
    with pytest.raises(ValueError):
        acceptance_snapshot(**data)


def test_governance_cannot_self_approve_on_math_alone():
    snapshot = acceptance_snapshot(
        invoices_extracted=110, invoices_exact=110, pinned_source_files=7,
        accounting_invoice_population=273, accounting_matched=273,
        accounting_cross_scope_errors=0, freight_labeled=110, freight_unknown=0,
        precision=1.0, rights_approved=True,
        independent_review_approved=True, production_approved=True)
    assert snapshot.release_status == "RELEASE_HOLD"
    assert "EXISTING_FREIGHT_PILOT_ACCEPTANCE_REQUIRED" in snapshot.blockers


def test_source_control_273_with_larger_group_sizes_no_cross_reference():
    invoices, payments = synthetic_population(273)
    assert len(invoices) == 273
    first = reconcile_scoped(invoices, payments, group_size_limit=8)
    assert first.matched_internal == 273
    assert first.unmatched_internal == 0
    assert first.proven_cleared_payment_count == 0
    again = reconcile_scoped(
        list(reversed(invoices)), list(reversed(payments)),
        group_size_limit=8)
    assert first.result_hash == again.result_hash


@pytest.mark.parametrize("size", (1, 2, 11, 273, 1000))
def test_deterministic_engine_scales_and_is_order_invariant(size):
    report = run_deterministic_throughput(size)
    assert report.synthetic_invoice_count == report.matched_internal == size
    assert report.missing_internal == report.cross_reference_errors == 0
    assert report.deterministic_replay
    assert len(report.stable_result_sha256) == 64
    assert report.records_per_second > 0
    assert report.production_accuracy_claim is False


def test_exact_minor_unit_invoice_conservation_randomized():
    template = ltl_record()
    generator = Random(20261019)
    for _ in range(500):
        amounts = [generator.randint(1, 50_000) for _ in range(generator.randint(1, 6))]
        gross = sum(amounts)
        discount = generator.randint(0, gross)
        charges = tuple(ChargeLine(f"c{i}", "BILLED", amount)
                        for i, amount in enumerate(amounts))
        adjustments = (
            (InvoiceAdjustment("discount", "DISCOUNT", discount, "a" * 64),)
            if discount else ())
        record = build_record(
            buyer_id=template.buyer_id, business_unit=template.business_unit,
            invoice_id=template.invoice_id, invoice_date=template.invoice_date,
            customer_id=template.customer_id, currency=template.currency,
            shipment=template.shipment, charges=charges, sources=template.sources,
            adjustments=adjustments,
        )
        assert record.gross_charge_cents - record.adjustment_total_cents == record.billed_total_cents
        assert record.billed_total_cents == gross - discount
        assert record.billed_total_cents >= 0
