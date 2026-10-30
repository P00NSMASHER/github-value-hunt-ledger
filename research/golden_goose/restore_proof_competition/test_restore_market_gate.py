"""Adversarial verification: never mint owner revenue or demand from vendor lists."""
import copy
import json
from pathlib import Path
import unittest
from restore_market_gate import audit_data, dollars, hours


DATA = json.loads(Path(__file__).with_name("restore_competition_2026-10-29.json").read_text(encoding="utf-8"))


class MarketGateTests(unittest.TestCase):
    def test_baseline(self):
        result = audit_data(DATA)
        self.assertEqual(result["competitor_offers_source_checked"], 7)
        self.assertEqual(result["verified_owner_revenue_usd"], "0.00")
        self.assertEqual(result["demand_status"], "NOT_TESTED")
        self.assertEqual([v["modeled_contribution_usd"] for v in result["modeled_contributions"]], ["89.00", "44.00", "-1.00", "-46.00"])
        self.assertEqual(result["break_even_hours"], "3.9778")

    def test_external_price_never_mints_owner_revenue(self):
        a = copy.deepcopy(DATA)
        a["hypothetical_own_offer"]["gross_revenue_received_usd"] = "199.00"
        with self.assertRaises(ValueError): audit_data(a)

    def test_unverified_collectible_rejected(self):
        a = copy.deepcopy(DATA)
        a["hypothetical_own_offer"]["verified_collectible_usd"] = "950.00"
        with self.assertRaises(ValueError): audit_data(a)

    def test_fake_paid_buyer_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"][0]["independently_verified_customers"] = 3
        with self.assertRaises(ValueError): audit_data(a)

    def test_fake_real_customer_rejected(self):
        a = copy.deepcopy(DATA)
        a["hypothetical_own_offer"]["real_customer_count"] = 1
        with self.assertRaises(ValueError): audit_data(a)

    def test_fake_customer_backup_rejected(self):
        a = copy.deepcopy(DATA)
        a["hypothetical_own_offer"]["authorized_real_customer_backups"] = 1
        with self.assertRaises(ValueError): audit_data(a)

    def test_duplicate_vendor_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"].append(copy.deepcopy(a["offers"][0]))
        with self.assertRaises(ValueError): audit_data(a)

    def test_unknown_fixed_price_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"][2]["advertised_price_usd"] = None
        with self.assertRaises(ValueError): audit_data(a)

    def test_fake_flat_price_on_aws_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"][0]["advertised_price_usd"] = "0.00"
        with self.assertRaises(ValueError): audit_data(a)

    def test_bad_source_link_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"][1]["url"] = "http://unverified.example.org/"
        with self.assertRaises(ValueError): audit_data(a)

    def test_bad_price_source_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"][2]["price_url"] = None
        with self.assertRaises(ValueError): audit_data(a)

    def test_marketing_claim_cannot_be_pretend_sale(self):
        a = copy.deepcopy(DATA)
        a["offers"][2]["value_evidence"] = "verified_sales"
        with self.assertRaises(ValueError): audit_data(a)

    def test_negative_hours_rejected(self):
        self.assertRaises(ValueError, hours, "-1")

    def test_nan_money_rejected(self):
        self.assertRaises(ValueError, dollars, "NaN")

    def test_infinite_hours_rejected(self):
        self.assertRaises(ValueError, hours, "Infinity")

    def test_integer_price_rejected(self):
        self.assertRaises(ValueError, dollars, 199)

    def test_boolean_price_rejected(self):
        self.assertRaises(ValueError, dollars, True)

    def test_float_price_rejected(self):
        self.assertRaises(ValueError, dollars, 19.99)

    def test_subcent_rejected(self):
        self.assertRaises(ValueError, dollars, "0.001")

    def test_negative_rate_rejected(self):
        a = copy.deepcopy(DATA)
        a["hypothetical_own_offer"]["reviewer_hourly_cost_usd"] = "-40"
        with self.assertRaises(ValueError): audit_data(a)

    def test_missing_hours_rejected(self):
        a = copy.deepcopy(DATA)
        a["hypothetical_own_offer"]["assumed_review_hours"] = []
        with self.assertRaises(ValueError): audit_data(a)

    def test_unknown_price_basis_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"][2]["price_basis"] = "per_potential_claimant"
        with self.assertRaises(ValueError): audit_data(a)

    def test_snapshot_mutation_rejected(self):
        a = copy.deepcopy(DATA)
        a["snapshot_date"] = "2026-10-30"
        with self.assertRaises(ValueError): audit_data(a)

    def test_no_sources_rejected(self):
        a = copy.deepcopy(DATA)
        a["offers"] = []
        with self.assertRaises(ValueError): audit_data(a)


if __name__ == "__main__":
    unittest.main()
