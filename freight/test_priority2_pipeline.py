"""Source-pinned original PDF candidate -> rate/evidence gates (fictional docs)."""
from dataclasses import replace

import pytest

from freight.contracts import canonical_hash
from freight.original_pdf_extraction import (
    KNOWN_ORIGINALS, OriginalExtractionBatch, _extract_page,
)
from freight.priority2_pipeline import (
    review_original_extraction, review_frozen_pdf_source, verify_original_batch,
)
from freight.priority2_evidence import witness_shipment_source, REQUIRED_SHIPMENT_FIELDS
from freight.rate_authority import AuthorityBook
from freight.test_phase0_recoveryos import ltl_record, ltl_authority


def synthetic_original():
    # Historical document *layout* example only, not external source bytes
    # and not any actual customer authorization. SHA is pinned reference.
    text=("Invoice Date Pick-Up Date Invoice No\n"
          "05/13/2025 04/25/2025 30794056\n"
          "Pieces Pallet Description Class Weight Charges\n"
          "1\n0\nSynthetic Goods 175 200\n"
          "542.78\n78.91\n-280.61\n"
          "Total: 200.00 341.08 USD\n")
    issuer="GLOBALTRANZ"
    face=_extract_page(issuer,text,4,KNOWN_ORIGINALS[issuer]["sha256"])
    assert face is not None
    batch=OriginalExtractionBatch(
        issuer=issuer,
        source_sha256=KNOWN_ORIGINALS[issuer]["sha256"],
        document_page_count=KNOWN_ORIGINALS[issuer]["pages"],
        invoices=(face,),
        original_amount_match_count=1,
        incomplete_charge_breakdown_count=0,
        typed_adjustment_invoice_count=1,
        extraction_hash=canonical_hash({
            "schema":1,
            "source":KNOWN_ORIGINALS[issuer]["sha256"],
            "issuer":issuer,"invoice_proofs":[face.document_hash],
        }),
    )
    return batch


def test_original_page_and_typed_discounts_integrity_has_no_automatic_accuracy():
    b=synthetic_original()
    verify_original_batch(b)
    out=review_original_extraction(b)
    assert out.source_sha256 == b.source_sha256
    assert out.invoice_count==1 and out.calculated_face_amount_count==1
    assert out.face_amounts_verified==0  # no authentic original bytes in synthetic test
    assert out.source_bytes_replayed_and_verified is False
    assert out.frozen_source_expected_invoice_count==100
    assert out.frozen_original_population_complete is False
    assert out.invoices_missing_freight_accuracy_evidence==1
    assert out.unresolved_invoice_count==1
    assert out.provisional_rated_count==0
    assert out.provisional_positive_variance_cents==0
    assert out.commercially_recovered_cents==0
    assert out.real_precision is None and out.real_recall is None


def test_missing_exact_field_witness_and_changed_invoice_amount_are_rejected():
    b=synthetic_original()
    changed=replace(b.invoices[0], original_face_cents=34109)
    with pytest.raises(ValueError,match="conserve"):
        verify_original_batch(replace(b,invoices=(changed,)))
    stripped=replace(b.invoices[0],field_witnesses=())
    with pytest.raises(ValueError,match="witness"):
        verify_original_batch(replace(b,invoices=(stripped,)))


def test_original_invoice_with_unsupported_native_charge_mapping_stays_unknown():
    b=synthetic_original()
    shipment=ltl_record().shipment
    proof=witness_shipment_source(
        shipment,source_bytes=b"SYNTHETIC_BOL_NOT_AN_INDEPENDENT_CUSTOMER_RECORD",
        source_kind="BILL_OF_LADING",
        supported_fields=REQUIRED_SHIPMENT_FIELDS,
    )
    report=review_original_extraction(
        b,shipment_by_invoice={b.invoices[0].invoice_id:(shipment,proof)},
        authorities=AuthorityBook((ltl_authority(),)),
        buyer_id="BUYER-1",business_unit="BU-1",customer_id="CUSTOMER-1",
    )
    assert report.provisional_rated_count==0
    assert report.commercially_recovered_cents==0
    assert report.independently_adjudicated_freight_errors==0


def test_duplicate_original_freight_faces_and_manifest_drift_are_rejected():
    b=synthetic_original()
    with pytest.raises(ValueError,match="duplicate"):
        verify_original_batch(replace(b,invoices=(b.invoices[0],b.invoices[0])))
    with pytest.raises(ValueError,match="manifest"):
        verify_original_batch(replace(b,extraction_hash="0"*64))
    with pytest.raises(ValueError,match="denominator"):
        verify_original_batch(replace(b,original_amount_match_count=0))


def test_no_unfetched_or_forged_pdf_bytes_can_be_promoted_to_verified_original():
    b=synthetic_original()
    with pytest.raises(ValueError,match="source"):
        review_original_extraction(b,original_pdf_bytes=b"%PDF-1.7 fake-doc")


def test_reject_unknown_pdf_templates_and_fake_byte_census():
    with pytest.raises(ValueError,match="approved"):
        review_frozen_pdf_source("UNAUTHORIZED_CARRIER",b"%PDF-1.7")
    with pytest.raises(ValueError,match="source"):
        review_frozen_pdf_source("GLOBALTRANZ",b"%PDF-1.7 fraudulent-data")


def test_extra_shipment_submission_cannot_be_added_to_frozen_original():
    b=synthetic_original()
    s=ltl_record().shipment
    proof=witness_shipment_source(
        s,source_bytes=b"SYNTHETIC_ONLY",
        source_kind="BILL_OF_LADING",
        supported_fields=REQUIRED_SHIPMENT_FIELDS,
    )
    with pytest.raises(ValueError,match="outside"):
        review_original_extraction(
            b,shipment_by_invoice={"NOT_IN_ORIGINAL_SOURCE":(s,proof)},
        )
