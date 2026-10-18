"""FMC Docket 17-05 litigant-filed invoice exhibit: numerical candidate, NOT an awarded overcharge.

Public PDF is a litigant's submission that reproduces a purported carrier
invoice. Four OCR-extracted line items reconcile to the first extracted
exhibit total, but OCR on the next adjacent rendition is inconsistent.
This is NOT proof of a verified carrier-issued invoice, mode actually
used, charge eligibility, payment, fraud, overcharge or customer cash.

This validator is offline and read-only; no raw PII, carrier contact,
customer acceptance or public marketing claims.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"fixtures/public_fmc_17_05_invoice_image_candidate_20261018.json"
URL="https://www2.fmc.gov/readingroom/docs/17-05/17-05_Cmpl_sup_rcd.pdf/"
STATUS="LITIGANT_FILED_EXHIBIT_NOT_ADJUDICATED_TRUTH"
SCHEMA={
 "schema_version","source_publisher","original_public_filing",
 "fmc_docket","published_document_url","document_pdf_pages",
 "original_public_pdf_exhibit_page_indices_zero_based",
 "extraction_scope","publication_status",
 "shown_invoice_issuer_organization","shown_invoice_billed_organization",
 "charges","publicly_indexed_page19_total_cents",
 "page20_OCR_duplicate_rendering_has_inconsistent_total_glyphs",
 "same_image_layout_two_adjacent_pages_do_not_establish_two_independent_invoices",
 "publicly_filed_complaint_alleges_container_moved_by_ocean_while_invoice_label_air_freight",
 "allegation_carrier_currently_disputed_or_adjudicated",
 "original_ocean_BOL_image_cross_match_independently_inspected",
 "source_indexed_pdf_invoice_image_visually_inspected_independently",
 "original_carrier_issued_document_independently_authenticated",
 "copied_public_filing_pdf_full_SHA256_verified",
 "original_payment_or_bank_receipt_authenticated",
 "directly_applicable_signed_freight_contract_or_tariff_obtained",
 "current_RETALLY_customer_relationship_or_authorization",
 "actual_invoice_overcharge_independently_proven",
 "recoverable_amount_cents","real_RETALLY_customer_invoices_adjudicated",
 "real_RETALLY_customer_recovered_cents","source_limitations"
}
EXACT_CHARGES=[
 {"label":"AIR FREIGHT","cents":540000},
 {"label":"IMPORT DUTY/TAX","cents":171293},
 {"label":"CONTAINER STRIPPING","cents":112300},
 {"label":"APPOINTMENT DELIVERY","cents":95000}
]
PROHIBITIONS=(
 "The reproduction is in a public litigant filing, not a separately authenticated carrier statement or verified business customer intake.",
 "The filed party alleges an air-versus-ocean mismatch; this is a disputed assertion rather than an independent adjudication of contract charge applicability.",
 "OCR in the second overlapping invoice image has inconsistent total glyphs; only the four consistently recognized numeric line-items and the matching first extracted total are retained as candidate values.",
 "No independent scan page comparison, complete document cryptographic hash or original carrier bill-of-lading-to-invoice chain has been obtained.",
 "A bill describing air freight on a container-associated movement does not by itself determine overcharge, since modes, accessorials, tariff basis and line-item descriptions need contract evidence.",
 "No customer authorization, funds recovery, refund or independent bank posting is established."
)
NEVER_VERIFIED={
 "original_ocean_BOL_image_cross_match_independently_inspected":False,
 "source_indexed_pdf_invoice_image_visually_inspected_independently":False,
 "original_carrier_issued_document_independently_authenticated":False,
 "copied_public_filing_pdf_full_SHA256_verified":False,
 "original_payment_or_bank_receipt_authenticated":False,
 "directly_applicable_signed_freight_contract_or_tariff_obtained":False,
 "current_RETALLY_customer_relationship_or_authorization":False,
 "actual_invoice_overcharge_independently_proven":False,
 "recoverable_amount_cents":None,
 "real_RETALLY_customer_invoices_adjudicated":0,
 "real_RETALLY_customer_recovered_cents":0
}

def _fail(msg:str)->None:
    raise ValueError("FMC_ORIGINAL_INVOICE_CANDIDATE_"+msg)

def verified_candidate()->dict:
    if SOURCE.is_symlink() or not SOURCE.is_file() or SOURCE.stat().st_size>10_000:
        _fail("UNTRUSTED_FILE")
    try:
        raw=json.loads(SOURCE.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError("FMC_ORIGINAL_INVOICE_CANDIDATE_MALFORMED_JSON") from exc
    if (type(raw) is not dict or set(raw)!=SCHEMA
        or type(raw["schema_version"]) is not int or raw["schema_version"]!=1
        or raw["source_publisher"]!="U.S. Federal Maritime Commission Reading Room"
        or raw["original_public_filing"]!="CMI Distribution, Inc. response to presiding judge's August 16, 2017 order to supplement the record"
        or raw["fmc_docket"]!="17-05"
        or raw["published_document_url"]!=URL
        or type(raw["document_pdf_pages"]) is not int
        or raw["document_pdf_pages"]!=113
        or raw["original_public_pdf_exhibit_page_indices_zero_based"]!=[19,20]
        or raw["extraction_scope"]!="ONLY_FOUR_CHARGE_NUMBERS_AND_TOTAL_TRANSCRIBED_FROM_PUBLIC_PDF_EXHIBIT_OCR"
        or raw["publication_status"]!=STATUS
        or raw["shown_invoice_issuer_organization"]!="Service by Air, Inc."
        or raw["shown_invoice_billed_organization"]!="CMI Distribution, Inc."
        or type(raw["charges"]) is not list or raw["charges"]!=EXACT_CHARGES
        or type(raw["publicly_indexed_page19_total_cents"]) is not int
        or raw["publicly_indexed_page19_total_cents"]!=918593
        or raw["page20_OCR_duplicate_rendering_has_inconsistent_total_glyphs"] is not True
        or raw["same_image_layout_two_adjacent_pages_do_not_establish_two_independent_invoices"] is not True
        or raw["publicly_filed_complaint_alleges_container_moved_by_ocean_while_invoice_label_air_freight"] is not True
        or raw["allegation_carrier_currently_disputed_or_adjudicated"]!="NOT_ESTABLISHED"
        or any(type(raw[k]) is not type(v) or raw[k]!=v
               for k,v in NEVER_VERIFIED.items())
        or type(raw["source_limitations"]) is not list
        or tuple(raw["source_limitations"])!=PROHIBITIONS):
        _fail("SOURCE_OR_COMMERCIAL_CLAIMS_NOT_AUTHENTICATED")
    if (sum(x["cents"] for x in raw["charges"])
        !=raw["publicly_indexed_page19_total_cents"]):
        _fail("PUBLIC_OCR_LINE_ITEM_SUM_MISMATCH")
    return raw

def report()->dict:
    original=verified_candidate()
    return {
        "scope":"FMC_PUBLIC_LITIGANT_FILED_INVOICE_IMAGE_CANDIDATE_NOT_VERIFIED_CARRIER_BILL",
        "federal_public_filing_docket":"17-05",
        "source_exhibit_pdf_page_number_zero_based":19,
        "adjacent_OCR_rendition_uncertain":True,
        "unique_actual_source_invoice_verified":False,
        "one_candidate_invoice_not_two_independent_invoices":True,
        "distinct_charge_labels":len(original["charges"]),
        "candidate_OCR_line_total_cents":sum(x["cents"] for x in original["charges"]),
        "candidate_OCR_extracted_invoice_total_cents":918593,
        "candidate_OCR_arithmetic_reconciles":True,
        "mode_mismatch_is_LITIGANT_ALLEGATION_only":True,
        "original_bill_of_lading_cross_match_verified":False,
        "invoice_actually_paid_verified":False,
        "carrier_specific_contract_and_tariff_verified":False,
        "adjudicated_charge_invalidity_proven":False,
        "invoice_overcharge_cents":None,
        "actual_cash_received_cents":None,
        "real_RETALLY_customer_invoices":0,
        "real_RETALLY_customer_recoveries_cents":0,
        "commercial_claim_clearance":"NO_GO"
    }

if __name__=="__main__":
    print(json.dumps(report(),sort_keys=True,indent=2))
