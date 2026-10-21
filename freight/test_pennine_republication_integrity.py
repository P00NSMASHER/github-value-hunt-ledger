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


@pytest.mark.parametrize("original,replacement", [
    ("29,601.74", "29,601.75"),
    ("06/07/2026", "07/07/2026"),
])
def test_public_census_holds_reused_invoice_with_changed_economics(
    original, replacement,
):
    conflicting = _original().replace(original.encode(), replacement.encode())
    with pytest.raises(ValueError, match="INVOICE_ECONOMIC_IDENTITY_CONFLICT") as exc:
        _replay(_original(), conflicting)
    assert "000123" not in str(exc.value)  # no supplier / invoice in errors


@pytest.mark.parametrize("original,replacement", [
    ("29,601.74", "29,601.75"),
    ("06/07/2026", "07/07/2026"),
])
def test_original_document_lab_holds_reused_invoice_with_changed_economics(
    original, replacement,
):
    conflicting = _original().replace(original.encode(), replacement.encode())
    with patch.dict(lab.PENNINE, {
        "2026-07": "https://example.invalid/one",
        "2026-08": "https://example.invalid/two",
    }, clear=True), patch.object(
        lab, "fetch_public", side_effect=[_original(), conflicting],
    ), patch.object(lab, "require_frozen_source", return_value="synthetic-only"):
        with pytest.raises(ValueError, match="INVOICE_ECONOMIC_IDENTITY_CONFLICT"):
            lab.benchmark_pennine()


@pytest.mark.parametrize("id_mutation", [
    b"000\x1f123",  # delimiter collision in laboratory's old join-based keys
    b"00\xe2\x80\x8d0123",  # invisible Unicode format control
    "Cafe\u0301".encode("utf-8"),  # Unicode canonical decomposition alias
])
def test_both_pennine_parsers_reject_ambiguous_invoice_id(id_mutation):
    corrupt = _original().replace(b"000123", id_mutation)
    with pytest.raises(ValueError, match="NONCANONICAL_PUBLIC_SOURCE_IDENTITY"):
        census.decode_month(corrupt, "2026-08")
    with pytest.raises(ValueError, match="NONCANONICAL_PUBLIC_SOURCE_IDENTITY"):
        lab.parse_pennine_csv(corrupt, "2026-08")


def test_different_suppliers_can_have_the_same_invoice_number_and_amount_changes():
    baseline = _original()
    second = baseline.replace(b"35,000123", b"36,000123").replace(
        b"29,601.74", b"29,601.75",
    )
    result = _replay(baseline, second)
    assert result["unique_economic_invoices"] == 2
    assert result["matched_original_invoices"] == 2
    assert result["republication_payment_annotations_consistent"] is True


@pytest.mark.parametrize("raw_id", [
    b"000123\x1f",  # Python strip() would silently erase a trailing delimiter
    b"\x1f000123",  # Python strip() would silently erase a leading delimiter
])
def test_both_parsers_reject_control_char_before_implicit_stripping(raw_id):
    corrupt = _original().replace(b"000123", raw_id)
    with pytest.raises(ValueError, match="NONCANONICAL_PUBLIC_SOURCE_IDENTITY"):
        census.decode_month(corrupt, "2026-08")
    with pytest.raises(ValueError, match="NONCANONICAL_PUBLIC_SOURCE_IDENTITY"):
        lab.parse_pennine_csv(corrupt, "2026-08")


def test_both_parsers_reject_duplicate_required_csv_header():
    corrupt = _original().replace(b"Invoice Number,Invoice Date",
                                  b"Invoice Number,Invoice Number,Invoice Date")
    with pytest.raises(ValueError, match="AMBIGUOUS_PUBLIC_SOURCE_HEADERS"):
        census.decode_month(corrupt, "2026-08")
    with pytest.raises(ValueError, match="AMBIGUOUS_PUBLIC_SOURCE_HEADERS"):
        lab.parse_pennine_csv(corrupt, "2026-08")


