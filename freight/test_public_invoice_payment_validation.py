"""Synthetic-only controls; no government supplier rows or bank data stored."""
from __future__ import annotations
import csv
import io
import unittest
from freight.research.public_invoice_payment_validation import (
    MAX_SOURCE_BYTES, SourceHold, fetch_official_csv, money_cents, profile_csv,
)

HEADERS = [
    "Supplier Number", "Invoice Number", "Invoice Date", "Invoice Amount",
    "Payment Number", "Payment Date", "Payment Method", "Payment Status Name",
    "Payment Currency", "Supplier", "Invoice Description",
]


def csv_bytes(*records):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=HEADERS)
    writer.writeheader()
    for record in records:
        data = dict(
            zip(HEADERS, [
                "VENDOR-1", "INVOICE-1", "01/06/2026", "1234.56",
                "PAY-1", "01/07/2026", "EFT", "Fully paid", "GBP",
                "TEST VENDOR ONLY", "Synthetic transaction",
            ])
        )
        data.update(record)
        writer.writerow(data)
    return stream.getvalue().encode("utf-8-sig")


class TestPublicInvoicePaymentProfile(unittest.TestCase):
    def test_one_paid_invoice_and_no_cash_truth_claim(self):
        p = profile_csv(csv_bytes({}))
        self.assertEqual(p["source_row_count"], 1)
        self.assertEqual(p["complete_paid_reference_rows"], 1)
        self.assertEqual(p["total_reported_invoice_amount_gbp_cents_for_complete_rows"], 123456)
        self.assertEqual(p["complete_paid_reference_fraction"], 1)
        self.assertFalse(p["original_invoice_document_present"])
        self.assertFalse(p["actual_bank_settlement_independently_verified"])
        self.assertFalse(p["commercial_freight_accuracy_validation_ready"])
        self.assertFalse(p["raw_invoice_rows_persisted"])
        self.assertEqual(p["verified_retally_recovered_cents"], 0)
        self.assertNotIn("TEST VENDOR", str(p))

    def test_one_payment_may_pay_multiple_invoices(self):
        p = profile_csv(csv_bytes(
            {"Invoice Number": "INVOICE-1"},
            {"Invoice Number": "INVOICE-2", "Invoice Amount": "75.20"},
        ))
        self.assertEqual(p["distinct_invoice_keys"], 2)
        self.assertEqual(p["distinct_payment_numbers"], 1)
        self.assertEqual(p["payment_numbers_covering_multiple_invoices"], 1)
        self.assertEqual(p["composite_invoice_key_duplicate_rows"], 0)

    def test_duplicate_invoice_identity_is_reported_not_inferred_recovery(self):
        p = profile_csv(csv_bytes({}, {}))
        self.assertEqual(p["composite_invoice_key_duplicate_rows"], 1)
        self.assertEqual(p["verified_retally_recovered_cents"], 0)

    def test_incomplete_identifiers_do_not_pass_replay(self):
        p = profile_csv(csv_bytes({"Payment Date": ""}))
        self.assertEqual(p["complete_paid_reference_rows"], 0)
        self.assertEqual(p["missing_required_field_counts"]["Payment Date"], 1)

    def test_invalid_amount_and_date_do_not_pass(self):
        p = profile_csv(csv_bytes(
            {"Invoice Amount": "not money"},
            {"Invoice Number": "X2", "Payment Date": "invalid"},
            {"Invoice Number": "X3", "Payment Date": "01/01/2026"},
        ))
        self.assertEqual(p["invalid_amount_rows"], 1)
        self.assertEqual(p["invalid_date_rows"], 1)
        self.assertEqual(p["payment_precedes_invoice_rows"], 1)
        self.assertEqual(p["complete_paid_reference_rows"], 0)

    def test_unpaid_and_foreign_currency_records_not_promoted(self):
        p = profile_csv(csv_bytes(
            {"Payment Status Name": "Pending"},
            {"Invoice Number": "X2", "Payment Currency": "USD"},
        ))
        self.assertEqual(p["complete_paid_reference_rows"], 0)

    def test_currency_values_cannot_be_rounded_from_excess_precision(self):
        self.assertEqual(money_cents("£1,234.56"), 123456)
        self.assertEqual(money_cents("-12.50"), -1250)
        for bad in ("20.999", "NaN", "20x", "", "true"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                money_cents(bad)

    def test_non_csv_is_held(self):
        with self.assertRaisesRegex(SourceHold, "NOT_CSV_CONTENT"):
            profile_csv(b"<html><body>not a CSV file</body></html>")

    def test_oversized_source_is_held(self):
        with self.assertRaisesRegex(SourceHold, "SOURCE_SIZE_HOLD"):
            profile_csv(b"x" * (MAX_SOURCE_BYTES + 1))


    def test_report_title_preamble_is_not_mistaken_for_header(self):
        preamble = "RT2N0012 - AP Invoices over 25K,,,,,,,,,,,,,,,\n" + (
            ",,,,,,,,,,,,,,,\n"
        )
        record = csv_bytes({}).decode("utf-8-sig")
        p = profile_csv((preamble + record).encode("utf-8"))
        self.assertEqual(p["source_row_count"], 1)
        self.assertEqual(p["complete_paid_reference_rows"], 1)
        self.assertEqual(p["preamble_rows_before_header"], 2)

    def test_duplicate_invoice_cross_month_is_reported_not_assumed_recovery(self):
        seen = set()
        april = profile_csv(csv_bytes({}), cross_period_keys=seen)
        may = profile_csv(csv_bytes({}), cross_period_keys=seen)
        self.assertEqual(april["cross_period_duplicate_invoice_rows"], 0)
        self.assertEqual(may["cross_period_duplicate_invoice_rows"], 1)
        self.assertEqual(len(seen), 1)
        self.assertEqual(may["verified_retally_recovered_cents"], 0)

    def test_different_months_new_invoices_not_marked_duplicate(self):
        seen = set()
        april = profile_csv(csv_bytes({"Invoice Number": "INV-APR"}), cross_period_keys=seen)
        may = profile_csv(csv_bytes({"Invoice Number": "INV-MAY"}), cross_period_keys=seen)
        self.assertEqual(april["cross_period_duplicate_invoice_rows"], 0)
        self.assertEqual(may["cross_period_duplicate_invoice_rows"], 0)
        self.assertEqual(len(seen), 2)


    def test_cross_period_same_invoice_same_payment_does_not_double_count_value(self):
        seen = set()
        history = {}
        profile_csv(csv_bytes({}), source_month="2026-06",
                    cross_period_keys=seen, cross_period_history=history)
        later = profile_csv(csv_bytes({}), source_month="2026-07",
                            cross_period_keys=seen, cross_period_history=history)
        self.assertEqual(later["cross_period_duplicate_invoice_rows"], 1)
        self.assertEqual(later["repeat_invoice_same_payment_reference"], 1)
        self.assertEqual(later["repeat_invoice_same_reported_invoice_amount"], 1)
        self.assertEqual(later["unique_cross_period_invoice_amount_gbp_cents"], 0)
        self.assertEqual(later["duplicate_prior_period_counts"], {"2026-06": 1})

    def test_same_invoice_different_payment_reference_is_not_claimed_recovery(self):
        history = {}
        profile_csv(csv_bytes({}), source_month="2026-06", cross_period_history=history)
        later = profile_csv(csv_bytes({"Payment Number": "PAY-2"}),
                            source_month="2026-07", cross_period_history=history)
        self.assertEqual(later["repeat_invoice_different_payment_reference"], 1)
        self.assertEqual(later["verified_retally_recovered_cents"], 0)

    def test_source_month_validates_payment_date_coverage(self):
        result = profile_csv(csv_bytes({}), source_month="2026-04")
        self.assertEqual(result["payment_dates_outside_named_report_month"], 1)
        self.assertEqual(result["source_payment_date_min"], "2026-07-01")
        self.assertEqual(result["source_payment_date_max"], "2026-07-01")

    def test_pinned_url_guard_blocks_arbitrary_network_calls(self):
        with self.assertRaisesRegex(SourceHold, "SOURCE_NOT_PINNED"):
            fetch_official_csv("https://example.net/secret")


if __name__ == "__main__":
    unittest.main()
