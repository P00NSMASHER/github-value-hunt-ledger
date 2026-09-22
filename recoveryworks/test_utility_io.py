from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.utility import audit_utility_bills
from recoveryworks.branches.utility_io import (
    dollars_per_unit_to_micros,
    dollars_to_cents,
    load_simple_tariff_definitions_json,
    load_utility_bills_csv,
)


class UtilityIoTests(unittest.TestCase):
    def test_decimal_conversions(self):
        self.assertEqual(dollars_to_cents("12.345"), 1235)
        self.assertEqual(dollars_per_unit_to_micros("0.123456"), 123456)

    def test_csv_and_simple_tariff_json_flow_to_validated_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bills = root / "Bills.csv"
            tariffs = root / "tariffs.json"
            bills.write_text(
                "Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,"
                "Billed_kWh,Billed_Demand_kW,Billed_rkVA\n"
                "B-1,Utility A,A-1,SC2D,2026-07-15,30.00,100,2,0\n",
                encoding="utf-8",
            )
            tariffs.write_text(
                """{
                  "tariffs": [{
                    "sc_code": "SC2D",
                    "effective_date": "2026-01-01",
                    "logic_steps": [
                      {"step_name": "Customer", "charge_type": "fixed_fee", "value": 5},
                      {"step_name": "Energy", "charge_type": "per_kwh", "value": 0.10},
                      {"step_name": "Demand", "charge_type": "per_kw", "value": 5}
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
                jurisdiction="NY",
            )
            batch = audit_utility_bills(
                client_id="client",
                bills=loaded_bills,
                tariffs=loaded_tariffs,
            )
            self.assertEqual(batch.exceptions, ())
            self.assertEqual(len(batch.observations), 1)
            finding = RecoveryEngine().evaluate(batch.observations[0])
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.expected_cents, 2500)
            self.assertEqual(finding.potential_recovery_cents, 500)
            self.assertIn("#row=2", finding.evidence[0].locator)
            self.assertTrue(finding.rule.source_hash)

    def test_conditional_tariff_logic_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tariffs.json"
            path.write_text(
                """[{
                  "sc_code": "SC1",
                  "logic_steps": [{
                    "step_name": "Conditional",
                    "charge_type": "per_kwh",
                    "value": 0.10,
                    "condition": "user.billed_kwh > 100"
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

    def test_formula_tariff_logic_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tariffs.json"
            path.write_text(
                """[{
                  "sc_code": "SC1",
                  "logic_steps": [{
                    "step_name": "Formula",
                    "charge_type": "formula",
                    "python_formula": "user.billed_kwh * 0.10"
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

    def test_tier_dictionary_is_rejected_not_silently_flattened(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tariffs.json"
            path.write_text(
                """[{
                  "sc_code": "SC1",
                  "logic_steps": [{
                    "step_name": "Voltage",
                    "charge_type": "per_kwh",
                    "value": {"0-2 kV": 0.10, "2-15 kV": 0.08}
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
