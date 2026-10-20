"""Synthetic regression controls; never store Pennine, GlobalTranz or ArcBest rows."""
import csv
import io
import unittest

from freight.research.real_document_engine_lab import (
    _extract_text_invoice, _is_text_amount, _pennine_population,
    benchmark_accounting, blind_score, historical_references,
    PROOF_KEYS,
)

HEADERS = [
    "Supplier Number", "Invoice Number", "Invoice Date", "Invoice Amount",
    "Payment Number", "Payment Date", "Payment Method", "Payment Status Name",
    "Payment Currency",
]


def fixture(*entries, preamble=False):
    out = io.StringIO(newline="")
    if preamble:
        out.write("Report title,,,,,,,,\n,,,,,,,,\n")
    writer = csv.DictWriter(out, fieldnames=HEADERS)
    writer.writeheader()
    for entry in entries:
        row = dict(zip(HEADERS, ("S-1", "I-1", "01/04/2026", "1,234.56",
                                  "P-1", "08/04/2026", "EFT", "Fully paid", "GBP")))
        row.update(entry)
        writer.writerow(row)
    return out.getvalue().encode("utf-8-sig")


class RealDocumentEngineLabTests(unittest.TestCase):
    def test_ledger_isolation_deduplication_and_kernel_money(self):
        samples = {
            "2026-04": fixture({}),
            "2026-05": fixture({"Invoice Number": "I-2", "Payment Number": "P-1"}),
            "2026-06": fixture({"Invoice Number": "I-3", "Invoice Amount": "-10.50",
                                 "Payment Number": "P-3"}),
            "2026-07": fixture({"Invoice Number": "I-4", "Payment Number": "P-4"}),
            "2026-08": fixture({"Invoice Number": "I-4", "Payment Number": "P-4"},
                                 preamble=True),
        }
        rows, population = _pennine_population(
            lambda url: next(samples[k] for k, v in __import__(
                "freight.research.public_invoice_payment_validation",
                fromlist=["SOURCE_URLS"]).SOURCE_URLS.items() if v == url),
            pinned=False,
        )
        self.assertEqual(population["published_rows"], 5)
        self.assertEqual(population["unique_invoices"], 4)
        self.assertEqual(population["repeated_publication_rows"], 1)
        self.assertEqual(len(rows), 4)
        self.assertNotIn("Supplier", str(population))
        self.assertNotIn("P-1", str(population))
        result = benchmark_accounting(
            lambda url: next(samples[k] for k, v in __import__(
                "freight.research.public_invoice_payment_validation",
                fromlist=["SOURCE_URLS"]).SOURCE_URLS.items() if v == url),
            pinned=False,
        )
        self.assertEqual(result["actual_kernel_money_parse_equal"], 4)
        self.assertEqual(result["actual_kernel_money_parse_checked"], 4)
        self.assertEqual(result["source_identity_propagated_control"]["same_publisher_row_links"], 4)
        self.assertIsNone(result["freight_detection_accuracy"])
        self.assertTrue(result["payment_annotations_are_not_independent_bank_evidence"])
        self.assertEqual(result["verified_customer_recovery_minor"], 0)

    def test_conflicting_repeat_is_hold_not_duplicated_payment(self):
        samples = {
            "2026-04": fixture({}),
            "2026-05": fixture({"Invoice Amount": "2000.00"}),
            "2026-06": fixture({"Invoice Number": "J-1"}),
            "2026-07": fixture({"Invoice Number": "K-1"}),
            "2026-08": fixture({"Invoice Number": "L-1"}),
        }
        from freight.research.public_invoice_payment_validation import SOURCE_URLS, SourceHold
        with self.assertRaisesRegex(SourceHold, "CONFLICTING_REPUBLISHED_INVOICES"):
            _pennine_population(lambda url: next(samples[k] for k, v in SOURCE_URLS.items()
                                                  if v == url), pinned=False)

    def test_blind_scoring_never_forces_unknown_to_negative(self):
        result = historical_references()
        self.assertEqual(result["reference_case_count"], 8)
        self.assertEqual(result["unknown_cases_excluded"], 8)
        self.assertEqual(result["eligible_labeled_cases"], 0)
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["accuracy"])
        self.assertEqual(result["state"], "INSUFFICIENT_INDEPENDENT_FREIGHT_LABELS")

    def test_blind_scores_only_complete_independent_truth(self):
        complete = dict.fromkeys(PROOF_KEYS, True)
        truth = {
            "positive": dict(complete, label="POSITIVE"),
            "negative": dict(complete, label="NEGATIVE"),
            "unknown": dict(complete, label="UNRESOLVED"),
            "missing_bank": dict(complete, label="POSITIVE",
                                 independent_payment_verified=False),
        }
        result = blind_score({"positive": "POSITIVE", "negative": "POSITIVE",
                              "unknown": "NEGATIVE", "missing_bank": "POSITIVE"}, truth)
        self.assertEqual(result["eligible_labeled_cases"], 2)
        self.assertEqual(result["unknown_cases_excluded"], 2)
        self.assertEqual(result["fp"], 1)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 1.0)

    def test_document_text_extraction_is_not_billed_accuracy(self):
        invoice, amount = _extract_text_invoice(
            "Invoice Number: 30794056 Total Amount: $341.08")
        self.assertEqual(invoice, "30794056")
        self.assertEqual(amount, 34108)
        self.assertTrue(_is_text_amount("TOTAL $3,200.00", "3200.00"))
        self.assertEqual(_extract_text_invoice("No source fields"), (None, None))


if __name__ == "__main__":
    unittest.main()
