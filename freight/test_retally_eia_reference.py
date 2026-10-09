"""Offline checks for immutable EIA reference admission. No customer inputs."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from freight import retally_eia_reference as eia


class OfficialReferenceTest(unittest.TestCase):
    def mutate(self, *, change: str, substitute: str, require_pin: bool = False):
        source = eia.PATH.read_text(encoding="utf-8")
        self.assertIn(change, source)
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "sample.csv"
            file.write_text(source.replace(change, substitute, 1), encoding="utf-8")
            with self.assertRaises(eia.ReferenceDataError):
                eia.load_reference(file, require_pin=require_pin)

    def test_pinned_digest_matches_exact_bytes(self):
        self.assertEqual(hashlib.sha256(eia.PATH.read_bytes()).hexdigest(), eia.PINNED_SHA256)

    def test_all_nine_observations_admitted(self):
        self.assertEqual(len(eia.load_reference()), 9)

    def test_three_independently_checked_regions(self):
        expected = {
            ("2026-09-21", "US"): "6.529",
            ("2026-09-28", "US"): "6.382",
            ("2026-10-05", "US"): "6.199",
            ("2026-09-21", "EAST_COAST"): "6.268",
            ("2026-09-28", "EAST_COAST"): "6.137",
            ("2026-10-05", "EAST_COAST"): "5.951",
            ("2026-09-21", "CENTRAL_ATLANTIC"): "6.546",
            ("2026-09-28", "CENTRAL_ATLANTIC"): "6.531",
            ("2026-10-05", "CENTRAL_ATLANTIC"): "6.485",
        }
        for key, value in expected.items():
            self.assertEqual(eia.reference_price(*key).price, Decimal(value))

    def test_tampering_of_valid_numeric_price_rejected_by_pin(self):
        self.mutate(change="2026-10-05,US,6.199", substitute="2026-10-05,US,6.999", require_pin=True)

    def test_duplicate_week_region_rejected(self):
        self.mutate(change="2026-09-28,US,6.382", substitute="2026-09-21,US,6.382")

    def test_missing_observation_rejected(self):
        self.mutate(change="2026-09-28,US,6.382\n", substitute="")

    def test_unknown_region_rejected(self):
        self.mutate(change=",EAST_COAST,6.268", substitute=",CUSTOMER_A,6.268")

    def test_unknown_week_rejected(self):
        self.mutate(change="2026-09-21,US,6.529", substitute="2026-09-22,US,6.529")

    def test_invalid_precision_rejected(self):
        self.mutate(change="2026-10-05,US,6.199", substitute="2026-10-05,US,6.2")

    def test_negative_and_unreasonable_prices_rejected(self):
        for substitute in ["-6.199", "30.999", "NaN", "6e0"]:
            with self.subTest(substitute=substitute):
                self.mutate(change="2026-10-05,US,6.199", substitute="2026-10-05,US," + substitute)

    def test_extra_csv_field_rejected(self):
        self.mutate(change="2026-09-21,US,6.529", substitute="2026-09-21,US,6.529,unexpected")

    def test_header_change_rejected(self):
        self.mutate(change="week,region,usd_per_gallon", substitute="week,carrier,price")

    def test_no_customer_or_fee_authorization_fields_exist(self):
        observation = eia.reference_price("2026-10-05", "CENTRAL_ATLANTIC")
        self.assertEqual(observation.role, "OBSERVED_PUBLIC_MARKET_REFERENCE_ONLY")
        self.assertEqual(observation.units, "USD_PER_GALLON_INCLUDING_TAXES")
        self.assertEqual(observation.publisher, "U.S. Energy Information Administration")
        self.assertEqual(set(observation.__dataclass_fields__), {
            "week", "region", "price", "publisher", "source_url", "units", "role",
        })

    def test_unsupported_lookup_fails(self):
        with self.assertRaises(eia.ReferenceDataError):
            eia.reference_price("2026-10-12", "US")
        with self.assertRaises(eia.ReferenceDataError):
            eia.reference_price("2026-10-05", "CUSTOMER_LTL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
