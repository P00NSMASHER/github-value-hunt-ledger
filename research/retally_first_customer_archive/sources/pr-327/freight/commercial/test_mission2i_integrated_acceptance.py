"""Final RETALLY Missions 2B-2I cross-workstream consistency tests.

These tests prove source consistency, not legal clearance, customer authorisation,
working inbound mail, confidential-data security, or a real recovery.
"""
from __future__ import annotations
import hashlib
import json
import unittest
from decimal import Decimal
from pathlib import Path

from freight.commercial.first_customer_gate import evaluate
from freight.commercial.zero_upfront_underwriting import model_scenario

FREIGHT = Path(__file__).resolve().parents[1]
COMMERCIAL = FREIGHT / "commercial"
COLLATERAL = FREIGHT / "brand" / "mission2b"


class RetallyFinalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = json.loads((COLLATERAL / "COMMERCIAL_TRUTH_M2C_V1.json").read_text())
        cls.generator = json.loads((COLLATERAL / "source" / "commercial_truth.json").read_text())
        cls.operator = json.loads((COMMERCIAL / "first_customer_acceptance_m2g.json").read_text())
        cls.scenario = json.loads((COMMERCIAL / "fixtures" / "zero_upfront_synthetic_example.json").read_text())

    def test_one_canonical_generator_truth(self):
        self.assertEqual(self.canonical, self.generator)

    def test_original_approved_masters_not_derivatives(self):
        for name in ("wordmark", "emblem"):
            filename = COLLATERAL / "assets" / ("retally-" + name + "-approved.png")
            digest = hashlib.sha256(filename.read_bytes()).hexdigest()
            self.assertEqual(digest, self.canonical["approved_brand"][name + "_sha256"])

    def test_synthetic_money_states_consistent_across_workstreams(self):
        a = self.canonical["synthetic_public_aggregate"]["usd"]
        b = self.operator["published_synthetic_sample"]
        matches = {
            "gross_posted_recovery": "gross_recovered_usd",
            "reversals": "reversals_usd",
            "net_posted_recovery": "net_recovered_usd",
            "published_fee_eligible": "published_fee_eligible_usd",
            "eligibility_difference_unallocated": "unallocated_difference_usd",
        }
        for left, right in matches.items():
            with self.subTest(field=left):
                self.assertEqual(Decimal(a[left]), Decimal(b[right]))
        self.assertEqual(Decimal(a["net_posted_recovery"])-Decimal(a["published_fee_eligible"]),Decimal("1650.00"))
        self.assertFalse(self.canonical["synthetic_public_aggregate"]["real_customer_outcome"])
        self.assertEqual(self.canonical["synthetic_public_aggregate"]["eligible_base_verdict"], "UNVERIFIED_UNALLOCATED_DIFFERENCE")
        self.assertFalse(b["customer_result"])

    def test_prospect_pilot_and_publication_remain_blocked(self):
        status=evaluate(self.operator)
        self.assertFalse(status["all_customer_pilot_gates_ready"])
        for name in ("contact","qualified_proposal","confidential_pilot","claims_recovery","sample_publication"):
            self.assertFalse(status["gates"][name]["ready"], name)
        self.assertEqual(status["release_policy"],"REVIEW_ONLY_NO_CUSTOMER_DATA")

    def test_underwriting_cannot_override_customer_gate(self):
        value=model_scenario(self.scenario)
        self.assertEqual(value["classification"], "SYNTHETIC_INTERNAL_WHAT_IF_ONLY")
        self.assertEqual(value["risk_decision"],"HOLD")
        self.assertFalse(value["customer_kickoff_authorized"])
        self.assertFalse(value["customer_price_or_approved_rate"])
        self.assertEqual(value["cost"]["program_zero_recovery_loss_usd"],"7500.00")
        self.assertEqual(value["cost"]["zero_recovery_loss_usd"],"2500.00")

    def test_contingency_illustrations_are_not_approved(self):
        self.assertFalse(self.canonical["hypothetical_pricing"]["approved_retally_rate"])
        self.assertFalse(self.scenario["actual_rate_approved_in_signed_terms"])
        self.assertNotEqual(self.canonical["hypothetical_pricing"]["rate"], "SIGNED")
        self.assertEqual(self.operator["founding_offer"]["actual_contingency_rate"], "NOT_APPROVED")


if __name__ == "__main__":
    unittest.main()
