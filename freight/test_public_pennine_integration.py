"""Original Pennine CSV contractual controls; these do not prove bank clearing."""

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
    result = _complete_public_report_fixture()
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


def _complete_public_report_fixture():
    """Aggregate-only frozen census receipt, without publisher row identities."""
    return {
        "scope": "PUBLIC_SAME_SOURCE_ACCOUNTING_ONLY",
        "source_months": 5,
        "monthly_rows": {"2026-04": 67, "2026-05": 53, "2026-06": 50,
                         "2026-07": 103, "2026-08": 41},
        "disclosed_rows": 314,
        "unique_economic_invoices": 273,
        "repeated_disclosures_not_duplicate_payments": 41,
        "republication_payment_annotations_consistent": True,
        "supplier_reference_payment_declaration_groups": 217,
        "exact_invoiced_source_minor": 7423667742,
        "exact_grouped_source_minor": 7423667742,
        "matched_original_invoices": 273,
        "unmatched_original_invoices": 0,
        "mismatched_source_references": 0,
        "independently_proven_bank_settlements": 0,
        "actual_freight_detection_accuracy": None,
        "realized_recovery_minor": 0,
        "replay_hash": "c599d67a0887fa84aacb4bc91af28d3b72dfbadf6a552bb64ee76947d45ff213",
        "publication_claim_approved": False,
    }


@pytest.mark.parametrize("field,corrupt", [
    ("scope", "BANK_CLEARED_ACCOUNTING"),
    ("supplier_reference_payment_declaration_groups", 216),
    ("monthly_rows", {"2026-04": 66, "2026-05": 54, "2026-06": 50,
                      "2026-07": 103, "2026-08": 41}),
    ("monthly_rows", {"2026-04": 67, "2026-05": 53, "2026-06": 50,
                      "2026-07": 103, "2026-08": 41, "2026-09": 0}),
    ("replay_hash", None),
    ("replay_hash", "forged"),
    ("replay_hash", "A" * 64),
    ("publication_claim_approved", 0),
    ("unmatched_original_invoices", False),
    ("independently_proven_bank_settlements", False),
    ("matched_original_invoices", 273.0),
    ("source_months", 5.0),
])
def test_public_report_receipt_rejects_false_accounting_provenance(field, corrupt):
    original = _complete_public_report_fixture()
    assert_public_census_result(original)
    original[field] = corrupt
    with pytest.raises(ValueError):
        assert_public_census_result(original)


def test_census_replay_hash_is_source_pinned_not_merely_well_formed():
    forged = _complete_public_report_fixture()
    forged["replay_hash"] = "b" * 64  # valid SHA-256 syntax, wrong result
    with pytest.raises(ValueError, match="replay_hash"):
        assert_public_census_result(forged)
