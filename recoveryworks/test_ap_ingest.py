from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.ap import APObligation, APPayment, build_ap_observations
from recoveryworks.branches.ap_ingest import ingest_ap_exports


def p(payment_id, amount, *, invoice="INV-1", locator="row"):
    return APPayment(
        payment_id=payment_id,
        vendor_id="Vendor A",
        invoice_number=invoice,
        amount_cents=amount,
        source_hash="same-export-hash",
        source_locator=f"file://payments.csv#{locator}",
        verified=True,
        payment_date="2026-08-01",
    )


def o(amount=10000):
    return APObligation(
        vendor_id="Vendor A",
        invoice_number="INV-1",
        expected_cents=amount,
        source_hash="invoice-export-hash",
        source_locator="file://invoices.csv#row=2",
        effective_from="2026-07-01",
        verified=True,
    )


class APIngestTests(unittest.TestCase):
    def test_repeated_identical_export_row_does_not_create_recovery(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                p("PAY-1", 10000, locator="row=2"),
                p("PAY-1", 10000, locator="row=3"),
            ),
            obligations=(o(),),
        )
        self.assertEqual(observations, ())

    def test_conflicting_repeated_payment_line_fails_closed(self):
        with self.assertRaises(ValueError):
            build_ap_observations(
                client_id="client",
                payments=(
                    p("PAY-1", 10000, locator="row=2"),
                    p("PAY-1", 12000, locator="row=3"),
                ),
                obligations=(o(),),
            )

    def test_same_payment_number_across_different_invoices_is_not_globally_deduped(self):
        observations = build_ap_observations(
            client_id="client",
            payments=(
                p("ACH-1", 10000, invoice="INV-1"),
                p("ACH-1", 20000, invoice="INV-2"),
            ),
            obligations=(
                o(10000),
                APObligation(
                    vendor_id="Vendor A",
                    invoice_number="INV-2",
                    expected_cents=20000,
                    source_hash="invoice-export-hash",
                    source_locator="file://invoices.csv#row=3",
                    effective_from="2026-07-01",
                    verified=True,
                ),
            ),
        )
        self.assertEqual(observations, ())

    def test_file_to_frozen_scan_is_deterministic_and_validated_when_verified(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            payments = root / "Payments.csv"
            invoices = root / "AP_Invoices.csv"
            payments.write_text(
                "Payment_Number,Vendor,Invoice_Number,Amount,Payment_Date\n"
                "P-1,Vendor A,INV-1,100.00,2026-08-01\n"
                "P-2,Vendor A,INV-1-DUP,100.00,2026-08-02\n",
                encoding="utf-8",
            )
            invoices.write_text(
                "Vendor,Invoice_Number,Amount,Invoice_Date\n"
                "Vendor A,INV-1,100.00,2026-07-15\n",
                encoding="utf-8",
            )

            first = ingest_ap_exports(
                client_id="client-1",
                payments_path=payments,
                obligations_path=invoices,
                verified_payments=True,
                verified_obligations=True,
                default_effective_from="2026-01-01",
            )
            second = ingest_ap_exports(
                client_id="client-1",
                payments_path=payments,
                obligations_path=invoices,
                verified_payments=True,
                verified_obligations=True,
                default_effective_from="2026-01-01",
            )

            self.assertEqual(first.scan.manifest.manifest_hash, second.scan.manifest.manifest_hash)
            self.assertEqual(first.scan.batch_hash, second.scan.batch_hash)
            self.assertEqual(len(first.scan.manifest.sources), 2)
            self.assertEqual(first.payment_count, 2)
            self.assertEqual(first.obligation_count, 1)
            self.assertEqual(len(first.scan.findings), 1)
            self.assertIs(first.scan.findings[0].state, FindingState.VALIDATED)
            self.assertEqual(first.scan.findings[0].potential_recovery_cents, 10000)


if __name__ == "__main__":
    unittest.main()
