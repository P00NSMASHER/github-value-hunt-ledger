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
    arcbest_printed_rate_bol_reference_census,
    arcbest_embedded_vpq_quote_reconciliation,
    arcbest_embedded_truckload_bol_reconciliation,
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

    def test_arcbest_printed_tariff_and_bol_are_hints_not_rate_proof(self):
        # All page text below is synthetic; source PDF original isn't embedded.
        pages = [
            ("ORIGINAL INVOICE\nFreight bill No: 352112867\n"
             "Tariff: ABF80193 PAYMENT DUE DATE: 05/24/2024\n"
             "Bill of Lading No: SEE BELOW AMOUNT DUE: $351.78\n"
             "PRIVATE CUSTOMER NAME MUST NEVER BE IN THE SUMMARY\n"),
            ("ORIGINAL INVOICE\nFreight Bill No: 051894063\n"
             "Tariff: VPQ PAYMENT DUE DATE: 05/21/2024\n"
             "Bill of Lading No: BOQ-123-PRIVATE AMOUNT DUE: $2,123.79\n"),
            ("ORIGINAL INVOICE\nFreight bill No: 051886768\n"
             "Tariff: ABF80193\nTariff: VPQ\n"
             "Bill of Lading No: NS AMOUNT DUE: $244.77\n"),
        ]
        faces = [
            InvoiceFace("arcbest", "352112867", 1, 35178, None, "2024-05-07", "LTL"),
            InvoiceFace("arcbest", "051894063", 2, 212379, None, "2024-05-02", "LTL"),
            InvoiceFace("arcbest", "051886768", 3, 24477, None, "2024-05-02", "LTL"),
        ]
        sha = FROZEN_DOCUMENT_SHA256["arcbest"]
        inventory = arcbest_printed_rate_bol_reference_census(faces, pages, sha)
        self.assertEqual(inventory["original_invoice_faces_considered"], 3)
        self.assertEqual(inventory["source_page_identity_bound_count"], 3)
        self.assertEqual(inventory["unbound_original_source_pages"], 0)
        self.assertEqual(inventory["printed_tariff_reference_class_counts"], {
            "CONFLICTING_PRINTED_TARIFF_REFERENCES": 1,
            "PRINTED_ABF_ACCOUNT_REFERENCE_ONLY": 1,
            "PRINTED_VOLUME_QUOTE_MARKER_ONLY": 1,
        })
        self.assertEqual(inventory["printed_bol_header_class_counts"], {
            "BOL_HEADER_IDENTIFIER_PRINTED_ONLY": 1,
            "BOL_HEADER_PLACEHOLDER_ONLY": 2,
        })
        self.assertEqual(inventory["printed_pricing_bol_joint_class_counts"], {
            "CONFLICTING_PRINTED_TARIFF_REFERENCES|BOL_HEADER_PLACEHOLDER_ONLY": 1,
            "PRINTED_ABF_ACCOUNT_REFERENCE_ONLY|BOL_HEADER_PLACEHOLDER_ONLY": 1,
            "PRINTED_VOLUME_QUOTE_MARKER_ONLY|BOL_HEADER_IDENTIFIER_PRINTED_ONLY": 1,
        })
        self.assertEqual(inventory["printed_vpq_with_bol_header_identifier_only"], 1)
        self.assertEqual(inventory["printed_vpq_without_bol_header_identifier"], 0)
        self.assertEqual(inventory["original_bol_quote_id_correspondence_independently_verified"], 0)
        self.assertTrue(inventory["printed_bol_header_is_not_original_bol_custody"])
        self.assertTrue(inventory["source_pdf_printed_reference_not_executed_rate_contract"])
        for k in (
            "original_customer_quote_documents_independently_verified",
            "independently_custodied_original_bol_documents",
            "shipment_effective_customer_rate_authorities_verified",
            "independently_scored_customer_overcharges",
            "original_source_identifiers_exported",
            "verified_retally_recovered_cash_cents",
            "third_party_contacts",
        ):
            self.assertEqual(inventory[k], 0, k)
        import json
        summary = json.dumps(inventory, sort_keys=True)
        for forbidden in ("BOQ-123-PRIVATE", "PRIVATE CUSTOMER", "352112867", "051894063",
                          "ABF80193", "Tariff:"):
            self.assertNotIn(forbidden, summary)
        again = arcbest_printed_rate_bol_reference_census(faces, pages, sha)
        self.assertEqual(inventory, again)

    def test_vpq_two_invoice_headers_never_establish_quote_id_on_original_bol(self):
        """One VPQ-printed BOL id and one placeholder: zero authoritative BOLs."""
        pages = [
            ("ORIGINAL INVOICE\nFreight bill No: 352112867\n"
             "Tariff: VPQ\nBill of Lading No: SEE BELOW\n"),
            ("ORIGINAL INVOICE\nFreight bill No: 051894063\n"
             "Tariff: VPQ\nBill of Lading No: SAMPLE-ID-NOT-ORIGINAL\n"),
        ]
        faces = [
            InvoiceFace("arcbest", "352112867", 1, 35178,
                        None, "2024-05-07", "LTL"),
            InvoiceFace("arcbest", "051894063", 2, 212379,
                        None, "2024-05-02", "LTL"),
        ]
        q = arcbest_printed_rate_bol_reference_census(
            faces, pages, FROZEN_DOCUMENT_SHA256["arcbest"])
        self.assertEqual(q["printed_vpq_with_bol_header_identifier_only"], 1)
        self.assertEqual(q["printed_vpq_without_bol_header_identifier"], 1)
        self.assertEqual(sum(q["printed_pricing_bol_joint_class_counts"].values()), 2)
        self.assertEqual(q["original_bol_quote_id_correspondence_independently_verified"], 0)
        self.assertEqual(q["independently_custodied_original_bol_documents"], 0)
        self.assertEqual(q["shipment_effective_customer_rate_authorities_verified"], 0)
        self.assertEqual(q["independently_scored_customer_overcharges"], 0)
        self.assertEqual(q["third_party_contacts"], 0)
        import json
        out = json.dumps(q)
        self.assertNotIn("SAMPLE-ID-NOT-ORIGINAL", out)
        self.assertNotIn("352112867", out)
        self.assertNotIn("051894063", out)

    def test_arcbest_tariff_bol_reference_source_identity_is_fail_closed(self):
        sha = FROZEN_DOCUMENT_SHA256["arcbest"]
        f = InvoiceFace("arcbest", "352112867", 1, 35178,
                        None, "2024-05-07", "LTL")
        page = ("ORIGINAL INVOICE\nFreight Bill No: WRONG123\n"
                "Tariff: ABF80193\nBill of Lading No: SEE BELOW\n")
        missing = arcbest_printed_rate_bol_reference_census([f], [page], sha)
        self.assertEqual(missing["unbound_original_source_pages"], 1)
        self.assertEqual(missing["printed_tariff_reference_class_counts"],
                         {"UNBOUND_SOURCE_PAGE": 1})
        self.assertEqual(missing["shipment_effective_customer_rate_authorities_verified"], 0)
        with self.assertRaisesRegex(ValueError, "ARCBEST_SOURCE_SHA256_MISMATCH"):
            arcbest_printed_rate_bol_reference_census([f], [page], "a" * 64)
        with self.assertRaisesRegex(ValueError, "ARCBEST_DUPLICATE_FACE_REFERENCE"):
            arcbest_printed_rate_bol_reference_census([f, f], [page], sha)
        with self.assertRaisesRegex(ValueError, "ARCBEST_INVALID_SOURCE_FACE"):
            arcbest_printed_rate_bol_reference_census(
                [InvoiceFace("arcbest", "352112867", 0, 35178,
                             None, "2024-05-07", "LTL")], [page], sha)


    def test_two_co_bundled_original_quotes_match_invoice_math_but_not_bol_custody(self):
        # All strings below are SYNTHETIC, not the original document's IDs.
        invoice_min = (
            "ORIGINAL INVOICE\nFreight bill No: 352112867\n"
            "Tariff: VPQ\nPQ SCHEDULE NO: SAMPLEQ101A\n"
            "ITEM 028160-01V 2,610 PPU 2,132.83\n"
            "LWH: 50 X 45 X 85 INCHES\n"
        )
        quote_min = (
            "Volume Pricing Quotation for Example\n"
            "Effective Date: 10-MAY-2024\nExpiration Date: 23-MAY-2024\n"
            "VPQ Quotation ID: SAMPLEQ101-\nA\n"
            "Weight: 2,610 lbs\n"
            "Minimum price including Fuel Surcharge* "
            "(max 14,450 lbs/17 linear ft): $ 2132.83\n"
            "*Charge per additional linear foot: $ 125.00\n"
        )
        invoice_length = (
            "ORIGINAL INVOICE\nFreight bill No: 051894063\n"
            "Tariff: VPQ\nPQ SCHEDULE NO: SAMPLEQ202B\n"
            "ITEM 049880-04V 12,573 PPU 606.00\n"
            "LWH: 525 X 80 X 72 INCHES\n"
        )
        quote_length = (
            "Volume Pricing Quotation for Example\n"
            "Effective Date: 15-APR-2024\nExpiration Date: 28-APR-2024\n"
            "VPQ Quotation ID: SAMPLEQ202-B\n"
            "Weight: 12,573 lbs\n"
            "Minimum price including Fuel Surcharge* "
            "(max 17,000 lbs/20 linear ft): $ 270.00\n"
            "*Charge per additional linear foot: $ 14.00\n"
        )
        faces = [
            InvoiceFace("arcbest", "352112867", 1, 213283,
                        None, "2024-05-13", "LTL"),
            InvoiceFace("arcbest", "051894063", 3, 60600,
                        None, "2024-04-16", "LTL"),
        ]
        text = [invoice_min, quote_min, invoice_length, quote_length]
        sha = FROZEN_DOCUMENT_SHA256["arcbest"]
        r = arcbest_embedded_vpq_quote_reconciliation(faces, text, sha)
        self.assertEqual(r["embedded_original_vpq_quotation_pages"], 2)
        self.assertEqual(r["vpq_original_invoice_faces"], 2)
        self.assertEqual(r["same_pdf_exact_quotation_id_invoice_joins"], 2)
        self.assertEqual(r["invoice_dates_within_printed_quote_effective_window"], 2)
        self.assertEqual(r["printed_invoice_quoted_weights_agree"], 2)
        self.assertEqual(r["invoice_amount_equals_printed_quote_minimum"], 1)
        self.assertEqual(r["conditional_printed_length_formula_matches"], 1)
        self.assertEqual(r["invoice_quote_money_unresolved"], 0)
        self.assertTrue(r["quote_and_invoice_documents_are_co_bundled_in_same_source_pdf"])
        self.assertFalse(r["conditional_length_footage_is_independently_certified"])
        for name in ("original_signed_bol_quotes_independently_verified",
                     "separate_quote_acceptance_independently_verified",
                     "independent_customer_invoice_overcharge_labels",
                     "bank_cleared_payments_verified",
                     "verified_retally_recovered_cash_cents",
                     "raw_invoice_quote_bol_identifiers_exported",
                     "customer_contact_actions"):
            self.assertEqual(r[name], 0, name)
        import json
        public = json.dumps(r)
        for forbidden in ("SAMPLEQ101", "SAMPLEQ202", "352112867", "051894063",
                          "2,610", "12,573", "2132.83"):
            self.assertNotIn(forbidden, public)
        self.assertEqual(r, arcbest_embedded_vpq_quote_reconciliation(
            faces, text, sha))

    def test_embedded_quote_join_rejects_false_identity_or_inferred_footage(self):
        invoice = (
            "ORIGINAL INVOICE\nFreight Bill No: 352112867\n"
            "Tariff: VPQ\nPQ SCHEDULE NO: SAMPLEQ101A\n"
            "ITEM 028160-01V 2,610 PPU 2,132.83\n"
        )
        quote = (
            "Volume Pricing Quotation\n"
            "Effective Date: 10-MAY-2024\nExpiration Date: 23-MAY-2024\n"
            "VPQ Quotation ID: SAMPLEQ101-A\nWeight: 2,610 lbs\n"
            "Minimum price including Fuel Surcharge* "
            "(max 14,450 lbs/17 linear ft): $ 2132.83\n"
            "*Charge per additional linear foot: $ 125.00\n"
        )
        correct = InvoiceFace("arcbest", "352112867", 1, 213283,
                              None, "2024-05-13", "LTL")
        digest = FROZEN_DOCUMENT_SHA256["arcbest"]
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256_MISMATCH"):
            arcbest_embedded_vpq_quote_reconciliation([correct], [invoice, quote], "0"*64)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_INVOICE"):
            arcbest_embedded_vpq_quote_reconciliation(
                [correct, correct], [invoice, quote], digest)
        changed = invoice.replace("SAMPLEQ101A", "DIFFERENTQUOTE")
        m = arcbest_embedded_vpq_quote_reconciliation(
            [correct], [changed, quote], digest)
        self.assertEqual(m["same_pdf_exact_quotation_id_invoice_joins"], 0)
        self.assertEqual(m["invoice_quote_money_unresolved"], 1)
        dated = InvoiceFace("arcbest", "352112867", 1, 213283,
                            None, "2024-06-13", "LTL")
        m = arcbest_embedded_vpq_quote_reconciliation(
            [dated], [invoice, quote], digest)
        self.assertEqual(m["invoice_dates_within_printed_quote_effective_window"], 0)
        self.assertEqual(m["invoice_quote_money_unresolved"], 1)
        one_cent = InvoiceFace("arcbest", "352112867", 1, 213284,
                               None, "2024-05-13", "LTL")
        m = arcbest_embedded_vpq_quote_reconciliation(
            [one_cent], [invoice, quote], digest)
        self.assertEqual(m["invoice_amount_equals_printed_quote_minimum"], 0)
        self.assertEqual(m["invoice_quote_money_unresolved"], 1)
        duplicate_quote = [invoice, quote, quote]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_QUOTE_ID"):
            arcbest_embedded_vpq_quote_reconciliation(
                [correct], duplicate_quote, digest)


    def test_co_bundled_truckload_bol_copies_match_both_source_invoices_but_conflict(self):
        """Two shipments, four BOL first-pages: different piece totals on one."""
        def invoice(pro, load, amount, printed_pieces, pounds, ship_date):
            return (
                f"ORIGINAL INVOICE\nService: Truckload\nFreight bill No: {pro}\n"
                f"Shipment Date: {ship_date}\nAMOUNT DUE: $ {amount:.2f}\n"
                f"CRN: 4001454894\nCRN: {load}\n"
                "Total Pieces Total Weight TOTAL AMOUNT\n"
                f"$" f"{amount:,.2f} {printed_pieces} {pounds:,}\n"
            )

        def bol(pro, load, pieces, pounds, pickup):
            return (
                f"Motor Carrier Bill of Lading\nLoad #: {load}\n"
                f"Order References: ArcBest Pronumber: {pro}\n"
                "Stop 1 - Pick Up\n"
                f"SYNTHETIC SHIPPER Date: {pickup} - {pickup}\n"
                "Total HU: 10 Total Pcs: "
                f"{pieces} Total Cmdty: 1 Total Wgt: {pounds} lbs\n"
                "Stop 2 - Delivery\n"
                "Shipper Signature / Date\nConsignee Signature/Date\n"
            )

        a, b = "123456789", "987654321"
        load_a, load_b = "6001438260", "6001488729"
        pages = [
            invoice(a, load_a, 2950, 0, 11993, "05/01/2024"),
            invoice(b, load_b, 3200, 225, 11050, "05/31/2024"),
            bol(a, load_a, 0, 11993, "5/1/2024"),
            bol(b, load_b, 30, 11050, "5/31/2024"),
            bol(b, load_b, 225, 11050, "5/31/2024"),
            bol(b, load_b, 225, 11050, "5/31/2024"),
        ]
        faces = [
            InvoiceFace("arcbest", a, 1, 295000, None, "2024-05-01", "TL"),
            InvoiceFace("arcbest", b, 2, 320000, None, "2024-05-31", "TL"),
        ]
        sha = FROZEN_DOCUMENT_SHA256["arcbest"]
        r = arcbest_embedded_truckload_bol_reconciliation(faces, pages, sha)
        self.assertEqual(r["original_truckload_invoice_faces"], 2)
        self.assertEqual(r["co_bundled_motor_carrier_bol_first_pages"], 4)
        self.assertEqual(r["co_bundled_bol_pages_bound_to_source_invoice"], 4)
        self.assertEqual(r["source_invoice_load_reference_matching_bol_pages"], 4)
        self.assertEqual(r["source_invoice_bol_totals_readable_pages"], 4)
        self.assertEqual(r["source_invoice_printed_weight_matches_on_bol_copies"], 4)
        self.assertEqual(r["source_invoice_pickup_date_matches_on_bol_copies"], 4)
        self.assertEqual(r["pickup_extraction_state_counts"],
                         {"PICKUP_DATE_MATCHES_INVOICE": 4})
        self.assertEqual(r["bol_header_vs_pickup_date_state_counts"],
                         {"BOL_HEADER_DATE_NOT_READABLE": 4})
        self.assertEqual(r["unique_truckload_invoices_with_co_bundled_bol_copies"], 2)
        self.assertEqual(r["duplicate_co_bundled_bol_copy_pages_not_new_shipments"], 2)
        self.assertEqual(r["repeated_load_groups_with_piece_count_disagreements"], 1)
        self.assertEqual(r["repeated_load_groups_with_weight_disagreements"], 0)
        self.assertEqual(r["repeated_load_groups_total"], 1)
        for field in ("independently_authenticated_signed_bol_acceptances",
                      "independent_custody_original_bol_verified",
                      "customer_rate_authority_verified",
                      "actual_delivery_proof_independently_verified",
                      "bank_cleared_payment_verified",
                      "independently_adjudicated_customer_overcharges",
                      "verified_retally_cash_recovered_cents",
                      "original_source_customer_or_load_identifiers_exported",
                      "external_contact_actions"):
            self.assertEqual(r[field], 0, field)
        self.assertFalse(r["commercial_reuse_authorized"])
        self.assertEqual(r["unresolved_reason_counts"], {})
        import json
        summary = json.dumps(r)
        for secret in (a, b, load_a, load_b, "SYNTHETIC SHIPPER", "Stop 1"):
            self.assertNotIn(secret, summary)
        self.assertEqual(r, arcbest_embedded_truckload_bol_reconciliation(faces, pages, sha))

    def test_bol_invoice_crosslink_detects_wrong_load_weight_and_pickup_day(self):
        sha = FROZEN_DOCUMENT_SHA256["arcbest"]
        invoice = (
            "ORIGINAL INVOICE\nFreight bill No: 123456789\n"
            "Total Pieces Total Weight TOTAL AMOUNT\n$2,950.00 0 11,993\n"
            "CRN: 6001438260\n"
        )
        face = InvoiceFace("arcbest", "123456789", 1, 295000,
                           None, "2024-05-01", "TL")
        bol = (
            "Motor Carrier Bill of Lading\nLoad #: 6001438260\n"
            "Order References: ArcBest Pronumber: 123456789\n"
            "Stop 1 - Pick Up\nSYNTHETIC Date: 5/1/2024 - 5/1/2024\n"
            "Total HU: 15 Total Pcs: 0 Total Cmdty: 1 Total Wgt: 11993 lbs\n"
            "Stop 2 - Delivery\n"
        )
        correct = arcbest_embedded_truckload_bol_reconciliation(
            [face], [invoice, bol], sha)
        self.assertEqual(correct["source_invoice_printed_weight_matches_on_bol_copies"], 1)
        self.assertEqual(correct["pickup_extraction_state_counts"],
                         {"PICKUP_DATE_MATCHES_INVOICE": 1})
        for edited, expected in (
            (bol.replace("6001438260", "6001488729"),
             "BOL_LOAD_REFERENCE_NOT_ON_INVOICE"),
            (bol.replace("11993", "11994"),
             "BOL_INVOICE_PRINTED_WEIGHT_CONFLICT"),
            (bol.replace("5/1/2024", "5/2/2024"),
             "BOL_PICKUP_INVOICE_DATE_CONFLICT"),
        ):
            with self.subTest(expected=expected):
                result = arcbest_embedded_truckload_bol_reconciliation(
                    [face], [invoice, edited], sha)
                self.assertEqual(result["unresolved_reason_counts"][expected], 1)
                if expected == "BOL_PICKUP_INVOICE_DATE_CONFLICT":
                    self.assertEqual(result["pickup_extraction_state_counts"], {
                        "EXPLICIT_PICKUP_DATE_DIFFERS_FROM_INVOICE": 1})
                self.assertEqual(result["independently_adjudicated_customer_overcharges"], 0)
        # The initial carrier BOL "Date" is the document date, not the
        # stop-1 pickup date. A date created a day before loading is allowed.
        header = bol.replace("Motor Carrier Bill of Lading\n",
                             "Motor Carrier Bill of Lading\nDate: 4/30/2024\n")
        r = arcbest_embedded_truckload_bol_reconciliation(
            [face], [invoice, header], sha)
        self.assertEqual(r["source_invoice_pickup_date_matches_on_bol_copies"], 1)
        self.assertEqual(r["bol_header_vs_pickup_date_state_counts"],
                         {"DOCUMENT_HEADER_DATE_DIFFERS_FROM_PICKUP": 1})
        self.assertEqual(r["pickup_extraction_state_counts"],
                         {"PICKUP_DATE_MATCHES_INVOICE": 1})

        missing_delimiter = bol.replace("Stop 2 - Delivery", "Delivery Stop 2")
        r = arcbest_embedded_truckload_bol_reconciliation(
            [face], [invoice, missing_delimiter], sha)
        self.assertEqual(r["source_invoice_pickup_date_matches_on_bol_copies"], 0)
        self.assertEqual(r["pickup_extraction_state_counts"],
                         {"DELIVERY_BOUNDARY_ABSENT": 1})
        self.assertEqual(r["unresolved_reason_counts"],
                         {"BOL_PICKUP_INVOICE_DATE_CONFLICT": 1})

        # Matching freight-bill number but a wrong CRN load ID is NOT a
        # linked shipment and must not enter unique-load denominators.
        wrong_load = bol.replace("6001438260", "6001488729")
        r = arcbest_embedded_truckload_bol_reconciliation(
            [face], [invoice, wrong_load], sha)
        self.assertEqual(r["unique_truckload_invoices_with_co_bundled_bol_copies"], 0)
        self.assertEqual(r["source_invoice_load_reference_matching_bol_pages"], 0)
        self.assertEqual(r["unresolved_reason_counts"],
                         {"BOL_LOAD_REFERENCE_NOT_ON_INVOICE": 1})

        with self.assertRaisesRegex(ValueError, "SOURCE_SHA256_MISMATCH"):
            arcbest_embedded_truckload_bol_reconciliation(
                [face], [invoice, bol], "0" * 64)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_INVOICE_FACE"):
            arcbest_embedded_truckload_bol_reconciliation(
                [face, face], [invoice, bol], sha)
        wrong_page = bol.replace("123456789", "000000001")
        result = arcbest_embedded_truckload_bol_reconciliation(
            [face], [invoice, wrong_page], sha)
        self.assertEqual(
            result["unresolved_reason_counts"]["BOL_NOT_LINKED_TO_TL_INVOICE_FACE"], 1)
        self.assertEqual(result["unique_truckload_invoices_with_co_bundled_bol_copies"], 0)

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
        self.assertEqual(report["canonical_invoice_records_with_exact_source_net"], 2)
        self.assertEqual(report["canonical_v2_adjustment_records_with_exact_source_net"], 1)
        self.assertEqual(report["canonical_v1_charge_only_records_with_exact_source_net"], 1)
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
