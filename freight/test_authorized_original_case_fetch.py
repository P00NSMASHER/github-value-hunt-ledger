"""Offline synthetic-only tests: no third-party source material or network."""
from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from freight.research.authorized_original_case_fetch import (
    AcquisitionHold, SOURCE_REGISTRY, MAX_PDF_BYTES, fetch_pinned_pdf,
    inspect_sources, normalize_https_url, private_destination, validate_pdf,
    case_text_signals, inspect_pdf_text,
)


SYNTHETIC_PDF = b"%PDF-1.4\n" + b"SYNTHETIC-ONLY-DOCUMENT\n" * 12 + b"\n%%EOF\n"


class FakeReply:
    def __init__(self, url, payload=SYNTHETIC_PDF, status=200):
        self.url, self.payload, self.status = url, payload, status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.payload[:limit]


def fake_retrieve(url):
    if url == SOURCE_REGISTRY["globaltranz-original-broker-bills"]["url"]:
        return FakeReply(url)
    raise ConnectionError("synthetic unavailable")


class TestOriginalSourceAcquisition(unittest.TestCase):
    def test_known_pdf_verifies_bytes(self):
        validate_pdf(SYNTHETIC_PDF)

    def test_naked_text_page_is_not_original_pdf(self):
        with self.assertRaisesRegex(AcquisitionHold, "NOT_AN_ORIGINAL_PDF"):
            validate_pdf(b"<!doctype html><html>" + b"x" * 120 + b"</html>")

    def test_truncated_pdf_refused(self):
        with self.assertRaisesRegex(AcquisitionHold, "TRUNCATED_PDF_END"):
            validate_pdf(b"%PDF-1.4\n" + b"x" * 150)

    def test_oversized_payload_refused(self):
        with self.assertRaisesRegex(AcquisitionHold, "EMPTY_OR_OVERSIZED_PDF"):
            validate_pdf(b"%PDF-" + b"x" * MAX_PDF_BYTES)

    def test_unknown_url_is_not_fetched(self):
        with self.assertRaisesRegex(AcquisitionHold, "UNREGISTERED_SOURCE"):
            fetch_pinned_pdf("https://example.invalid/unknown", retrieve=fake_retrieve)

    def test_host_spoof_blocked(self):
        with self.assertRaisesRegex(AcquisitionHold, "UNSAFE_SOURCE_URL"):
            normalize_https_url("https://www.cbca.gov.evil.example/file.pdf")

    def test_non_https_blocked(self):
        with self.assertRaisesRegex(AcquisitionHold, "UNSAFE_SOURCE_URL"):
            normalize_https_url("http://www.cbca.gov/files/decision.pdf")

    def test_path_traversal_blocked(self):
        with self.assertRaisesRegex(AcquisitionHold, "UNSAFE_SOURCE_URL"):
            normalize_https_url("https://www.cbca.gov/files/%2e%2e/secrets")

    def test_credentialed_url_blocked(self):
        with self.assertRaisesRegex(AcquisitionHold, "UNSAFE_SOURCE_URL"):
            normalize_https_url("https://name:password@www.cbca.gov/files/a.pdf")

    def test_only_original_byte_retrieval_can_claim_success(self):
        result = fetch_pinned_pdf("globaltranz-original-broker-bills", retrieve=fake_retrieve)
        self.assertEqual(result, SYNTHETIC_PDF)

    def test_wrong_final_url_holds_even_for_valid_pdf(self):
        with self.assertRaisesRegex(AcquisitionHold, "UNEXPECTED_HTTP_OR_FINAL_URL"):
            fetch_pinned_pdf(
                "globaltranz-original-broker-bills",
                retrieve=lambda _: FakeReply(
                    "https://www.cbca.gov/other.pdf"
                )
            )

    def test_http_failure_holds(self):
        with self.assertRaisesRegex(AcquisitionHold, "UNEXPECTED_HTTP_OR_FINAL_URL"):
            fetch_pinned_pdf(
                "globaltranz-original-broker-bills",
                retrieve=lambda url: FakeReply(url, status=404),
            )

    def test_public_checkout_directories_forbidden(self):
        checkout = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(AcquisitionHold, "NO_ORIGINAL_DOCUMENT_BYTES_IN_GIT"):
            private_destination(str(checkout / "freight" / "no-real-documents"))

    def test_synthetic_retrieval_report_never_implies_recovery(self):
        report = inspect_sources(retrieve=fake_retrieve)
        self.assertEqual(report["retrieved_document_count"], 1)
        self.assertFalse(report["freight_recovery_case_complete"])
        self.assertFalse(report["bank_clearing_verified"])
        self.assertEqual(report["verified_retally_recovered_cents"], 0)
        self.assertFalse(report["raw_bytes_in_public_repository"])
        self.assertEqual(
            [e["state"] for e in report["sources"]].count("DOWNLOADED_ORIGINAL_PDF_BYTES"),
            1,
        )
        self.assertTrue(all("INVOICE-SECRET" not in str(x) for x in report["sources"]))


    def test_claim_transfer_requires_same_page_exact_claim_numbers_and_artivo(self):
        one = "GlobalTranz proof of claim 10002 original 25,954.47"
        two = "Transferred to Artivo 24,457.95 retained 1,496.52"
        result = case_text_signals(
            "court-globaltranz-final-order-623", [one, two]
        )
        self.assertFalse(result["court_claim_liability_transfer_page_coincident"])
        self.assertEqual(result["matching_source_pages"], [])

    def test_claim_transfer_matches_only_coincident_page_not_cash(self):
        text = "GlobalTranz 10002 original 25,954.47 transferred 24,457.95 to Artivo retained 1,496.52"
        result = case_text_signals(
            "court-globaltranz-final-order-623", ["unrelated page", text]
        )
        self.assertTrue(result["court_claim_liability_transfer_page_coincident"])
        self.assertEqual(result["matching_source_pages"], [2])
        self.assertFalse(result["reported_transfer_is_recovery"])

    def test_broker_issued_invoice_never_becomes_carrier_origin_bill(self):
        result = case_text_signals(
            "globaltranz-original-broker-bills", [
                "Globaltranz Invoice Carrier: ExampleCarrier",
            ]
        )
        self.assertTrue(result["original_broker_invoice_page_identified"])
        self.assertFalse(result["original_underlying_carrier_invoice_verified"])

    def test_adjudicator_win_has_no_refund_clearing(self):
        result = case_text_signals(
            "cbca-aare-6578-adjudication", ["AARE's claim is granted"]
        )
        self.assertTrue(result["independent_board_granted_aare_claim"])
        self.assertFalse(result["refund_bank_clearing_verified"])

    def test_adjudicator_loss_has_no_offset_clearing(self):
        result = case_text_signals(
            "cbca-arpin-6729-adjudication", ["The claim is denied."]
        )
        self.assertTrue(result["independent_board_denied_arpin_claim"])
        self.assertFalse(result["offset_bank_clearing_verified"])

    def test_malformed_fake_pdf_never_claims_text_provenance(self):
        # PDF header and EOF alone do not guarantee searchable page content.
        result = inspect_pdf_text("court-globaltranz-final-order-623", SYNTHETIC_PDF)
        self.assertNotEqual(result.get("source_text_status"), "TEXT_EXTRACTED_NO_SOURCE_TEXT_LOGGED")


    def test_direct_carrier_invoice_reference_does_not_prove_payment(self):
        p = case_text_signals("arcbest-underlying-carrier-invoices",
                              ["ABF Freight Bill 051894063 amount 2123.79"])
        self.assertEqual(p["carrier_origin_invoice_text_reference_pages"], [1])
        self.assertFalse(p["actual_original_payment_bank_clearing_verified"])
        self.assertFalse(p["freight_overcharge_adjudicated"])

    def test_direct_carrier_invoice_pages_must_not_be_invented(self):
        p = case_text_signals("arcbest-underlying-carrier-invoices",
                              ["ABF bill unrelated", "051894063 without carrier header"])
        self.assertEqual(p["carrier_origin_invoice_text_reference_pages"], [])

    def test_possible_abf_refund_allowance_is_not_a_settled_credit(self):
        p = case_text_signals(
            "arcbest-underlying-carrier-invoices",
            ["ABF invoice 051894063. A refund allowance of US-$21.61 may be paid to consignee."],
        )
        self.assertEqual(p["conditional_unloading_allowance_text_pages"], [1])
        self.assertFalse(p["conditional_allowance_proves_executed_refund"])
        self.assertFalse(p["actual_original_payment_bank_clearing_verified"])

    def test_fmc_original_carrier_invoice_refund_not_implied(self):
        p = case_text_signals("fmc-pro-transport-carrier-invoice-exhibits",
                              ["PRO TRANSPORT INC Invoice 84579 BOL B436543"])
        self.assertEqual(p["issued_carrier_invoice_text_reference_pages"], [1])
        self.assertFalse(p["bank_cleared_original_payment_verified"])
        self.assertFalse(p["bank_cleared_executed_refund_verified"])

    def test_fmc_forwarder_invoice_not_underlying_linehaul_carrier_bill(self):
        p = case_text_signals("fmc-uti-freight-invoice-and-bol",
                              ["UTI invoice CHI023693200 shipment BOL 5860613289"])
        self.assertEqual(p["original_forwarder_invoice_text_reference_pages"], [1])
        self.assertFalse(p["underlying_linehaul_carrier_bill_verified"])
        self.assertFalse(p["bank_cleared_recovery_verified"])

    def test_fmc_claimant_acknowledges_refund_not_bank_cleared_overcharge(self):
        p = case_text_signals("fmc-terra-refund-decision",
                              ["Complainant acknowledged a refund of $1,985"])
        self.assertEqual(p["adjudication_text_mentions_refund_pages"], [1])
        self.assertFalse(p["bank_cleared_refund_verified"])
        self.assertFalse(p["overcharge_independently_adjudicated"])

    def test_registry_never_marks_new_case_as_required_positive(self):
        for key in (
            "arcbest-underlying-carrier-invoices",
            "fmc-pro-transport-carrier-invoice-exhibits",
            "fmc-uti-freight-invoice-and-bol",
            "fmc-terra-refund-decision",
        ):
            self.assertIn(key, SOURCE_REGISTRY)
            self.assertFalse(SOURCE_REGISTRY[key]["required"])

    def test_color_brands_invoice_ach_reference_not_proven_bank_clearance(self):
        records = [
            "AAF Invoice I2007047 ocean freight and cargo insurance.",
            "Exhibit 3: Proof of Complainant ACH payment of Invoice I2007047",
        ]
        got = case_text_signals("fmc-color-brands-original-invoices-and-ach", records)
        self.assertEqual(got["original_invoice_reference_pages"]["i2007047"], [1, 2])
        self.assertEqual(got["filed_ach_payment_evidence_reference_pages"], [2])
        self.assertFalse(got["separately_bank_cleared_original_payment_verified"])
        self.assertFalse(got["executed_reparations_bank_receipt_verified"])
        self.assertFalse(got["frozen_invoice_level_overcharge_truth_verified"])

    def test_color_brands_no_invoice_reference_yields_empty_not_success(self):
        got = case_text_signals("fmc-color-brands-original-invoices-and-ach",
                                ["No referenced freight bill here", "ACH banking instructions only"])
        self.assertEqual(got["original_invoice_reference_pages"]["i2109072"], [])
        self.assertFalse(got["governing_effective_tariff_or_rate_verified"])

    def test_zelle_under_protest_is_not_refund_or_adjudication(self):
        got = case_text_signals("fmc-kaushik-quote-invoices-zelle-evidence",
                                ["SFL original invoice $7,840.00", "Zelle paid under protest"])
        self.assertEqual(got["filed_forwarder_invoice_text_pages"], [1])
        self.assertEqual(got["filed_original_payment_claim_pages"], [2])
        self.assertTrue(got["refund_executed_not_established"])
        self.assertFalse(got["overcharge_independently_adjudicated"])

    def test_new_research_source_is_optional_and_private_data_unpublished(self):
        keys = ("fmc-color-brands-original-invoices-and-ach",
                "fmc-kaushik-quote-invoices-zelle-evidence")
        for key in keys:
            self.assertIn(key, SOURCE_REGISTRY)
            self.assertFalse(SOURCE_REGISTRY[key]["required"])
            self.assertTrue(SOURCE_REGISTRY[key]["private_third_party_content"])

    def test_2022_carrier_detention_tariff_date_is_not_shipment_rate_proof(self):
        p = case_text_signals(
            "cma-cgm-india-2022-export-detention-rate",
            ["CMA CGM Revision 20th Jan 2022. Export Container Detention Charges"],
        )
        self.assertEqual(p["issued_general_rate_effective_date_text_pages"], [1])
        self.assertFalse(p["particular_shipments_rated_against_this_tariff"])
        self.assertFalse(p["private_agreement_or_later_amendment_excluded"])
        self.assertFalse(p["final_credit_to_shipper_executed"])

    def test_export_demurrage_not_interchangeable_with_detention(self):
        p = case_text_signals(
            "cma-cgm-india-2022-export-demurrage-rate",
            ["CMA - CGM Revision 20th January 2022 export demurrage charges"],
        )
        self.assertEqual(p["issued_general_rate_effective_date_text_pages"], [1])
        self.assertFalse(p["particular_shipments_rated_against_this_tariff"])

    def test_rate_reference_without_effective_date_is_held(self):
        p = case_text_signals(
            "cma-cgm-india-2022-export-detention-rate",
            ["CMA CGM official India general rates 2026"],
        )
        self.assertEqual(p["issued_general_rate_effective_date_text_pages"], [])

    def test_new_rate_documents_are_optional_third_party_sources(self):
        for key in ("cma-cgm-india-2022-export-detention-rate",
                    "cma-cgm-india-2022-export-demurrage-rate"):
            self.assertIn(key, SOURCE_REGISTRY)
            self.assertFalse(SOURCE_REGISTRY[key]["required"])
            self.assertTrue(SOURCE_REGISTRY[key]["private_third_party_content"])

    def test_private_local_download_is_owner_only_and_source_hashed(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "originals")
            receipt = inspect_sources(retrieve=fake_retrieve, dest=path)
            name = "globaltranz-original-broker-bills.pdf"
            stored = Path(path) / name
            self.assertTrue(stored.exists())
            self.assertEqual(stored.read_bytes(), SYNTHETIC_PDF)
            self.assertEqual(
                receipt["sources"][0]["sha256"],
                hashlib.sha256(SYNTHETIC_PDF).hexdigest(),
            )
            if os.name != "nt":
                self.assertEqual(stored.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
