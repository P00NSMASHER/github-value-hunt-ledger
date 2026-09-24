from recoveryworks.test_support import source_hash as H
from pathlib import Path
import tempfile
import unittest

from recoveryworks import FindingState
from recoveryworks.branches.utility import (
    UtilityBill,
    UtilityCharge,
    UtilityChargeKind,
    UtilityTariff,
    audit_utility_bills,
)
from recoveryworks.branches.utility_ingest import ingest_utility_exports


def tariff(start, end, energy_rate):
    return UtilityTariff(
        utility_id="Utility A",
        service_class="SC1",
        effective_from=start,
        effective_to=end,
        charges=(
            UtilityCharge("customer", UtilityChargeKind.FIXED, amount_cents=500),
            UtilityCharge(
                "energy",
                UtilityChargeKind.ENERGY,
                rate_micros_per_unit=energy_rate,
            ),
        ),
        source_hash=H(f"tariff-{start}"),
        source_locator=f"file://tariff#{start}",
        verified=True,
    )


def bill(start, end, *, bill_date="2026-07-10", actual=3000):
    return UtilityBill(
        bill_id="B-1",
        utility_id="Utility A",
        account_id="A-1",
        service_class="SC1",
        bill_date=bill_date,
        service_start=start,
        service_end=end,
        actual_cents=actual,
        billed_kwh="100",
        source_hash=H("bill-hash"),
        source_locator="file://bill#1",
        verified=True,
    )


class UtilityIngestTests(unittest.TestCase):
    def test_service_period_not_bill_date_selects_tariff_version(self):
        old = tariff("2026-01-01", "2026-06-30", 100000)
        new = tariff("2026-07-01", None, 200000)
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill("2026-06-01", "2026-06-30", bill_date="2026-07-10", actual=2000),),
            tariffs=(old, new),
        )
        self.assertEqual(batch.exceptions, ())
        self.assertEqual(len(batch.observations), 1)
        self.assertEqual(batch.observations[0].expected_cents, 1500)
        self.assertEqual(batch.observations[0].metadata["rate_selection_basis"], "service_period")

    def test_service_period_crossing_tariff_change_fails_closed(self):
        old = tariff("2026-01-01", "2026-06-30", 100000)
        new = tariff("2026-07-01", None, 200000)
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill("2026-06-15", "2026-07-15", actual=4000),),
            tariffs=(old, new),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(len(batch.exceptions), 1)
        self.assertEqual(batch.exceptions[0].code, "SERVICE_PERIOD_SPANS_TARIFF_CHANGE")

    def test_partial_service_period_coverage_fails_closed(self):
        only = tariff("2026-06-15", None, 100000)
        batch = audit_utility_bills(
            client_id="client",
            bills=(bill("2026-06-01", "2026-06-30", actual=4000),),
            tariffs=(only,),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "PARTIAL_TARIFF_COVERAGE")

    def test_file_to_frozen_scan_carries_service_period_and_is_validated(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bills = root / "Bills.csv"
            tariffs = root / "tariffs.json"
            bills.write_text(
                "Bill_ID,Utility,Account_ID,Service_Class,Bill_Date,Bill_Amount,"
                "Billed_kWh,Billed_Demand_kW,Billed_rkVA,Service_Start,Service_End\n"
                "B-1,Utility A,A-1,SC1,2026-07-10,20.00,100,0,0,2026-06-01,2026-06-30\n",
                encoding="utf-8",
            )
            tariffs.write_text(
                """{
                  "tariffs": [
                    {
                      "sc_code": "SC1",
                      "effective_date": "2026-01-01",
                      "effective_to": "2026-06-30",
                      "logic_steps": [
                        {"step_name": "Customer", "charge_type": "fixed_fee", "value": 5},
                        {"step_name": "Energy", "charge_type": "per_kwh", "value": 0.10}
                      ]
                    },
                    {
                      "sc_code": "SC1",
                      "effective_date": "2026-07-01",
                      "logic_steps": [
                        {"step_name": "Customer", "charge_type": "fixed_fee", "value": 5},
                        {"step_name": "Energy", "charge_type": "per_kwh", "value": 0.20}
                      ]
                    }
                  ]
                }""",
                encoding="utf-8",
            )

            result = ingest_utility_exports(
                client_id="client-1",
                bills_path=bills,
                tariffs_path=tariffs,
                utility_id="Utility A",
                default_effective_from="2026-01-01",
                verified_bills=True,
                verified_tariffs=True,
            )
            self.assertEqual(result.audit.exceptions, ())
            self.assertEqual(result.bill_count, 1)
            self.assertEqual(result.tariff_count, 2)
            self.assertEqual(len(result.scan.manifest.sources), 2)
            self.assertEqual(len(result.scan.findings), 1)
            finding = result.scan.findings[0]
            self.assertIs(finding.state, FindingState.VALIDATED)
            self.assertEqual(finding.expected_cents, 1500)
            self.assertEqual(finding.potential_recovery_cents, 500)
            self.assertEqual(finding.metadata["service_start"], "2026-06-01")
            self.assertEqual(finding.metadata["service_end"], "2026-06-30")

    def test_only_one_service_boundary_is_rejected(self):
        with self.assertRaises(ValueError):
            UtilityBill(
                bill_id="B-X",
                utility_id="Utility A",
                account_id="A-1",
                service_class="SC1",
                bill_date="2026-07-10",
                service_start="2026-06-01",
                service_end=None,
                actual_cents=1000,
                source_hash=H("h"),
                source_locator="file://b",
            )


if __name__ == "__main__":
    unittest.main()
