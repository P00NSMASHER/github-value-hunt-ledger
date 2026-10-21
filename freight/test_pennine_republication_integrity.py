"""Synthetic negative controls for public-source invoice republication.

No source rows, supplier identifiers, or payment references from actual records.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from freight import public_pennine_integration as census
from freight import real_document_lab as lab


def _original() -> bytes:
    return (
        "Publication heading\n"
        "Supplier Number,Invoice Number,Invoice Date,Invoice Amount,"
        "Payment Number,Payment Date,Payment Currency,Payment Status Name\n"
        '35,000123,06/07/2026,"29,601.74",5174602,05/08/2026,GBP,Fully paid\n'
    ).encode("utf-8")


def _replay(*months: bytes):
    with patch.dict(census.SOURCES, {
        "2026-07": ("synthetic/1", "a"*64, 1),
        "2026-08": ("synthetic/2", "b"*64, 1),
    }, clear=True), patch.object(census, "read_pinned_month", side_effect=months):
        return census.run_public_census_replay()


@pytest.mark.parametrize("original,replacement", [
    ("5174602", "5174603"),
    ("05/08/2026", "06/08/2026"),
    ("Fully paid", "Not paid"),
])
def test_public_census_refuses_contradictory_republication(original, replacement):
    tampered = _original().replace(original.encode(), replacement.encode())
    with pytest.raises(ValueError, match="REPUBLICATION_PAYMENT_ANNOTATION_CONFLICT"):
        _replay(_original(), tampered)


def test_repeated_identical_public_declaration_stays_one_invoice():
    result = _replay(_original(), _original())
    assert result["disclosed_rows"] == 2
    assert result["unique_economic_invoices"] == 1
    assert result["repeated_disclosures_not_duplicate_payments"] == 1
    assert result["matched_original_invoices"] == 1
    assert result["independently_proven_bank_settlements"] == 0
    assert result["republication_payment_annotations_consistent"] is True


@pytest.mark.parametrize("original,replacement", [
    ("5174602", "5174603"),
    ("05/08/2026", "06/08/2026"),
    ("Fully paid", "Not paid"),
])
def test_original_document_lab_refuses_contradictory_republication(original, replacement):
    tampered = _original().replace(original.encode(), replacement.encode())
    with patch.dict(lab.PENNINE, {
        "2026-07": "https://example.invalid/one",
        "2026-08": "https://example.invalid/two",
    }, clear=True), patch.object(lab, "fetch_public", side_effect=[_original(), tampered]), \
         patch.object(lab, "require_frozen_source", return_value="synthetic-only"):
        with pytest.raises(ValueError, match="REPUBLICATION_PAYMENT_ANNOTATION_CONFLICT"):
            lab.benchmark_pennine()


def test_payment_reference_scope_includes_supplier_identity():
    row = {
        "supplier number": "supplier-A",
        "payment number": "same-payment-123",
        "payment date": "2026-08-05",
        "payment currency": "GBP",
    }
    assert lab._payment_scope_key(row) == lab._payment_scope_key(dict(row))
    assert lab._payment_scope_key(row) != lab._payment_scope_key({
        **row, "supplier number": "supplier-B"
    })


def test_republication_status_case_and_whitespace_are_semantically_equal():
    normalized = _original().replace(b"Fully paid", b"  fully   PAID  ")
    result = _replay(_original(), normalized)
    assert result["unique_economic_invoices"] == 1
    assert result["republication_payment_annotations_consistent"] is True


def test_actual_kernel_keeps_equal_remittance_reference_but_distinct_suppliers_apart():
    lines = _original().decode("utf-8").splitlines()
    second = '36,000124,06/07/2026,"7,000.00",5174602,05/08/2026,GBP,Fully paid'
    two_suppliers = ("\n".join([lines[0], lines[1], lines[2], second]) + "\n").encode()
    with patch.dict(lab.PENNINE, {
        "2026-08": "https://example.invalid/synthetic"
    }, clear=True), patch.object(lab, "fetch_public", return_value=two_suppliers), \
         patch.object(lab, "require_frozen_source", return_value="synthetic-only"):
        report = lab.benchmark_pennine()
    assert report["unique_invoice_economic_identities"] == 2
    assert report["declared_payment_references"] == 2
    scoped = report["retally_source_reference_scoped_kernel_replay"]
    assert scoped["matched_invoices"] == 2
    assert scoped["matched_groups"] == 2
    assert scoped["cross_reference_false_joins"] == 0
    assert report["independent_bank_clearing_verified"] is False
    assert report["economic_false_positive_rate"] is None


def test_lab_truncated_csv_row_cannot_disappear_from_published_population():
    # Before the repair the lab silently dropped this nonblank truncated
    # invoice, making its measured source population incomplete.
    corrupt = _original() + b"36,000124\n"
    with pytest.raises(ValueError, match="TRUNCATED_PUBLIC_CSV_INVOICE_RECORD"):
        lab.parse_pennine_csv(corrupt, "2026-08")
    with pytest.raises(ValueError, match="truncated"):
        census.decode_month(corrupt, "2026-08")
