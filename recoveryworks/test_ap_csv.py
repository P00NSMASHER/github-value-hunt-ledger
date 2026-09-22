from pathlib import Path
import tempfile
import unittest

from recoveryworks.ap_csv import (
    execute_ap_csv_scan,
    load_ap_invoices_csv,
    money_to_cents,
)


INVOICES = """vendor_id,invoice_id,invoice_date,amount,currency
Vendor A,INV-1,2026-06-01,100.00,USD
"""

PAYMENTS = """vendor_id,invoice_id,payment_id,payment_date,amount,currency,posted
Vendor A,INV-1,PAY-1,2026-06-05,75.00,USD,true
Vendor A,INV-1,PAY-2,2026-06-06,75.00,USD,true
"""


class APCSVIntakeTests(unittest.TestCase):
    def test_money_parser_never_silently_rounds_subcent_values(self):
        self.assertEqual(money_to_cents("1,234.56"), 123456)
        with self.assertRaises(ValueError):
            money_to_cents("1.005")

    def test_file_hash_and_row_locator_are_generated_by_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invoices.csv"
            path.write_text(INVOICES, encoding="utf-8")
            invoices, source_hash = load_ap_invoices_csv(path, verified=True)
            self.assertEqual(len(source_hash), 64)
            self.assertEqual(invoices[0].source_hash, source_hash)
            self.assertIn("#row=2", invoices[0].locator)

    def test_verified_csv_exports_produce_validated_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            invoices = Path(tmp) / "invoices.csv"
            payments = Path(tmp) / "payments.csv"
            invoices.write_text(INVOICES, encoding="utf-8")
            payments.write_text(PAYMENTS, encoding="utf-8")
            result, ledger = execute_ap_csv_scan(
                scan_id="ap-csv-1",
                client_id="client-1",
                invoices_path=invoices,
                payments_path=payments,
                invoices_verified=True,
                payments_verified=True,
            )
            self.assertEqual(result["portfolio"]["totals"]["potential_cents"], 5000)
            self.assertEqual(result["portfolio"]["totals"]["validated_cents"], 5000)
            self.assertEqual(ledger.rollup()["totals"]["cases"], 1)

    def test_unverified_file_cannot_create_validated_dollars(self):
        with tempfile.TemporaryDirectory() as tmp:
            invoices = Path(tmp) / "invoices.csv"
            payments = Path(tmp) / "payments.csv"
            invoices.write_text(INVOICES, encoding="utf-8")
            payments.write_text(PAYMENTS, encoding="utf-8")
            result, _ = execute_ap_csv_scan(
                scan_id="ap-csv-2",
                client_id="client-1",
                invoices_path=invoices,
                payments_path=payments,
                invoices_verified=True,
                payments_verified=False,
            )
            self.assertEqual(result["portfolio"]["totals"]["validated_cents"], 0)
            self.assertEqual(result["findings"][0]["case_state"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
