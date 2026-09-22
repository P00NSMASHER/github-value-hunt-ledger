from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.payer import audit_payer_lines
from recoveryworks.branches.payer_csv import (
    load_payer_lines_csv,
    load_payer_rates_csv,
)


class PayerCsvTests(unittest.TestCase):
    def test_deidentified_exports_flow_to_validated_underpayment(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lines = root / "remittance_lines.csv"
            rates = root / "rates.csv"
            lines.write_text(
                "Line_ID,Claim_Surrogate_ID,Payer,Service_Date,Billed_Procedure,"
                "Paid_Procedure,Units,Paid_Amount,Modifier,Place_Of_Service\n"
                "L1,SUR-1,Payer A,2026-08-01,99214,99213,1,120.00,,11\n",
                encoding="utf-8",
            )
            rates.write_text(
                "Payer,Procedure_Code,Allowed_Amount_Per_Unit,Effective_From,"
                "Effective_To,Modifier,Place_Of_Service\n"
                "Payer A,99214,200.00,2026-01-01,,,,\n",
                encoding="utf-8",
            )
            service_lines = load_payer_lines_csv(lines, verified=True)
            rate_rows = load_payer_rates_csv(
                rates,
                verified=True,
                default_effective_from="2026-01-01",
                jurisdiction="US",
            )
            batch = audit_payer_lines(
                client_id="provider",
                lines=service_lines,
                rates=rate_rows,
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 8000)
            self.assertIn("#row=2", finding.evidence[0].locator)
            self.assertTrue(finding.rule.source_hash)

    def test_phi_column_is_rejected_from_common_ledger_input(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.csv"
            path.write_text(
                "Line_ID,Claim_Surrogate_ID,Payer,Service_Date,Billed_Procedure,"
                "Units,Paid_Amount,Patient_Name\n"
                "L1,SUR-1,Payer A,2026-08-01,99214,1,120.00,Jane Doe\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_payer_lines_csv(path)

    def test_unverified_csvs_cannot_create_validated_dollars(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lines = root / "lines.csv"
            rates = root / "rates.csv"
            lines.write_text(
                "Line_ID,Claim_Surrogate_ID,Payer,Service_Date,Billed_Procedure,"
                "Paid_Procedure,Units,Paid_Amount,Modifier,Place_Of_Service\n"
                "L1,SUR-1,Payer A,2026-08-01,99214,99213,1,120.00,,11\n",
                encoding="utf-8",
            )
            rates.write_text(
                "Payer,Procedure_Code,Allowed_Amount_Per_Unit,Effective_From,"
                "Effective_To,Modifier,Place_Of_Service\n"
                "Payer A,99214,200.00,2026-01-01,,,,\n",
                encoding="utf-8",
            )
            batch = audit_payer_lines(
                client_id="provider",
                lines=load_payer_lines_csv(lines),
                rates=load_payer_rates_csv(
                    rates,
                    default_effective_from="2026-01-01",
                ),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.REVIEW)


if __name__ == "__main__":
    unittest.main()
