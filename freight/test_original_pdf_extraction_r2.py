"""R2 document extraction: adversarial, witness-bound and no invented shipments."""
from dataclasses import replace

import pytest

from freight.original_pdf_extraction import (
    FieldWitness, KNOWN_ORIGINALS, _extract_page, _pennies,
    bind_independent_shipment, parse_original_pdf, safe_summary,
)
from freight.canonical_schema import verify_record
from freight.test_phase0_recoveryos import ltl_record

SHA = KNOWN_ORIGINALS["GLOBALTRANZ"]["sha256"]


def original_global_page():
    return (
        "Invoice Date Pick-Up Date Invoice No\n"
        "05/13/2025 04/25/2025 30794056\n"
        "Pieces Pallet Description Class Weight Charges\n"
        "1\n0\nTiles 175 200\n"
        "542.78\n78.91\n-280.61\n"
        "Total: 200.00 341.08 USD\n"
        "Invoice No. Amount Due Amount Enclosed\n"
    )


def test_full_original_invoice_lines_are_net_exact_with_witnesses():
    found = _extract_page("GLOBALTRANZ", original_global_page(), 4, SHA)
    assert found is not None and found.invoice_id == "30794056"
    assert found.original_face_cents == 34108
    assert found.gross_cents == 62169
    assert found.adjustment_cents == 28061
    assert found.signed_net_cents == 34108
    assert len(found.charges) == 2 and len(found.adjustments) == 1
    assert set(found.blockers) >= {"CONTROLLING_RATE_UNVERIFIED", "BANK_PAYMENT_NOT_VERIFIED"}
    assert {f.page for f in found.field_witnesses} == {4}
    assert all(f.source_sha256 == SHA for f in found.field_witnesses)
    assert len(found.document_hash) == 64
    second = _extract_page("GLOBALTRANZ", original_global_page(), 4, SHA)
    assert second.document_hash == found.document_hash


def test_one_cent_original_document_discrepancy_rejected():
    tampered = original_global_page().replace("78.91", "78.92")
    with pytest.raises(ValueError, match="do not conserve"):
        _extract_page("GLOBALTRANZ", tampered, 4, SHA)


def test_malformed_amounts_and_incomplete_charges_fail_closed():
    with pytest.raises(ValueError, match="malformed"):
        _pennies("1,2,3.45")
    with pytest.raises(ValueError, match="source"):
        parse_original_pdf("GLOBALTRANZ", b"%PDF-1.4 tampered")
    with pytest.raises(ValueError, match="approved"):
        parse_original_pdf("UNRECOGNIZED_CARRIER", b"%PDF-1.4")
    no_amount = original_global_page().replace("Total: 200.00 341.08 USD", "")
    with pytest.raises(ValueError, match="face amount"):
        _extract_page("GLOBALTRANZ", no_amount, 4, SHA)


def test_arcbest_is_extracted_but_not_fake_rated():
    text = ("ORIGINAL INVOICE\nService: LTL\nFreight bill No: 051894063\n"
            "Shipment Date: 05/02/2024\n"
            "AMOUNT DUE:\n(payable in US funds)\n$2,123.79\n")
    found = _extract_page(
        "ARCBEST", text, 16, KNOWN_ORIGINALS["ARCBEST"]["sha256"])
    assert found.invoice_id == "051894063"
    assert found.original_face_cents == 212379
    assert "CHARGE_LINES_NOT_INDEPENDENTLY_EXTRACTED" in found.blockers
    assert found.invoice_date is None
    with pytest.raises(ValueError, match="invoice date"):
        bind_independent_shipment(
            found, buyer_id="research", business_unit="test", customer_id="buyer",
            currency="USD", shipment=ltl_record().shipment,
            observed_at="2026-10-19T00:00:00.000000Z")


def test_no_unsupported_shipment_is_invented_for_original_discount():
    found = _extract_page("GLOBALTRANZ", original_global_page(), 4, SHA)
    with pytest.raises(ValueError, match="ShipmentFacts"):
        bind_independent_shipment(
            found, buyer_id="research", business_unit="test", customer_id="buyer",
            currency="USD", shipment=None, observed_at="2026-10-19T00:00:00.000000Z")
    record = bind_independent_shipment(
        found, buyer_id="research", business_unit="test", customer_id="buyer",
        currency="USD", shipment=ltl_record().shipment,
        observed_at="2026-10-19T00:00:00.000000Z")
    assert record.schema_version == 2 and record.billed_total_cents == 34108
    verify_record(record)
    assert record.adjustments[0].amount_cents == 28061


def test_source_index_is_explicitly_research_only_and_not_accuracy():
    specs = KNOWN_ORIGINALS
    assert all(len(spec["sha256"]) == 64 for spec in specs.values())
    assert specs["GLOBALTRANZ"]["faces"] == 100
    assert specs["ARCBEST"]["faces"] == 10
