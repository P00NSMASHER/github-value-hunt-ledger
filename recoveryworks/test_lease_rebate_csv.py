from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.lease import audit_lease_billing
from recoveryworks.branches.lease_csv import load_lease_area_csv
from recoveryworks.branches.contract_billing_csv import (
    load_contract_rates_csv,
    load_invoice_charges_csv,
)
from recoveryworks.branches.rebate import audit_rebates
from recoveryworks.branches.rebate_csv import (
    load_rebate_activity_csv,
    load_rebate_agreements_csv,
    load_rebate_credits_csv,
)


class LeaseRebateCsvTests(unittest.TestCase):
    def test_lease_csv_sources_flow_to_validated_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Landlord A,CAM-2026,2026-01-01,,1000.00,0,2.50\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "L-1,Landlord A,SITE-1,CAM-2026,2026-08-31,1400.00\n",
                encoding="utf-8",
            )
            (root / "area.csv").write_text(
                "Charge_ID,Area_SqFt\n"
                "L-1,100\n",
                encoding="utf-8",
            )
            batch = audit_lease_billing(
                client_id="client",
                charges=load_invoice_charges_csv(root / "charges.csv", verified=True),
                rates=load_contract_rates_csv(root / "rates.csv", verified=True),
                area=load_lease_area_csv(root / "area.csv", verified=True),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 15000)
            self.assertIn("#row=2", finding.evidence[1].locator)

    def test_rebate_csv_supports_verified_zero_credit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "agreements.csv").write_text(
                "Agreement_ID,Vendor,Basis,Effective_From,Effective_To,"
                "Threshold_Amount,Threshold_Units,Rate_BPS,Rate_Per_Unit,Fixed_Bonus\n"
                "AGR-1,Vendor A,spend_bps,2026-01-01,,50000,,200,,500.00\n",
                encoding="utf-8",
            )
            (root / "activity.csv").write_text(
                "Agreement_ID,Period_ID,Period_End,Eligible_Spend,Eligible_Units\n"
                "AGR-1,2026-Q3,2026-09-30,100000,\n",
                encoding="utf-8",
            )
            (root / "credits.csv").write_text(
                "Credit_ID,Agreement_ID,Period_ID,Amount\n"
                "CR-0,AGR-1,2026-Q3,0\n",
                encoding="utf-8",
            )
            batch = audit_rebates(
                client_id="client",
                agreements=load_rebate_agreements_csv(
                    root / "agreements.csv", verified=True
                ),
                activities=load_rebate_activity_csv(
                    root / "activity.csv", verified=True
                ),
                credits=load_rebate_credits_csv(
                    root / "credits.csv", verified=True
                ),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 250000)
            self.assertTrue(all(ref.source_hash for ref in finding.evidence))


if __name__ == "__main__":
    unittest.main()
