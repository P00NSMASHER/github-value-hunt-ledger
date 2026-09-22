from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState
from recoveryworks.branches.procurement_ingest import ingest_procurement_exports


class ProcurementIngestionTests(unittest.TestCase):
    def test_procurement_exports_freeze_reproducible_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Supplier A,SKU-1,2026-01-01,,0,0,10.00\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "PO-LINE-1,Supplier A,PO-100,SKU-1,2026-08-31,1200.00\n",
                encoding="utf-8",
            )
            (root / "quantities.csv").write_text(
                "Charge_ID,Quantity\n"
                "PO-LINE-1,100\n",
                encoding="utf-8",
            )
            kwargs = dict(
                client_id="client",
                charges_path=root / "charges.csv",
                rates_path=root / "rates.csv",
                quantities_path=root / "quantities.csv",
                verified_charges=True,
                verified_rates=True,
                verified_quantities=True,
            )
            first = ingest_procurement_exports(**kwargs)
            second = ingest_procurement_exports(**kwargs)

            self.assertEqual(first.scan.batch_hash, second.scan.batch_hash)
            self.assertEqual(first.scan.manifest.manifest_hash, second.scan.manifest.manifest_hash)
            self.assertEqual(len(first.scan.findings), 1)
            self.assertIs(first.scan.findings[0].state, FindingState.VALIDATED)
            self.assertEqual(first.scan.findings[0].potential_recovery_cents, 20000)
            self.assertEqual(len(first.scan.manifest.sources), 3)
            self.assertEqual(first.quantity_count, 1)


if __name__ == "__main__":
    unittest.main()
