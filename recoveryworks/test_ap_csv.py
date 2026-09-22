from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.ap import build_ap_observations
from recoveryworks.branches.ap_csv import (
    load_obligations_csv,
    load_payments_csv,
    money_to_cents,
)


class APCsvTests(unittest.TestCase):
    def test_money_parser_is_decimal_safe(self):
        self.assertEqual(money_to_cents("$4,321.00"), 432100)
        self.assertEqual(money_to_cents("10.005"), 1001)
        with self.assertRaises(ValueError):
            money_to_cents("0")

    def test_suffix_normalized_exports_stay_review_without_exact_authority(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            payments_path = root / "Payments.csv"
            invoices_path = root / "AP_Invoices.csv"
            payments_path.write_text(
                "Payment_Number,Vendor,Invoice_Number,Amount,Payment_Date\n"
                "P-1,Vendor A,INV-2001,4321.00,2026-08-01\n"
                "P-2,Vendor A,INV-2001-R,4321.00,2026-08-02\n",
                encoding="utf-8",
            )
            invoices_path.write_text(
                "Vendor,Invoice_Number,Amount,Invoice_Date\n"
                "Vendor A,INV-2001,4321.00,2026-07-20\n",
                encoding="utf-8",
            )

            payments = load_payments_csv(payments_path, verified=True)
            obligations = load_obligations_csv(
                invoices_path,
                verified=True,
                default_effective_from="2026-01-01",
            )
            observations = build_ap_observations(
                client_id="client-1",
                payments=payments,
                obligations=obligations,
            )
            self.assertEqual(len(observations), 1)
            finding = RecoveryEngine().evaluate(observations[0])
            self.assertIs(finding.state, FindingState.REVIEW)
            self.assertEqual(finding.potential_recovery_cents, 432100)
            self.assertEqual(len(finding.evidence), 2)
            self.assertTrue(all(ref.source_hash for ref in finding.evidence))
            self.assertIn("#row=2", finding.evidence[0].locator)

    def test_unverified_csvs_cannot_create_validated_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            payments_path = root / "Payments.csv"
            invoices_path = root / "AP_Invoices.csv"
            payments_path.write_text(
                "Payment_Number,Vendor,Invoice_Number,Amount,Payment_Date\n"
                "P-1,V,INV-1,100.00,2026-08-01\n"
                "P-2,V,INV-1-DUP,100.00,2026-08-02\n",
                encoding="utf-8",
            )
            invoices_path.write_text(
                "Vendor,Invoice_Number,Amount,Invoice_Date\n"
                "V,INV-1,100.00,2026-07-01\n",
                encoding="utf-8",
            )
            obs = build_ap_observations(
                client_id="client",
                payments=load_payments_csv(payments_path),
                obligations=load_obligations_csv(
                    invoices_path,
                    default_effective_from="2026-01-01",
                ),
            )
            finding = RecoveryEngine().evaluate(obs[0])
            self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
