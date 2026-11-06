"""GAO original-source negative control: scrap-sale bid is NOT federal spend.

GAO B-423992/B-423992.2 (February 9, 2026), primary adjudicative source:
https://www.gao.gov/products/b-423992,b-423992.2
DLA Disposition Services SOLD electronic scrap to the highest bidder, Gem
Southwest, under solicitation 33-4012. Its $152,124,000 EVALUATED PURCHASE
bid is not a federal payment to Gem; Regency bid $133,002,800 and lost.
DLA SAM award notice (original award bytes NOT independently retrieved):
https://sam.gov/opp/f50438e2e1b1475d9019196e6b8d68d9/view
Only cash-flow DIRECTION is falsified by the official GAO decision. The
underlying issuer award, contract modifications, payments and disbursements,
original byte custody, award transaction and reuse rights remain UNKNOWN.
Not a validated source-to-award benchmark. No D1, production or customer data.
"""
from __future__ import annotations

import copy
import unittest

SOURCE = {
    "issuer": "DEFENSE LOGISTICS AGENCY DISPOSITION SERVICES",
    "solicitation": "33-4012",
    "buyer_awardee": "GEM SOUTHWEST LLC",
    "protester_runner_up": "REGENCY PARTNERS LLC",
    "sale_commodity": "ELECTRONIC SCRAP PROPERTY",
    "contract_type": "SALES_CONTRACT",
    "award_notice_date": "2025-09-22",
    "gao_decision_date": "2026-02-09",
    "winning_evaluated_bid_usd": 152_124_000,
    "runner_up_evaluated_bid_usd": 133_002_800,
    "issuer_direction": "CONTRACTOR_PAYS_GOVERNMENT_FOR_PROPERTY",
    "award_contract_number": None,
    "contract_modifications": None,
    "actual_cash_received_by_issuer_usd": None,
    "independently_verified_spending_usd": None,
    "verified_customer_recovery_usd": None,
    "first_party_issuer_award_bytes_sha256": None,
    "commercial_reuse_approved": False,
}


def judge_claim(src: dict, claim: dict) -> str:
    """Fail closed on identity; reject cash-flow inversion without claiming cash."""
    if type(src) is not dict or type(claim) is not dict:
        return "UNKNOWN_MALFORMED"
    required = ("issuer", "solicitation", "buyer_awardee", "contract_type",
                "winning_evaluated_bid_usd")
    if any(not isinstance(src.get(k), str) or not src[k]
           for k in required[:-1]):
        return "UNKNOWN_INCOMPLETE_ORIGINAL"
    if type(src.get("winning_evaluated_bid_usd")) is not int:
        return "UNKNOWN_INCOMPLETE_ORIGINAL"
    if any(k not in claim or claim[k] is None for k in required):
        return "UNKNOWN_INCOMPLETE_CLAIM"
    if any(type(claim[k]) is not type(src[k]) or claim[k] != src[k]
           for k in required):
        return "UNKNOWN_UNMATCHED_SOURCE_IDENTITY_OR_BID"
    if src["contract_type"] != "SALES_CONTRACT" or src.get("issuer_direction") != (
            "CONTRACTOR_PAYS_GOVERNMENT_FOR_PROPERTY"):
        return "UNKNOWN_ORIGINAL_DIRECTION"
    if claim.get("cash_flow_direction") == "GOVERNMENT_PAYS_CONTRACTOR":
        return "FALSIFIED_GOVERNMENT_SPENDING_CLASSIFICATION"
    if claim.get("cash_flow_direction") == src["issuer_direction"]:
        return "SALE_DIRECTION_CONSISTENT_ACTUAL_CASH_UNKNOWN"
    return "UNKNOWN_CASH_FLOW_DIRECTION"


class DlaSaleBidNotGovernmentSpend(unittest.TestCase):
    def setUp(self):
        self.claim = {k: SOURCE[k] for k in (
            "issuer", "solicitation", "buyer_awardee", "contract_type",
            "winning_evaluated_bid_usd")}

    def test_exact_gao_case_falsifies_152m_spend_attribution(self):
        claim = {**self.claim, "cash_flow_direction": "GOVERNMENT_PAYS_CONTRACTOR"}
        self.assertEqual(judge_claim(SOURCE, claim),
                         "FALSIFIED_GOVERNMENT_SPENDING_CLASSIFICATION")
        self.assertEqual(SOURCE["contract_type"], "SALES_CONTRACT")
        self.assertEqual(SOURCE["winning_evaluated_bid_usd"], 152_124_000)

    def test_correct_sale_direction_does_not_prove_cash_received(self):
        claim = {**self.claim, "cash_flow_direction": SOURCE["issuer_direction"]}
        self.assertEqual(judge_claim(SOURCE, claim),
                         "SALE_DIRECTION_CONSISTENT_ACTUAL_CASH_UNKNOWN")
        self.assertIsNone(SOURCE["actual_cash_received_by_issuer_usd"])
        self.assertIsNone(SOURCE["independently_verified_spending_usd"])
        self.assertIsNone(SOURCE["verified_customer_recovery_usd"])

    def test_swapped_protester_or_runner_up_price_cannot_join(self):
        claim = {**self.claim, "buyer_awardee": SOURCE["protester_runner_up"],
                 "cash_flow_direction": "GOVERNMENT_PAYS_CONTRACTOR"}
        self.assertEqual(judge_claim(SOURCE, claim),
                         "UNKNOWN_UNMATCHED_SOURCE_IDENTITY_OR_BID")
        claim["buyer_awardee"] = SOURCE["buyer_awardee"]
        claim["winning_evaluated_bid_usd"] = SOURCE["runner_up_evaluated_bid_usd"]
        self.assertEqual(judge_claim(SOURCE, claim),
                         "UNKNOWN_UNMATCHED_SOURCE_IDENTITY_OR_BID")
        self.assertGreater(SOURCE["winning_evaluated_bid_usd"],
                           SOURCE["runner_up_evaluated_bid_usd"])

    def test_wrong_issuer_solicitation_or_purchaser_fails_closed(self):
        for field, bad in (("issuer", "OTHER ISSUER"),
                           ("solicitation", "33-4013"),
                           ("buyer_awardee", "UNRELATED PURCHASER LLC")):
            with self.subTest(field=field):
                claim = copy.deepcopy(self.claim)
                claim[field] = bad
                claim["cash_flow_direction"] = "GOVERNMENT_PAYS_CONTRACTOR"
                self.assertEqual(judge_claim(SOURCE, claim),
                                 "UNKNOWN_UNMATCHED_SOURCE_IDENTITY_OR_BID")

    def test_original_issuer_award_modifications_cash_and_rights_unknown(self):
        self.assertIsNone(SOURCE["award_contract_number"])
        self.assertIsNone(SOURCE["contract_modifications"])
        self.assertIsNone(SOURCE["first_party_issuer_award_bytes_sha256"])
        self.assertFalse(SOURCE["commercial_reuse_approved"])
        missing = {**self.claim, "buyer_awardee": None}
        self.assertEqual(judge_claim(SOURCE, missing), "UNKNOWN_INCOMPLETE_CLAIM")


if __name__ == "__main__":
    unittest.main()
