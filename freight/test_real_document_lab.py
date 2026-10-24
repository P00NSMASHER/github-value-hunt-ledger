"""Offline adversarial contracts for the real-document lab; no network required."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
from freight.real_document_lab import (
    _arcbest_page, _global_page, _recon_result, blind_freight_assessment,
    fetch_public, iso_date, minor, parse_pennine_csv, statement_rows,
    reference_scoped_replay, InvoiceFace, _rating_probe, survey_historical_adjudications,
    adversarial_declared_payment_controls, require_frozen_source, digest, _ApprovedRedirects,
    historical_reference_money_controls, globaltranz_charge_components,
    globaltranz_invoice_line_total_benchmark,
    globaltranz_canonical_v2_adjustment_replay, FROZEN_DOCUMENT_SHA256,
)
from recoveryworks.reconciliation_kernel import ReconTxn


class LaboratoryTests(unittest.TestCase):
    def test_exact_money_parse_including_british_presentation(self):
        self.assertEqual(minor("29,601.74"), 2960174)
        self.assertEqual(minor("£35,032.20"), 3503220)
        self.assertEqual(minor("(12.34)"), -1234)
        self.assertEqual(minor("0.09"), 9)
        for bad in ("NaN", "1.234", "1e3", "1,2,3x", "1,2", "1,23.45", "1,234,56", "££1.00", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                minor(bad)

    def test_frozen_public_sources_reject_byte_drift(self):
        with self.assertRaisesRegex(ValueError, "FROZEN_PUBLIC_SOURCE_CHANGED"):
            require_frozen_source("document", "globaltranz", b"%PDF-1.4 changed source")
        with self.assertRaisesRegex(ValueError, "unknown frozen source identity"):
            require_frozen_source("pennine", "unknown", b"x")
        payload = b"known legitimate fixture bytes"
        with patch.dict("freight.real_document_lab.FROZEN_DOCUMENT_SHA256",
                        {"globaltranz": digest(payload)}):
            self.assertEqual(
                require_frozen_source("document", "globaltranz", payload),
                digest(payload),
            )

    def test_allowlisted_https_redirect_checked_before_follow(self):
        from urllib.request import Request
        request = Request("https://www.penninecare.nhs.uk/download_file/5855/277")
        handler = _ApprovedRedirects()
        for target in (
            "https://evil.example.net/collect",
            "http://www.penninecare.nhs.uk/download_file/5855/277",
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, "found", {}, target)
        with self.assertRaises(ValueError):
            fetch_public("http://www.penninecare.nhs.uk/download_file/5855/277")

    def test_csv_bytes_decode_fail_closed(self):
        with self.assertRaises(UnicodeDecodeError):
            parse_pennine_csv(b"\xff\xfe", "2026-08")

    def test_uk_source_dates_and_money_are_exact(self):
        self.assertEqual(iso_date("05/08/2026"), "2026-08-05")
        sample = (
            "RT2N0012 - AP Invoices over 25K\n,\n"
            "Business Unit Name,Supplier Type,Supplier,Supplier Number,Site,"
            "Remit-to Bank Account,Payment Document,Payment Method,Payment Date,"
            "Payment Number,Payment Currency,Invoice Number,Invoice Date,"
            "Invoice Description,Payment Status Name,Invoice Amount\n"
            'BU,Other,Example,35,ZIP,REMIT,BACS,EFT,05/08/2026,5174602,GBP,000123,06/07/2026,,Fully paid,"29,601.74"\n'
        ).encode("utf-8")
        records = parse_pennine_csv(sample, "2026-08")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["invoice number"], "000123")
        self.assertEqual(records[0]["invoice_amount_minor"], 2960174)

    def test_missing_columns_and_unsafe_host_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_pennine_csv(b"hello,world\nx,y\n", "2026-08")
        with self.assertRaises(ValueError):
            fetch_public("https://evil.example.net/download_file/5855/277")

    def test_real_invoice_face_regex_regressions(self):
        global_text = (
            "Invoice Date Pick-Up Date Invoice No\n"
            "05/13/2025 04/25/2025 30794056\n"
            "Carrier: R&L Carriers\n"
            "542.78\n78.91\n-280.61\n"
            "Total: 200.00 341.08 USD\n"
            "Invoice No. Amount Due Amount Enclosed\n30794056 $341.08\n"
        )
        f = _global_page(global_text, 4)
        self.assertIsNotNone(f)
        self.assertEqual((f.number, f.cents), ("30794056", 34108))
        arc_text = (
            "ORIGINAL INVOICE\nService: LTL\nFreight bill No: 051894063\n"
            "Shipment Date: 05/02/2024\nAMOUNT DUE:\n"
            "(payable in US funds)\n$2,123.79\n"
        )
        f = _arcbest_page(arc_text, 16)
        self.assertIsNotNone(f)
        self.assertEqual((f.number, f.cents, f.mode), ("051894063", 212379, "LTL"))

    def test_actual_invoice_component_sum_and_adversarial_one_cent(self):
        content = (
            "Pieces Pallet Description Class Weight Charges\n"
            "1\n0\nTILE\n175\n200\n"
            "542.78\n78.91\n-280.61\n"
            "Total: 200.00 341.08 USD\n"
        )
        self.assertEqual(globaltranz_charge_components(content),
                         (54278, 7891, -28061))
        face = InvoiceFace(
            "globaltranz", "30794056", 1, 34108,
            "2025-05-13", "2025-04-25", None)
        report = globaltranz_invoice_line_total_benchmark([face], [content])
        self.assertEqual(report["invoice_face_exact_line_sum"], 1)
        self.assertEqual(report["negative_adjustment_tokens"], 1)
        self.assertEqual(report["invoice_faces_containing_negative_discounts"], 1)
        self.assertEqual(report["invoice_faces_canonical_signed_charge_schema_compatible"], 0)
        self.assertFalse(report["production_freight_ChargeLine_accepts_negative_discounts"])
        from freight.canonical_schema import ChargeLine
        with self.assertRaisesRegex(ValueError, "billed_cents"):
            ChargeLine(charge_id="discount", charge_code="DISC", billed_cents=-1)
        self.assertTrue(report["every_face_conserved"])
        self.assertFalse(report["line_sum_proves_controlling_rate_or_overcharge"])
        modified = content.replace("78.91", "78.92")
        changed = globaltranz_invoice_line_total_benchmark([face], [modified])
        self.assertEqual(changed["invoice_face_exact_line_sum"], 0)
        self.assertEqual(changed["invoice_face_nonmatching_extracted_line_sum"], 1)


    def test_original_pdf_discounts_flow_through_v2_without_auto_rating(self):
        signed = (
            "Pieces Pallet Description Class Weight Charges\n"
            "1\n0\nTILE\n175\n200\n"
            "542.78\n78.91\n-280.61\n"
            "Total: 200.00 341.08 USD\n"
        )
        plain = (
            "Pieces Pallet Description Class Weight Charges\n"
            "1\n0\nGENERAL\n100\n1\n120.00\n"
            "Total: 1.00 120.00 USD\n"
        )
        faces = [
            InvoiceFace("globaltranz", "30794056", 1, 34108,
                        "2025-05-13", "2025-04-25", None),
            InvoiceFace("globaltranz", "30794057", 2, 12000,
                        "2025-05-14", "2025-04-25", None),
        ]
        sha = FROZEN_DOCUMENT_SHA256["globaltranz"]
        report = globaltranz_canonical_v2_adjustment_replay(
            faces, [signed, plain], sha)
        self.assertEqual(report["canonical_v2_records_with_exact_net"], 2)
        self.assertEqual(report["canonical_records_built"], 2)
        self.assertEqual(report["discount_bearing_v2_records"], 1)
        self.assertEqual(report["rate_review_required"], 2)
        self.assertEqual(report["unrepresentable_or_missing_source"], 0)
        self.assertEqual(report["unsafe_auto_money_or_nondeterministic"], 0)
        self.assertTrue(report["input_original_pdf_digest_matches_frozen_baseline"])
        self.assertTrue(report["shipment_fields_are_synthetic_lab_placeholders"])
        self.assertTrue(report["invoice_adjustment_kind_is_lab_hypothesis_not_adjudicated"])
        self.assertFalse(report["production_pdf_extraction_completed"])
        self.assertFalse(report["commercial_rate_authority_verified"])
        self.assertEqual(report["independent_invoice_overcharge_labels"], 0)
        self.assertEqual(report["recovered_cash_cents"], 0)
        self.assertEqual(report["customer_contact_actions"], 0)
        again = globaltranz_canonical_v2_adjustment_replay(faces, [signed, plain], sha)
        self.assertEqual(report, again)

    def test_original_pdf_v2_catches_one_cent_or_missing_original_fields(self):
        base = (
            "Pieces Pallet Description Class Weight Charges\n"
            "1\n0\nTILE\n175\n200\n"
            "542.78\n78.91\n-280.61\n"
            "Total: 200.00 341.08 USD\n"
        )
        face = InvoiceFace("globaltranz", "30794056", 1, 34108,
                           "2025-05-13", "2025-04-25", None)
        bad = base.replace("78.91", "78.92")
        result = globaltranz_canonical_v2_adjustment_replay(
            [face], [bad], FROZEN_DOCUMENT_SHA256["globaltranz"])
        self.assertEqual(result["canonical_records_built"], 0)
        self.assertEqual(result["unrepresentable_or_missing_source"], 1)
        self.assertEqual(result["incomplete_source_reason_counts"],
                         {"ORIGINAL_FACE_NET_NOT_RECONCILED": 1})
        # Original PDF SHA must be canonical lowercase hex even for a lab
        # proxy; mutation must never be silently treated as a valid original.
        with self.assertRaisesRegex(ValueError, "LAB_SOURCE_SHA256_REQUIRED"):
            globaltranz_canonical_v2_adjustment_replay([face], [base], "not-a-sha")
        with self.assertRaisesRegex(ValueError, "LAB_SOURCE_SHA256_REQUIRED"):
            globaltranz_canonical_v2_adjustment_replay([face], [base], "A" * 64)
        invalid = InvoiceFace("globaltranz", "30794056", 1, 34108,
                              None, "2025-04-25", None)
        missing = globaltranz_canonical_v2_adjustment_replay(
            [invalid], [base], FROZEN_DOCUMENT_SHA256["globaltranz"])
        self.assertEqual(missing["canonical_records_built"], 0)
        self.assertEqual(missing["unrepresentable_or_missing_source"], 1)
        self.assertEqual(missing["incomplete_source_reason_counts"],
                         {"FACE_IDENTITY_DATE_OR_AMOUNT_INCOMPLETE": 1})

    def test_v2_adjustment_cannot_outgrow_original_positive_invoice_charge(self):
        # This would have an unverified negative face total. The adapter must
        # not manufacture credit, negative freight charges, or recovered cash.
        content = (
            "Pieces Pallet Description Class Weight Charges\n"
            "1\n0\nTILE\n100\n1\n100.00\n-120.00\n"
            "Total: 1.00 -20.00 USD\n"
        )
        face = InvoiceFace("globaltranz", "30794058", 1, -2000,
                           "2025-05-13", "2025-04-25", None)
        result = globaltranz_canonical_v2_adjustment_replay(
            [face], [content], FROZEN_DOCUMENT_SHA256["globaltranz"])
        self.assertEqual(result["canonical_records_built"], 0)
        self.assertEqual(result["unrepresentable_or_missing_source"], 1)
        self.assertEqual(result["recovered_cash_cents"], 0)

    def test_open_statement_is_not_a_cleared_payment(self):
        texts = [""] * 120
        texts[114] = (
            "Transaction Class Activity Date Entered Currency Original Amount Current Amount\n"
            "29937996 Invoice 11/8/24 USD 201.4 129.26\n"
            "30984884 A Invoice 6/25/25 USD 29.88 29.88\n"
        )
        rows = statement_rows(texts)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(r["original"] - r["current"] for r in rows), 7214)
        self.assertEqual(rows[1]["number"], "30984884 A")

    def test_actual_kernel_cross_reference_mismatch_visible(self):
        internal = [ReconTxn("i1", "100.00", "2026-07-01", "GBP", "PAY-1")]
        counterpart = [ReconTxn("p2", "100.00", "2026-07-01", "GBP", "PAY-2")]
        report = _recon_result(internal, counterpart, {"i1": "PAY-1", "p2": "PAY-2"})
        self.assertGreaterEqual(report["cross_reference_false_joins"], 1)

    def test_actual_kernel_reference_scope_preserves_many_invoice_groups(self):
        invoice_rows = [
            ReconTxn("i1", "12.00", "2026-07-01", "GBP", "PAY1"),
            ReconTxn("i2", "9.00", "2026-07-01", "GBP", "PAY1"),
            ReconTxn("i3", "5.00", "2026-07-01", "GBP", "PAY2"),
        ]
        declarations = [
            ReconTxn("p1", "21.00", "2026-07-01", "GBP", "PAY1"),
            ReconTxn("p2", "5.00", "2026-07-01", "GBP", "PAY2"),
        ]
        a_keys = {"i1": "PAY1", "i2": "PAY1", "i3": "PAY2"}
        b_keys = {"p1": "PAY1", "p2": "PAY2"}
        result = reference_scoped_replay(
            invoice_rows, declarations, a_keys, b_keys, max_group_size=8)
        self.assertEqual(result["matched_invoices"], 3)
        self.assertEqual(result["matched_groups"], 2)
        self.assertEqual(result["cross_reference_false_joins"], 0)
        self.assertEqual(result["by_kernel_rule"]["many-to-one"], 1)
        capped = reference_scoped_replay(
            invoice_rows, declarations, a_keys, b_keys, max_group_size=1)
        self.assertEqual(capped["matched_invoices"], 1)
        self.assertEqual(capped["unmatched_over_group_bound_invoices"], 2)

    def test_real_kernel_falsifies_corrupted_source_declarations(self):
        invoices = [
            ReconTxn("inv-1", "12.00", "2026-07-01", "GBP", "PAY1"),
            ReconTxn("inv-2", "9.00", "2026-07-01", "GBP", "PAY1"),
            ReconTxn("inv-3", "5.00", "2026-07-01", "GBP", "PAY2"),
        ]
        declarations = [
            ReconTxn("pay-1", "21.00", "2026-07-01", "GBP", "PAY1"),
            ReconTxn("pay-2", "5.00", "2026-07-01", "GBP", "PAY2"),
        ]
        inv = {"inv-1": "PAY1", "inv-2": "PAY1", "inv-3": "PAY2"}
        pay = {"pay-1": "PAY1", "pay-2": "PAY2"}
        result = adversarial_declared_payment_controls(invoices, declarations, inv, pay)
        self.assertEqual(result["scenario_count"], 4)
        self.assertTrue(result["all_controls_detected"])
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["independently_cleared_bank_rows_used"], 0)
        self.assertIsNone(result["real_world_economic_false_positive_rate"])

    def test_actual_freight_rating_engine_abstains_on_lab_proxy(self):
        page = (
            "ORIGINAL INVOICE\nService: LTL\nFreight Bill No: 044177205\n"
            "AMOUNT DUE: $314.77\nShipper Acct. # 00001\n"
            "Freight Bill No: 044177205\n"
            "SHIPPER NAME\nLAUREL HILL, NC 28351\n"
            "CONSIGNEE NAME\nMERIDEN, CT 06450\n"
            "Shipping Date: 05/01/2024\n"
            "Total Pieces Total Weight TOTAL AMOUNT\n$314.77 1 320\n"
        )
        face = InvoiceFace("arcbest", "044177205", 1, 31477,
                           None, "2024-05-01", "LTL")
        result = _rating_probe([face], [page], "a" * 64)
        self.assertEqual(result["lab_proxy_canonical_records_executed"], 1)
        self.assertEqual(result["engine_review_required"], 1)
        self.assertEqual(result["unsafe_auto_money_or_nondeterministic"], 0)
        self.assertEqual(result["auto_overcharges_asserted"], 0)

    def test_adjudication_refs_cannot_be_promoted_to_labels(self):
        with patch("freight.real_document_lab.fetch_public", return_value=b"<html>GAO</html>"):
            result = survey_historical_adjudications()
        self.assertEqual(result["government_decision_reference_count"], 8)
        self.assertEqual(result["source_pages_fetched"], 8)
        self.assertEqual(result["full_independent_case_labels_for_test_invoices"], 0)
        self.assertIsNone(result["real_freight_accuracy_from_these_sources"])
        notes = result["curated_official_decision_challenge_examples"]
        self.assertEqual(len(notes), 3)
        self.assertEqual(notes["B-221594-0"]["independent_decision_summary"],
                         "GOVERNMENT_OVERCHARGE_DETERMINATION_REVERSED")
        self.assertTrue(all(not r["is_label_for_test_invoice"] for r in notes.values()))

    def test_real_historical_GAO_decision_arithmetic_never_becomes_recovery(self):
        result = historical_reference_money_controls()
        self.assertTrue(result["all_reference_arithmetic_exact"])
        self.assertEqual(result["reference_cases"], 3)
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["original_invoice_documents_joined"], 0)
        self.assertEqual(result["independently_scored_freight_cases"], 0)
        self.assertEqual(result["recovery_claims_usd_minor"], 0)
        # A rate/tender invalidation cannot be turned into an overcharge
        # finding merely because a billed-minus-proposed subtraction works.
        from copy import deepcopy
        from freight.real_document_lab import HISTORICAL_GAO_AMOUNT_REFERENCES
        corrupt = deepcopy(HISTORICAL_GAO_AMOUNT_REFERENCES)
        corrupt["B-221594-0"]["legal_disposition"] = "INVALID_TEST_OVERRIDE"
        with patch.dict(
            "freight.real_document_lab.HISTORICAL_GAO_AMOUNT_REFERENCES",
            corrupt, clear=True,
        ):
            check = historical_reference_money_controls()
        self.assertFalse(check["all_reference_arithmetic_exact"])
        self.assertFalse(check["checks"][
            "gao_b221594_ledger_math_does_not_validate_invalid_deduction"])

    def test_native_pdf_ingress_is_not_pdf_extraction(self):
        receipt = ingest_bytes(
            IngressEnvelope("test", "research", "ephemeral", "BATCH", "document.pdf"),
            b"%PDF-1.4\n% test PDF envelope",
        )
        self.assertEqual(receipt.route, "DOCUMENT_EXTRACTION_REQUIRED")
        self.assertEqual(receipt.status, "ACCEPT")

    def test_blinded_freight_does_not_invent_labels(self):
        result = blind_freight_assessment({
            "globaltranz": {"distinct_invoice_face_ids": 100,
                            "sha256": "a" * 64,
                            "source_face_catalog_sha256": "c" * 64},
            "arcbest": {"distinct_invoice_face_ids": 10,
                        "sha256": "b" * 64,
                        "source_face_catalog_sha256": "d" * 64},
        })
        self.assertEqual(result["unknown_cases_preserved"], 110)
        self.assertFalse(result["predictions_frozen_before_truth"])
        self.assertEqual(result["blinding_protocol_status"],
                         "NOT_EXECUTED_INDEPENDENT_TRUTH_AND_REVIEWERS_ABSENT")
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["freight_detection_accuracy"])
        self.assertEqual(result["validated_recovery_cents"], 0)


    def test_repeated_original_invoice_face_must_not_be_silently_overwritten(self):
        from freight.real_document_lab import index_unique_invoice_faces
        a = InvoiceFace("arcbest", "051894063", 16, 212379,
                        None, "2024-05-02", "LTL")
        same_identical = InvoiceFace("arcbest", "051894063", 18, 212379,
                                     None, "2024-05-02", "LTL")
        changed_amount = InvoiceFace("arcbest", "051894063", 18, 212380,
                                     None, "2024-05-02", "LTL")
        for duplicate in (same_identical, changed_amount):
            with self.subTest(case=duplicate.cents), self.assertRaisesRegex(
                ValueError, "DUPLICATE_PUBLIC_ORIGINAL_INVOICE_FACE"
            ) as cm:
                index_unique_invoice_faces([a, duplicate], "arcbest")
            self.assertNotIn(a.number, str(cm.exception))
        self.assertEqual(index_unique_invoice_faces([a], "arcbest"), {a.number: a})

    def test_pdf_adapter_rejects_repeated_original_invoice_face_id(self):
        from freight.real_document_lab import extract_faces, check_anchors
        original = (
            "ORIGINAL INVOICE\n"
            "Service: LTL\n"
            "Freight bill No: 051894063\n"
            "Shipment Date: 05/02/2024\n"
            "AMOUNT DUE: $2,123.79\n"
        )
        with self.assertRaisesRegex(
            ValueError, "DUPLICATE_PUBLIC_ORIGINAL_INVOICE_FACE"
        ):
            extract_faces("arcbest", [original, original])
        prior = InvoiceFace("arcbest", "051894063", 16, 212379, None,
                            "2024-05-02", "LTL")
        mutated = InvoiceFace("arcbest", "051894063", 19, 212380, None,
                              "2024-05-02", "LTL")
        with self.assertRaisesRegex(
            ValueError, "DUPLICATE_PUBLIC_ORIGINAL_INVOICE_FACE"
        ):
            check_anchors([prior, mutated], {"051894063": (19, 212380)})


if __name__ == "__main__":
    unittest.main()
