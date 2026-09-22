from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.utility import audit_utility_bills
from recoveryworks.branches.utility_io import (
    load_simple_tariff_definitions_json,
    load_utility_bills_csv,
)


class UtilityRealIngestionTests(unittest.TestCase):
    def test_tiered_energy_ingests_and_calculates_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bills = root / "Bills.csv"
            tariffs = root / "tariffs.json"
            bills.write_text(
                "Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,"
                "Billed_kWh,Billed_Demand_kW,Billed_rkVA,Days_Used\n"
                "B-1,Utility A,A-1,SC1,2026-08-31,220.00,1500,0,0,31\n",
                encoding="utf-8",
            )
            tariffs.write_text(
                """{
                  "tariffs": [{
                    "sc_code": "SC1",
                    "effective_date": "2026-01-01",
                    "logic_steps": [
                      {"step_name": "Customer", "charge_type": "fixed_fee", "value": 5},
                      {"step_name": "Energy", "charge_type": "tiered_kwh",
                       "tiers": [
                         {"up_to_kwh": 1000, "rate": 0.10},
                         {"up_to_kwh": null, "rate": 0.20}
                       ]}
                    ]
                  }]
                }""",
                encoding="utf-8",
            )
            loaded_bills = load_utility_bills_csv(bills, verified=True)
            loaded_tariffs = load_simple_tariff_definitions_json(
                tariffs,
                utility_id="Utility A",
                verified=True,
                default_effective_from="2026-01-01",
            )
            batch = audit_utility_bills(
                client_id="client",
                bills=loaded_bills,
                tariffs=loaded_tariffs,
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.expected_cents, 20500)
            self.assertEqual(finding.potential_recovery_cents, 1500)
            tier_trace = finding.metadata["calculation_trace"][1]
            self.assertEqual(tier_trace["tiers"][0]["amount_cents"], 10000)
            self.assertEqual(tier_trace["tiers"][1]["amount_cents"], 10000)

    def test_tou_and_daily_charge_use_real_bill_columns(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bills = root / "Bills.csv"
            tariffs = root / "tariffs.json"
            bills.write_text(
                "Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,"
                "Billed_kWh,Billed_Demand_kW,Billed_rkVA,Days_Used,"
                "Billed_kWh_On_Peak,Billed_kWh_Off_Peak\n"
                "B-1,Utility A,A-1,TOU1,2026-08-31,70.00,300,0,0,30,100,200\n",
                encoding="utf-8",
            )
            tariffs.write_text(
                """[{
                  "sc_code": "TOU1",
                  "effective_date": "2026-01-01",
                  "logic_steps": [
                    {"step_name":"Customer","charge_type":"fixed_fee","value":5},
                    {"step_name":"Daily","charge_type":"daily_fixed_fee","value":0.50},
                    {"step_name":"Peak","charge_type":"tou_kwh","period":"on_peak","value":0.20},
                    {"step_name":"Off Peak","charge_type":"tou_kwh","period":"off_peak","value":0.10}
                  ]
                }]""",
                encoding="utf-8",
            )
            loaded_bills = load_utility_bills_csv(bills, verified=True)
            self.assertEqual(
                loaded_bills[0].normalized_period_quantities,
                {"ON_PEAK": "100", "OFF_PEAK": "200"},
            )
            loaded_tariffs = load_simple_tariff_definitions_json(
                tariffs,
                utility_id="Utility A",
                verified=True,
                default_effective_from="2026-01-01",
            )
            batch = audit_utility_bills(
                client_id="client",
                bills=loaded_bills,
                tariffs=loaded_tariffs,
            )
            self.assertEqual(batch.exceptions, ())
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertEqual(finding.expected_cents, 6000)
            self.assertEqual(finding.potential_recovery_cents, 1000)

    def test_missing_required_tou_quantity_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bills = root / "Bills.csv"
            tariffs = root / "tariffs.json"
            bills.write_text(
                "Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,"
                "Billed_kWh\n"
                "B-1,Utility A,A-1,TOU1,2026-08-31,70.00,300\n",
                encoding="utf-8",
            )
            tariffs.write_text(
                """[{
                  "sc_code":"TOU1",
                  "logic_steps":[
                    {"step_name":"Peak","charge_type":"tou_kwh","period":"on_peak","value":0.20}
                  ]
                }]""",
                encoding="utf-8",
            )
            batch = audit_utility_bills(
                client_id="client",
                bills=load_utility_bills_csv(bills, verified=True),
                tariffs=load_simple_tariff_definitions_json(
                    tariffs,
                    utility_id="Utility A",
                    verified=True,
                    default_effective_from="2026-01-01",
                ),
            )
            self.assertEqual(batch.observations, ())
            self.assertEqual(
                batch.exceptions[0].code,
                "MISSING_OR_INVALID_BILL_QUANTITY",
            )
            self.assertIn("ON_PEAK", batch.exceptions[0].detail)

    def test_tier_schedule_requires_open_ended_final_tier(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tariffs.json"
            path.write_text(
                """[{
                  "sc_code":"SC1",
                  "logic_steps":[{
                    "step_name":"Energy",
                    "charge_type":"tiered_kwh",
                    "tiers":[{"up_to_kwh":1000,"rate":0.10}]
                  }]
                }]""",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_simple_tariff_definitions_json(
                    path,
                    utility_id="Utility A",
                    default_effective_from="2026-01-01",
                )


if __name__ == "__main__":
    unittest.main()
