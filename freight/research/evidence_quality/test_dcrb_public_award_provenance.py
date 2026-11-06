"""Standalone fail-closed, research-only source-identity regression; no network/API.

This validates that indexed first-party DCRB notice metadata cannot be turned
into an independently adjudicated commercial benchmark. It does NOT check live
issuer bytes or award-payment truth and must not enter an application release.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

FIXTURE = Path(__file__).with_name("dcrb_case.json")


def decide(record):
    """Fail closed; explicit RFP alias supports provenance, not award truth."""
    award, rfp = record["award_publisher_page"], record["original_solicitation"]
    if not all(urlsplit(x["url"]).hostname == "dcrb.dc.gov" for x in (award, rfp)):
        return "REJECT_NOT_SAME_OFFICIAL_ISSUER", False
    if award["issuer"] != rfp["issuer"]:
        return "REJECT_ISSUER_DISAGREEMENT", False
    original = rfp["original_solicitation_number"]
    raw = award["raw_solicitation_field"]
    if raw == original:
        return "LINKED_EXACT_FIRST_PARTY_RFP_ID", False
    # Narrow, human-reviewed alias for this ONE publisher's typo. Never use a
    # general whitespace/fuzzy join, and do not promote to independent truth.
    if raw == "D CR B-2025-RFP-0500" and original == "DCRB-2025-RFP-0500":
        return "LINKED_EXPLICIT_FIRST_PARTY_RFP_ALIAS", False
    return "UNKNOWN_NO_SOURCE_PROVEN_JOIN", False


class DCRBOriginalCaseNegativeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_actual_publisher_spelling_mismatch_requires_explicit_source_alias(self):
        a = self.case["award_publisher_page"]
        b = self.case["original_solicitation"]
        self.assertNotEqual(a["raw_solicitation_field"], b["original_solicitation_number"])
        self.assertEqual(decide(self.case), ("LINKED_EXPLICIT_FIRST_PARTY_RFP_ALIAS", False))

    def test_award_number_must_not_substitute_for_solicitation_number(self):
        case = copy.deepcopy(self.case)
        case["award_publisher_page"]["raw_solicitation_field"] = "DCRB-2026-C-0100"
        self.assertEqual(decide(case), ("UNKNOWN_NO_SOURCE_PROVEN_JOIN", False))

    def test_wrong_publisher_or_issuer_rejected_not_weakly_fuzzy_joined(self):
        for field, value in (("url", "https://malicious.example/publication"),
                             ("issuer", "Another District Agency")):
            case = copy.deepcopy(self.case)
            case["award_publisher_page"][field] = value
            self.assertTrue(decide(case)[0].startswith("REJECT_"))

    def test_unrelated_authorized_federal_fixture_cannot_link_to_dc_award(self):
        federal = self.case["historical_repository_fixture"]
        district = self.case["original_solicitation"]["original_solicitation_number"]
        self.assertEqual(len(federal["existing_award_piids"]), 2)
        self.assertTrue(all(x != district for x in federal["existing_award_piids"]))
        self.assertEqual(federal["scope"],
                         "PUBLISHER_INDEXED_REPORTED_FEDERAL_AWARDS_NOT_FIRST_PARTY_SOLICITATION_RECORDS")

    def test_rfp_amendments_are_not_post_award_contract_modifications(self):
        a = self.case["award_publisher_page"]
        self.assertEqual(a["listed_rfp_amendments"], ["A0001", "A0002"])
        self.assertIsNone(a["post_award_contract_modification_history"])
        self.assertIsNone(a["cash_paid"])
        self.assertNotEqual(a["total_contract_value_including_options_usd"], "0")

    def test_no_false_benchmark_release_from_publisher_source(self):
        limits = self.case["derived_conclusions"]
        for k in ("validated_benchmark", "independent_award_outcome_adjudication",
                  "rights_cleared_for_commercial_automated_reuse",
                  "contract_value_is_cash_received",
                  "listed_amendments_are_post_award_modifications"):
            self.assertIs(limits[k], False)
        self.assertIs(decide(self.case)[1], False)


if __name__ == "__main__":
    unittest.main()
