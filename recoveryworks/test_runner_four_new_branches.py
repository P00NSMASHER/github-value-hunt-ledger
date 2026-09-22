from pathlib import Path
import tempfile
import unittest

from recoveryworks.runner import run_scan360_config


class FourNewBranchesRunnerTests(unittest.TestCase):
    def test_all_four_branches_run_into_one_durable_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            # ParcelRecovery
            (root / "parcel_charges.csv").write_text(
                "Shipment_ID,Invoice_ID,Shipper_ID,Carrier_ID,Ship_Date,Service_Code,"
                "Zone,Billed_Weight,Actual_Total\n"
                "SHIP-1,INV-1,client-1,Carrier A,2026-08-15,GROUND,5,10,30.00\n",
                encoding="utf-8",
            )
            (root / "parcel_assessments.csv").write_text(
                "Assessment_ID,Shipment_ID,Carrier_ID,Ship_Date,Service_Code,Zone,"
                "Billed_Weight,Expected_Total,Rate_Basis,Rate_Snapshot_Date,Rate_Reviewer_ID\n"
                "PA-1,SHIP-1,Carrier A,2026-08-15,GROUND,5,10,22.00,"
                "Reviewed carrier contract,2026-08-01,parcel-reviewer-1\n",
                encoding="utf-8",
            )

            # ProcurementRecovery
            (root / "proc_invoice.csv").write_text(
                "Invoice_Line_ID,Invoice_ID,Purchaser_ID,Supplier_ID,PO_Line_ID,SKU,"
                "Invoice_Date,Invoiced_Quantity,Actual_Line_Amount\n"
                "PL-1,PINV-1,client-1,Supplier A,PO-1-L1,SKU-1,2026-08-15,10,100.00\n",
                encoding="utf-8",
            )
            (root / "proc_authority.csv").write_text(
                "Authority_ID,Supplier_ID,PO_Line_ID,SKU,Effective_From,Effective_To,"
                "Contracted_Unit_Price,Price_Basis\n"
                "AUTH-1,Supplier A,PO-1-L1,SKU-1,2026-01-01,,10.00,Approved PO\n",
                encoding="utf-8",
            )
            (root / "proc_quantity.csv").write_text(
                "Invoice_Line_ID,Approved_Billable_Quantity,Quantity_Basis\n"
                "PL-1,8,Receiving and three-way match\n",
                encoding="utf-8",
            )

            # Warranty/CreditRecovery
            (root / "credit_entitlements.csv").write_text(
                "Entitlement_ID,Client_ID,Supplier_ID,Reference_ID,Credit_Category,"
                "Entitled_Amount,Effective_Date,Entitlement_Basis,Entitlement_Reviewer_ID\n"
                "WC-1,client-1,Supplier B,RMA-77,WARRANTY,100.00,2026-08-01,"
                "Approved warranty claim,credit-reviewer-1\n",
                encoding="utf-8",
            )
            (root / "credit_settlements.csv").write_text(
                "Settlement_ID,Entitlement_ID,Amount_Received,Settlement_Date,Settlement_Kind\n"
                "WCS-1,WC-1,30.00,2026-08-20,CREDIT_MEMO\n",
                encoding="utf-8",
            )

            # Payroll/BenefitBillingRecovery
            (root / "pb_rates.csv").write_text(
                "Counterparty,Service_ID,Effective_From,Effective_To,"
                "Fixed_Fee,Included_Units,Unit_Rate\n"
                "Benefit Carrier,MED-FAMILY,2026-01-01,,10.00,0,2.00\n",
                encoding="utf-8",
            )
            (root / "pb_charges.csv").write_text(
                "Charge_ID,Counterparty,Account_ID,Service_ID,Service_Date,Actual_Amount\n"
                "PB-1,Benefit Carrier,employer-1,MED-FAMILY,2026-08-31,40.00\n",
                encoding="utf-8",
            )
            (root / "pb_units.csv").write_text(
                "Charge_ID,Record_ID,Units\n"
                "PB-1,SURR-1,4\n"
                "PB-1,SURR-2,6\n",
                encoding="utf-8",
            )

            config = {
                "client_id": "client-1",
                "currency": "USD",
                "parcel": {
                    "charges_csv": "parcel_charges.csv",
                    "assessments_csv": "parcel_assessments.csv",
                    "charge_source_verified": True,
                    "assessment_source_verified": True,
                },
                "procurement": {
                    "invoice_lines_csv": "proc_invoice.csv",
                    "authorities_csv": "proc_authority.csv",
                    "quantities_csv": "proc_quantity.csv",
                    "invoice_source_verified": True,
                    "authority_source_verified": True,
                    "quantity_source_verified": True,
                },
                "warranty_credit": {
                    "entitlements_csv": "credit_entitlements.csv",
                    "settlements_csv": "credit_settlements.csv",
                    "entitlement_source_verified": True,
                    "settlement_source_verified": True,
                },
                "payroll_benefit": {
                    "charges_csv": "pb_charges.csv",
                    "rates_csv": "pb_rates.csv",
                    "units_csv": "pb_units.csv",
                    "charge_source_verified": True,
                    "rate_source_verified": True,
                    "unit_source_verified": True,
                },
            }

            state = root / "private" / "ledger.json"
            first = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(first.exceptions, ())
            self.assertEqual(len(first.added_finding_ids), 4)
            self.assertEqual(first.report.totals["validated_cents"], 10800)
            self.assertEqual(first.report.branches["parcel"]["validated_cents"], 800)
            self.assertEqual(
                first.report.branches["procurement"]["validated_cents"], 2000
            )
            self.assertEqual(
                first.report.branches["warranty_credit"]["validated_cents"], 7000
            )
            self.assertEqual(
                first.report.branches["payroll_benefit"]["validated_cents"], 1000
            )

            second = run_scan360_config(config, state_path=state, base_dir=root)
            self.assertEqual(second.added_finding_ids, ())
            self.assertEqual(second.state_head_hash, first.state_head_hash)
            self.assertEqual(second.report.as_dict(), first.report.as_dict())


if __name__ == "__main__":
    unittest.main()
