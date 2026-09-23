import json
from pathlib import Path
import tempfile
import unittest

from recoveryworks.cli import main
from recoveryworks.private_io import private_permissions_verified


class Scan360CliTests(unittest.TestCase):
    def test_cli_writes_private_state_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Payments.csv").write_text(
                "Payment_Number,Vendor,Invoice_Number,Amount,Payment_Date\n"
                "P-1,V,INV-1,100.00,2026-08-01\n"
                "P-2,V,INV-1-DUP,100.00,2026-08-02\n",
                encoding="utf-8",
            )
            (root / "AP_Invoices.csv").write_text(
                "Vendor,Invoice_Number,Amount,Invoice_Date\n"
                "V,INV-1,100.00,2026-07-01\n",
                encoding="utf-8",
            )
            config = root / "scan.json"
            config.write_text(json.dumps({
                "client_id": "client",
                "ap": {
                    "payments_csv": "Payments.csv",
                    "obligations_csv": "AP_Invoices.csv",
                    "default_effective_from": "2026-01-01",
                    "payment_source_verified": True,
                    "obligation_source_verified": True,
                },
            }), encoding="utf-8")
            state = root / "private" / "state.json"
            report = root / "private" / "report.json"

            rc = main([
                "--config", str(config),
                "--state", str(state),
                "--report", str(report),
            ])

            self.assertEqual(rc, 0)
            self.assertTrue(state.exists())
            self.assertTrue(report.exists())
            payload = json.loads(report.read_text())
            self.assertEqual(payload["report"]["totals"]["validated_cents"], 10000)
            self.assertTrue(private_permissions_verified(state))
            self.assertTrue(private_permissions_verified(report))


if __name__ == "__main__":
    unittest.main()
