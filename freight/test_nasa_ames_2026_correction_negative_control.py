"""Nonproduction, first-party SAM notice correction negative-control tests.

Source: NASA Ames SAM.gov public justification, revised 2026-10-20.
The fixture is a human-transcribed public agency record, NOT source-byte
custody, contract transaction reconciliation, source-rights approval or a
validated notice-to-award performance benchmark.
No network, customer data, release, workflow or D1 reads.
"""
from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

CASE_FILE = (
    Path(__file__).resolve().parent
    / "fixtures/nasa_ames_2026_correction_negative_control_v1.json"
)
AS_OBSERVED = datetime(2026, 11, 5, 16, 0, tzinfo=timezone.utc)


def fixture():
    return json.loads(CASE_FILE.read_text(encoding="utf-8"))


def corrected_capability_status(case):
    """An explicit later agency correction overrides the original zero claim."""
    src = case["source"]
    fix = case["correction"]
    if src["raw_notice_bytes_retained"] or src["raw_notice_sha256"] is not None:
        return "INVALID_SOURCE_CUSTODY_CLAIM"
    if fix["official_correction_date"] < fix["prior_justification_published_date"]:
        return "INVALID_REVISION_CHRONOLOGY"
    if (fix["earlier_claim_capability_statements_received"] == 0
            and fix["corrected_capability_statements_received"] == 1
            and fix["capability_statement_received_date"] == "2026-06-30"):
        return "FALSIFIED_EARLIER_ZERO_STATEMENTS"
    return "UNKNOWN_NOT_ADJUDICATED"


class NasaAmes2026CorrectionNegativeControlTests(unittest.TestCase):
    def test_falsifies_no_capability_statements_without_implying_multiple_offers(self):
        c = fixture()
        self.assertEqual(
            corrected_capability_status(c),
            "FALSIFIED_EARLIER_ZERO_STATEMENTS",
        )
        self.assertFalse(c["correction"]["sole_source_decision_changed"])
        self.assertFalse(c["correction"]["evaluation_said_alternative_capable_within_schedule"])
        changed = copy.deepcopy(c)
        changed["correction"]["corrected_capability_statements_received"] = 0
        self.assertNotEqual(
            corrected_capability_status(changed), "FALSIFIED_EARLIER_ZERO_STATEMENTS"
        )
        backdated = copy.deepcopy(c)
        backdated["correction"]["official_correction_date"] = "2026-09-01"
        self.assertEqual(
            corrected_capability_status(backdated), "INVALID_REVISION_CHRONOLOGY"
        )

    def test_notice_identifier_not_assumed_to_be_solicitation_identifier(self):
        c = fixture()
        p = c["identity"]
        self.assertNotEqual(
            p["current_justification_notice_identifier"],
            p["solicitation_identifier_referenced"],
        )
        award = {
            "solicitation_identifier": p["solicitation_identifier_referenced"],
            "matched_issuer_agency_code": "NASA",
            "matched_issuer_office": p["office"],
            "award_date_signed": p["award_date"],
        }
        notice = {
            "solicitation_number": p["current_justification_notice_identifier"],
            "agency_code": "NASA",
            "office": p["office"],
            "posted_date": c["source"]["notice_updated_date"],
        }
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=AS_OBSERVED
            ), "UNMATCHED_OR_UNKNOWN"
        )
        notice["solicitation_number"] = p["solicitation_identifier_referenced"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=AS_OBSERVED
            ), "FUTURE_POSTED_NOTICE_NOT_PREAWARD"
        )
        notice["posted_date"] = "2026-06-16"  # Earlier intent date is NOT a saved 6/16 original.
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=AS_OBSERVED
            ), "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF"
        )
        award["matched_issuer_office"] = "DIFFERENT CONTRACTING OFFICE"
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=AS_OBSERVED
            ), "ISSUER_CONFLICT"
        )

    def test_notice_revision_is_not_award_modification_or_recovered_cash(self):
        c = fixture()
        p = c["identity"]
        b = c["boundaries"]
        self.assertEqual(p["contract_award_identifier"], "80ARC026C0006")
        self.assertEqual(p["awardee_uei"], "PLUQPL2X6CN3")
        self.assertEqual(p["awardee"], "EraDrive, Inc.")
        self.assertEqual(p["agency_noticed_award_amount_usd"], 11_925_000)
        self.assertEqual(p["agency_noticed_total_including_options_usd"], 13_000_000)
        self.assertEqual(
            p["agency_noticed_total_including_options_usd"]
            - p["agency_noticed_award_amount_usd"], 1_075_000
        )  # Option headroom is NOT identified overpayment/recovery.
        self.assertIsNone(p["award_modification_number"])
        self.assertIsNone(b["verified_contract_modification_count"])
        self.assertIsNone(b["verified_recovery_amount_usd"])
        self.assertFalse(c["correction"]["notice_revision_is_contract_modification"])
        self.assertFalse(b["independently_validated_notice_to_award_transaction"])
        self.assertFalse(b["independently_adjudicated_award_outcome"])
        self.assertFalse(b["case_is_in_fy2027_archive"])
        self.assertFalse(b["official_correction_retroactively_proves_notice_public_at_prior_date"])

    def test_source_custody_and_rights_remain_unknown_not_implicit_approval(self):
        c = fixture()
        self.assertEqual(c["source"]["publisher"], "NASA Ames Research Center via SAM.gov")
        self.assertTrue(c["source"]["official_notice_url"].startswith(
            "https://sam.gov/workspace/contract/opp/"
        ))
        self.assertFalse(c["source"]["raw_notice_bytes_retained"])
        self.assertIsNone(c["source"]["raw_notice_sha256"])
        self.assertFalse(c["source"]["independent_award_transaction_retrieved"])
        self.assertFalse(c["source"]["source_specific_reuse_approved"])
        self.assertEqual(
            c["boundaries"]["classification"],
            "AUTHENTIC_CORRECTION_FALSIFIES_ZERO_STATEMENTS_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
