"""Offline adversarial contracts for the real-document lab; no network required."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from freight.ingestion_gateway import IngressEnvelope, ingest_bytes
from freight.real_document_lab import (
    _arcbest_page, _global_page, _recon_result, blind_freight_assessment,
    fetch_public, iso_date, minor, parse_pennine_csv, statement_rows,
    reference_scoped_replay, InvoiceFace, _rating_probe, survey_historical_adjudications,
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

    def test_native_pdf_ingress_is_not_pdf_extraction(self):
        receipt = ingest_bytes(
            IngressEnvelope("test", "research", "ephemeral", "BATCH", "document.pdf"),
            b"%PDF-1.4\n% test PDF envelope",
        )
        self.assertEqual(receipt.route, "DOCUMENT_EXTRACTION_REQUIRED")
        self.assertEqual(receipt.status, "ACCEPT")

    def test_blinded_freight_does_not_invent_labels(self):
        result = blind_freight_assessment({
            "globaltranz": {"distinct_invoice_face_ids": 100},
            "arcbest": {"distinct_invoice_face_ids": 10},
        })
        self.assertEqual(result["unknown_cases_preserved"], 110)
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["freight_detection_accuracy"])
        self.assertEqual(result["validated_recovery_cents"], 0)


if __name__ == "__main__":
    unittest.main()
