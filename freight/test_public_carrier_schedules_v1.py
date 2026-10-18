"""Fail-closed public carrier-source and exact EIA cross-index regressions."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight import public_carrier_schedules_v1 as c


class CarrierPublicSourceTests(unittest.TestCase):
    def test_genuine_carrier_observations_are_date_scoped(self):
        rows=c.read_carrier_rates()
        self.assertEqual(len(rows),11)
        self.assertEqual([r["effective_start"] for r in rows
                          if r["carrier_service"]=="FEDEX_FREIGHT_LTL"],
                         ["2026-09-09","2026-09-16","2026-09-23",
                          "2026-09-30","2026-10-07","2026-10-14"])
        self.assertEqual(len([r for r in rows
            if r["carrier_service"]=="UPS_DOMESTIC_GROUND"]),4)
        self.assertEqual(len([r for r in rows
            if r["carrier_service"]=="UNION_PACIFIC_DOMESTIC_INTERMODAL"]),1)

    def test_exact_eia_index_lag_is_verified_where_carrier_publishes_it(self):
        fedex=[r for r in c.read_carrier_rates()
               if r["carrier_service"]=="FEDEX_FREIGHT_LTL"]
        self.assertEqual(fedex[0]["referenced_eia_us_week"],"2026-09-07")
        self.assertEqual(fedex[0]["referenced_eia_us_usd_per_gallon"],"5.967")
        self.assertEqual(fedex[-1]["referenced_eia_us_week"],"2026-10-12")
        self.assertEqual(fedex[-1]["referenced_eia_us_usd_per_gallon"],"6.179")
        self.assertEqual(fedex[-1]["surcharge_percent"],"57.50")

    def test_published_carrier_schedule_is_not_a_contract_or_recovery(self):
        report=c.public_schedule_report()
        self.assertEqual(report["source_rows"],11)
        self.assertEqual(report["carrier_source_families"],3)
        self.assertTrue(report["customer_agreement_still_controls"])
        self.assertTrue(report["public_surcharge_is_not_billed_invoice_charge"])
        self.assertTrue(report["not_continuous_current_rates"])
        self.assertEqual(report["verified_customer_invoice_count"],0)
        self.assertIsNone(report["verified_overcharge_cents"])
        self.assertFalse(report["financial_recovery_authorized"])
        self.assertEqual(report["commercial_claim_clearance"],"NOT_ESTABLISHED")

    def _alter(self,original,replacement):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"source.csv"
            source=c.CSV.read_text(encoding="utf-8")
            self.assertIn(original,source)
            p.write_text(source.replace(original,replacement,1),encoding="utf-8")
            with patch.object(c,"CSV",p):
                with self.assertRaisesRegex(ValueError,"CARRIER_PUBLIC_REFERENCE_"):
                    c.read_carrier_rates()

    def test_changed_original_carrier_percent_fails(self):
        self._alter("2026-09-09,55.4","2026-09-09,55.5")

    def test_referenced_wrong_EIA_price_or_incorrect_lag_fails(self):
        self._alter("2026-09-09,55.4,2026-09-07,5.967",
                    "2026-09-09,55.4,2026-09-07,5.999")
        self._alter("2026-09-09,55.4,2026-09-07,5.967",
                    "2026-09-09,55.4,2026-09-14,5.967")

    def test_unknown_source_host_is_not_trusted(self):
        self._alter(
           "https://www.fedexfreight.com/fragments/fuel-surcharge-table",
           "https://unapproved.example/fragments/fuel-surcharge-table"
        )

    def test_customer_invoice_column_cannot_be_injected(self):
        self._alter("official_source\n","official_source,customer_invoice_cents\n")

    def test_ups_index_is_not_inferred_or_silently_attached(self):
        self._alter("2026-09-07,27.50,,",
                    "2026-09-07,27.50,2026-09-07,5.967")

    def test_fabricated_extra_effective_date_is_rejected(self):
        self._alter(
            "UPS_DOMESTIC_GROUND,2026-09-28,30.25",
            "UPS_DOMESTIC_GROUND,2026-10-12,30.25"
        )


if __name__=="__main__":
    unittest.main()