def test_pennine_dual_source_parser_parity_preserves_every_record():
    original = _original()
    lab_rows = lab.parse_pennine_csv(original, "2026-08")
    census_rows = census.decode_month(original, "2026-08")
    lab.verify_public_csv_adapter_parity(lab_rows, census_rows)


def test_pennine_dual_source_parser_parity_refuses_one_penny_drift():
    original = _original()
    lab_rows = lab.parse_pennine_csv(original, "2026-08")
    census_rows = [dict(row) for row in census.decode_month(original, "2026-08")]
    census_rows[0]["invoice amount minor"] += 1
    with pytest.raises(ValueError, match="PUBLIC_CSV_ADAPTER_PARITY_MISMATCH") as error:
        lab.verify_public_csv_adapter_parity(lab_rows, census_rows)
    assert "000123" not in str(error.value)


def test_pennine_dual_source_parser_parity_refuses_row_drop():
    original = _original()
    lab_rows = lab.parse_pennine_csv(original, "2026-08")
    with pytest.raises(ValueError, match="PUBLIC_CSV_ADAPTER_PARITY_MISMATCH"):
        lab.verify_public_csv_adapter_parity(lab_rows, [])

def test_actual_lab_benchmark_aborts_if_independent_parser_diverges():
    source = _original()
    parsed = [dict(x) for x in census.decode_month(source, "2026-08")]
    parsed[0]["invoice amount minor"] += 1
    with patch.dict(lab.PENNINE, {
        "2026-08": "https://example.invalid/synthetic"
    }, clear=True), patch.object(lab, "fetch_public", return_value=source), \
         patch.object(lab, "require_frozen_source", return_value="synthetic-only"), \
         patch.object(census, "decode_month", return_value=tuple(parsed)):
        with pytest.raises(ValueError, match="PUBLIC_CSV_ADAPTER_PARITY_MISMATCH"):
            lab.benchmark_pennine()


def test_adapter_parity_respects_duplicate_multiplicity():
    source = _original()
    lab_rows = lab.parse_pennine_csv(source, "2026-08")
    published = census.decode_month(source, "2026-08")
    with pytest.raises(ValueError, match="PUBLIC_CSV_ADAPTER_PARITY_MISMATCH"):
        lab.verify_public_csv_adapter_parity(lab_rows, published + published)

def test_public_source_registries_have_identical_pins_and_urls():
    assert set(lab.PENNINE) == set(lab.FROZEN_PENNINE_SHA256) == set(census.SOURCES)
    for month, (route, digest, expected_rows) in census.SOURCES.items():
        assert lab.PENNINE[month] == census.ROOT + "/download_file/" + route
        assert lab.FROZEN_PENNINE_SHA256[month] == digest
        assert type(expected_rows) is int and expected_rows > 0


@pytest.mark.parametrize("broken_ids", [
    b"35,,06/07/2026,\x2229,601.74\x22,,05/08/2026,GBP,Fully paid",
    b"35,,06/07/2026,\x2229,601.74\x22,,05/08/2026,GBP,",
])
def test_post_header_accounting_row_missing_both_identities_fails_closed(
    broken_ids,
):
    """A published nonblank row cannot silently vanish from the denominator."""
    original = _original()
    changed = original + broken_ids + b"\n"
    assert changed != original
    with pytest.raises(ValueError, match="MISSING_PUBLIC_INVOICE_AND_PAYMENT_ID"):
        census.decode_month(changed, "2026-08")
    with pytest.raises(ValueError, match="MISSING_PUBLIC_INVOICE_AND_PAYMENT_ID"):
        lab.parse_pennine_csv(changed, "2026-08")


def test_blank_csv_separator_after_header_is_not_a_dropped_invoice():
    raw = _original() + b"\n"
    assert len(census.decode_month(raw, "2026-08")) == 1
    assert len(lab.parse_pennine_csv(raw, "2026-08")) == 1
