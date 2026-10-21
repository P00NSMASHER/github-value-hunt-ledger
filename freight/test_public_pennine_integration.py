"""Original Pennine CSV contractual controls; these do not prove bank clearing."""
from copy import deepcopy

import pytest

from freight.public_pennine_integration import (
    _cents, _date, _anon, SOURCES, decode_month,
    read_pinned_month, assert_public_census_result,
)


def _csv() -> bytes:
    return (
        "Public spend disclosure\n"
        "Business Unit Name,Supplier Type,Supplier,Supplier Number,Site,"
        "Remit-to Bank Account,Payment Document,Payment Method,Payment Date,"
        "Payment Number,Payment Currency,Invoice Number,Invoice Date,"
        "Invoice Description,Payment Status Name,Invoice Amount\n"
        'BU,Other,Example,35,ZIP,REMIT,BACS,EFT,05/08/2026,5174602,GBP,000123,06/07/2026,,Fully paid,"29,601.74"\n'
    ).encode("utf-8")


def test_real_publisher_header_and_cents_exact():
    rows = decode_month(_csv(), "2026-08")
    assert len(rows) == 1
    assert rows[0]["supplier number"] == "35"
    assert rows[0]["invoice number"] == "000123"
    assert rows[0]["invoice date"] == "2026-07-06"
    assert rows[0]["payment date"] == "2026-08-05"
    assert rows[0]["invoice amount minor"] == 2960174
    assert _cents("0.01") == 1
    assert _cents("29,601.74") == 2960174
    assert _date("05/08/2026") == "2026-08-05"
    assert _anon(("test",)) == _anon(("test",))
    assert _anon(("test",)) != _anon(("test changed",))


@pytest.mark.parametrize("bad", ["", "1,23.00", "1.234", "NaN", "1e3", "£1.00"])
def test_accounting_money_input_fail_closed(bad):
    with pytest.raises(ValueError, match="malformed"):
        _cents(bad)


def test_missing_month_and_unauthorized_source_fails_closed():
    with pytest.raises(ValueError, match="unapproved"):
        read_pinned_month("2025-01")
    with pytest.raises(ValueError, match="unapproved"):
        decode_month(_csv(), "2025-01")
    with pytest.raises(UnicodeDecodeError):
        decode_month(b"\xff", "2026-08")
    assert len(SOURCES) == 5


def test_incomplete_csv_source_rows_fail_closed():
    with pytest.raises(ValueError, match="truncated"):
        decode_month(
            _csv() + b"BUYER,OTHER\n",
            "2026-08",
        )
    malformed = _csv().replace(b"Fully paid", b"Fully paid").replace(
        b"29,601.74", b"X", 1
    )
    with pytest.raises(ValueError, match="malformed"):
        decode_month(malformed, "2026-08")


def test_result_integrity_cannot_forge_success():
    result = {
        "source_months": 5,
        "disclosed_rows": 314,
        "unique_economic_invoices": 273,
        "repeated_disclosures_not_duplicate_payments": 41,
        "republication_payment_annotations_consistent": True,
        "exact_invoiced_source_minor": 7423667742,
        "exact_grouped_source_minor": 7423667742,
        "matched_original_invoices": 273,
        "unmatched_original_invoices": 0,
        "mismatched_source_references": 0,
        "independently_proven_bank_settlements": 0,
        "realized_recovery_minor": 0,
        "publication_claim_approved": False,
        "actual_freight_detection_accuracy": None,
    }
    assert_public_census_result(result)
    for field, tampered in [
        ("matched_original_invoices", 272),
        ("republication_payment_annotations_consistent", False),
        ("republication_payment_annotations_consistent", 1),
        ("independently_proven_bank_settlements", 273),
        ("realized_recovery_minor", 1),
        ("actual_freight_detection_accuracy", 1.0),
    ]:
        changed = dict(result)
        changed[field] = tampered
        with pytest.raises(ValueError):
            assert_public_census_result(changed)
