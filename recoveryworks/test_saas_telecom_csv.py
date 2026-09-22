from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.contract_billing_csv import (
    load_contract_rates_csv,
    load_invoice_charges_csv,
    load_usage_csv,
)
from recoveryworks.branches.saas import audit_saas_billing
from recoveryworks.branches.saas_csv import load_billable_seat_snapshot_csv
from recoveryworks.branches.telecom import audit_telecom_billing
from recoveryworks.branches.telecom_csv import load_cdr_usage_csv


class SaaSTelecomCsvTests(unittest.TestCase):
    def test_saas_seat_snapshot_aggregates_billable_seats(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Seats.csv"
            path.write_text(
                "Charge_ID,Seat_ID,Billable\n"
                "C-1,S-1,true\n"
                "C-1,S-2,true\n"
                "C-1,S-3,false\n",
                encoding="utf-8",
            )
            usage = load_billable_seat_snapshot_csv(path, verified=True)
            self.assertEqual(len(usage), 1)
            self.assertEqual(usage[0].units, "2")
            self.assertEqual(usage[0].metadata["billable_seat_count"], 2)
            self.assertTrue(usage[0].source_hash)

    def test_duplicate_saas_seat_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Seats.csv"
            path.write_text(
                "Charge_ID,Seat_ID,Billable\n"
                "C-1,S-1,true\n"
                "C-1,S-1,true\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_billable_seat_snapshot_csv(path)

    def test_telecom_cdrs_aggregate_usage(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CDR.csv"
            path.write_text(
                "Charge_ID,CDR_ID,Usage_Units\n"
                "T-1,R-1,100\n"
                "T-1,R-2,50\n",
                encoding="utf-8",
            )
            usage = load_cdr_usage_csv(path, verified=True)
            self.assertEqual(usage[0].units, "150")
            self.assertEqual(usage[0].metadata["cdr_count"], 2)

    def test_duplicate_cdr_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CDR.csv"
            path.write_text(
                "Charge_ID,CDR_ID,Usage_Units\n"
                "T-1,R-1,100\n"
                "T-1,R-1,50\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_cdr_usage_csv(path)

    def test_generic_files_flow_to_validated_saas_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Vendor,svc,2026-01-01,,10.00,0,2.00\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "C-1,Vendor,A-1,svc,2026-08-31,40.00\n",
                encoding="utf-8",
            )
            (root / "usage.csv").write_text(
                "Charge_ID,Units\nC-1,10\n",
                encoding="utf-8",
            )
            batch = audit_saas_billing(
                client_id="client",
                charges=load_invoice_charges_csv(root / "charges.csv", verified=True),
                rates=load_contract_rates_csv(root / "rates.csv", verified=True),
                usage=load_usage_csv(root / "usage.csv", verified=True),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.potential_recovery_cents, 1000)

    def test_cdr_quantity_flows_to_validated_telecom_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Carrier,voice,2026-01-01,,20.00,100,0.10\n",
                encoding="utf-8",
            )
            (root / "charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "T-1,Carrier,A-1,voice,2026-08-31,30.00\n",
                encoding="utf-8",
            )
            (root / "cdr.csv").write_text(
                "Charge_ID,CDR_ID,Usage_Units\n"
                "T-1,R-1,100\n"
                "T-1,R-2,50\n",
                encoding="utf-8",
            )
            batch = audit_telecom_billing(
                client_id="client",
                charges=load_invoice_charges_csv(root / "charges.csv", verified=True),
                rates=load_contract_rates_csv(root / "rates.csv", verified=True),
                usage=load_cdr_usage_csv(root / "cdr.csv", verified=True),
            )
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.expected_cents, 2500)
            self.assertEqual(finding.potential_recovery_cents, 500)


if __name__ == "__main__":
    unittest.main()
