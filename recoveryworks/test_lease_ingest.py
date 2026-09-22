from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState
from recoveryworks.branches.lease_ingest import ingest_lease_exports


class LeaseIngestionTests(unittest.TestCase):
    def test_lease_exports_freeze_reproducible_validated_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rates = root / "rates.csv"
            charges = root / "charges.csv"
            area = root / "area.csv"

            rates.write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Landlord A,CAM-2026,2026-01-01,,1000.00,0,2.50\n",
                encoding="utf-8",
            )
            charges.write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "L-1,Landlord A,SITE-1,CAM-2026,2026-08-31,1400.00\n",
                encoding="utf-8",
            )
            area.write_text(
                "Charge_ID,Area_SqFt\n"
                "L-1,100\n",
                encoding="utf-8",
            )

            first = ingest_lease_exports(
                client_id="client",
                charges_path=charges,
                rates_path=rates,
                area_path=area,
                verified_charges=True,
                verified_rates=True,
                verified_area=True,
            )
            second = ingest_lease_exports(
                client_id="client",
                charges_path=charges,
                rates_path=rates,
                area_path=area,
                verified_charges=True,
                verified_rates=True,
                verified_area=True,
            )

            self.assertEqual(first.scan.batch_hash, second.scan.batch_hash)
            self.assertEqual(first.scan.manifest.manifest_hash, second.scan.manifest.manifest_hash)
            self.assertEqual(first.charge_count, 1)
            self.assertEqual(first.rate_count, 1)
            self.assertEqual(first.quantity_count, 1)
            self.assertEqual(len(first.scan.findings), 1)
            self.assertIs(first.scan.findings[0].state, FindingState.VALIDATED)
            self.assertEqual(first.scan.findings[0].potential_recovery_cents, 15000)
            self.assertEqual(len(first.scan.manifest.sources), 3)

    def test_fixed_only_lease_does_not_require_area_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Landlord A,BASE,2026-01-01,,1000.00,0,0\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "L-1,Landlord A,SITE-1,BASE,2026-08-31,1100.00\n",
                encoding="utf-8",
            )
            result = ingest_lease_exports(
                client_id="client",
                charges_path=root / "charges.csv",
                rates_path=root / "rates.csv",
                verified_charges=True,
                verified_rates=True,
            )
            self.assertEqual(result.audit.exceptions, ())
            self.assertEqual(result.scan.findings[0].potential_recovery_cents, 10000)


if __name__ == "__main__":
    unittest.main()
