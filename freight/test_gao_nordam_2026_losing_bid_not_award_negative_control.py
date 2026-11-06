"""Original GAO decision negative control: losing bid is not awarded cash.

Official primary adjudicative record (GAO, July 7, 2026):
https://www.gao.gov/products/b-424390

The publicly released GAO decision reports that the Navy/Naval Supply
Systems Command selected Vertex under RFP N00383-25-R-001D, not NORDAM.
It reports *evaluated proposals* of $50,821,834 (Vertex) and $37,927,951
(NORDAM); the protester separately claimed $19,205,784 in hypothetical
excess costs. GAO denied the protest. None of those prices/claims is a
verified disbursement, avoidable loss, refund, or customer recovery.

Research-only original-decision transcription; GAO's decision is original
for the adjudication but is NOT an independently retrieved Navy award
transaction. Original Navy award number, actual award date, obligations,
contract modifications, source-byte digest and commercial reuse rights
remain UNKNOWN. Do not count a validated notice-to-award benchmark.

No network/D1 queries, secrets, application feature edits, release, or cash.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

SOURCE = {
    "official_gao_url": "https://www.gao.gov/products/b-424390",
    "gao_case": "B-424390",
    "decision_date": "2026-07-07",
    "decision_result": "DENIED",
    "issuer": "Department of the Navy",
    "office": "Naval Supply Systems Command",
    "rfp": "N00383-25-R-001D",
    "rfp_issued": "2025-02-24",
    "reported_awardee": "Vertex Modernization and Sustainment LLC",
    "losing_protester": "The NORDAM Group, LLC",
    "evaluated_vertex_proposal_usd": 50_821_834,
    "evaluated_nordam_proposal_usd": 37_927_951,
    "protester_alleged_excess_usd": 19_205_784,
    "navy_award_contract_id": None,
    "navy_award_signed_date": None,
    "confirmed_contract_modification_numbers": None,
    "transaction_obligated_usd": None,
    "customer_recovery_usd": None,
    "source_document_bytes_sha256": None,
    "reuse_rights_verified": False,
}
OBSERVED = datetime(2026, 11, 6, tzinfo=timezone.utc)


def adjudicate_gao_awardee_claim(source: dict, candidate: dict) -> str:
    """Adjudicate GAO's named awardee only, never validate award transactions."""
    if type(source) is not dict or type(candidate) is not dict:
        return "UNKNOWN_SOURCE_OR_CANDIDATE"
    if (
        source.get("official_gao_url") != SOURCE["official_gao_url"]
        or source.get("gao_case") != SOURCE["gao_case"]
        or source.get("decision_result") != "DENIED"
        or not source.get("reported_awardee")
        or not source.get("issuer")
        or not source.get("office")
        or not source.get("rfp")
    ):
        return "UNKNOWN_UNAUTHENTICATED_ADJUDICATION"
    if (
        candidate.get("issuer") != source["issuer"]
        or candidate.get("office") != source["office"]
        or candidate.get("rfp") != source["rfp"]
    ):
        return "UNKNOWN_MISMATCHED_CASE_IDENTITY"
    if not candidate.get("reported_awardee"):
        return "UNKNOWN_MISSING_AWARDEE"
    if candidate["reported_awardee"] != source["reported_awardee"]:
        return "FALSIFIED_LOSING_PROPOSAL_AS_AWARDEE"
    if (
        candidate.get("claimed_recovery_usd") is not None
        or candidate.get("claimed_obligation_usd") is not None
        or candidate.get("claimed_savings_usd") is not None
    ):
        return "FALSIFIED_PROPOSAL_OR_ALLEGATION_AS_PAID_OUTCOME"
    if candidate.get("award_contract_id") is not None:
        return "UNKNOWN_AWARD_CONTRACT_ID_NOT_IN_GAO_EXCERPT"
    return "GAO_AWARDEE_SUPPORTED_TRANSACTION_UNKNOWN"


def candidate_for(awardee: str) -> dict:
    return {
        "issuer": SOURCE["issuer"],
        "office": SOURCE["office"],
        "rfp": SOURCE["rfp"],
        "reported_awardee": awardee,
        "award_contract_id": None,
        "claimed_recovery_usd": None,
        "claimed_obligation_usd": None,
        "claimed_savings_usd": None,
    }


class GAO2026NordamAwardeeAndPriceNegativeControls(unittest.TestCase):
    def test_primary_decision_falsifies_lower_bid_as_awardee(self):
        self.assertEqual(
            adjudicate_gao_awardee_claim(
                SOURCE, candidate_for(SOURCE["losing_protester"])
            ),
            "FALSIFIED_LOSING_PROPOSAL_AS_AWARDEE",
        )
        self.assertEqual(
            adjudicate_gao_awardee_claim(
                SOURCE, candidate_for(SOURCE["reported_awardee"])
            ),
            "GAO_AWARDEE_SUPPORTED_TRANSACTION_UNKNOWN",
        )

    def test_official_issuer_rfp_and_awardee_identity_are_required(self):
        for field, wrong in (
            ("issuer", "Department of Veterans Affairs"),
            ("office", "Unrelated Contracting Activity"),
            ("rfp", "N00383-25-R-9999"),
        ):
            with self.subTest(field=field):
                candidate = candidate_for(SOURCE["reported_awardee"])
                candidate[field] = wrong
                self.assertEqual(
                    adjudicate_gao_awardee_claim(SOURCE, candidate),
                    "UNKNOWN_MISMATCHED_CASE_IDENTITY",
                )
        missing = candidate_for(SOURCE["reported_awardee"])
        missing["reported_awardee"] = None
        self.assertEqual(
            adjudicate_gao_awardee_claim(SOURCE, missing),
            "UNKNOWN_MISSING_AWARDEE",
        )
        altered = copy.deepcopy(SOURCE)
        altered["gao_case"] = "B-000000"
        self.assertEqual(
            adjudicate_gao_awardee_claim(
                altered, candidate_for(SOURCE["reported_awardee"])
            ),
            "UNKNOWN_UNAUTHENTICATED_ADJUDICATION",
        )

    def test_proposal_arithmetic_and_allegation_are_not_cash(self):
        # These are two evaluated offer prices, not contract obligations.
        delta = (
            SOURCE["evaluated_vertex_proposal_usd"]
            - SOURCE["evaluated_nordam_proposal_usd"]
        )
        self.assertEqual(delta, 12_893_883)
        self.assertNotEqual(delta, SOURCE["protester_alleged_excess_usd"])
        for alleged in (delta, SOURCE["protester_alleged_excess_usd"]):
            for field in (
                "claimed_recovery_usd",
                "claimed_obligation_usd",
                "claimed_savings_usd",
            ):
                with self.subTest(field=field, alleged=alleged):
                    candidate = candidate_for(SOURCE["reported_awardee"])
                    candidate[field] = alleged
                    self.assertEqual(
                        adjudicate_gao_awardee_claim(SOURCE, candidate),
                        "FALSIFIED_PROPOSAL_OR_ALLEGATION_AS_PAID_OUTCOME",
                    )

    def test_unknown_award_id_cannot_be_invented(self):
        candidate = candidate_for(SOURCE["reported_awardee"])
        candidate["award_contract_id"] = "N00383-26-D-FAKE"
        self.assertEqual(
            adjudicate_gao_awardee_claim(SOURCE, candidate),
            "UNKNOWN_AWARD_CONTRACT_ID_NOT_IN_GAO_EXCERPT",
        )
        self.assertIsNone(SOURCE["navy_award_contract_id"])
        self.assertIsNone(SOURCE["confirmed_contract_modification_numbers"])
        self.assertIsNone(SOURCE["transaction_obligated_usd"])
        self.assertIsNone(SOURCE["customer_recovery_usd"])
        self.assertIsNone(SOURCE["source_document_bytes_sha256"])
        self.assertFalse(SOURCE["reuse_rights_verified"])

    def test_original_gao_decision_date_is_not_navy_award_date(self):
        # The original GAO decision is dated July 7, 2026. It is NOT
        # evidence of the date the Navy actually signed its contract.
        notice = {
            "solicitation_number": SOURCE["rfp"],
            "agency_code": "DOD",
            "office": SOURCE["office"],
            "posted_date": SOURCE["rfp_issued"],
        }
        candidate = {
            "solicitation_identifier": SOURCE["rfp"],
            "matched_issuer_agency_code": "DOD",
            "matched_issuer_office": SOURCE["office"],
            "award_date_signed": SOURCE["navy_award_signed_date"],
        }
        self.assertEqual(
            assess_cross_source_chronology(
                notice, candidate, source_observed_at=OBSERVED
            ),
            "SOURCE_DATE_UNKNOWN",
        )
        # Even an invalid guess using GAO's later decision date is
        # retrospective rather than a verified preaward capture.
        candidate["award_date_signed"] = SOURCE["decision_date"]
        self.assertEqual(
            assess_cross_source_chronology(
                notice, candidate, source_observed_at=OBSERVED
            ),
            "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF",
        )


if __name__ == "__main__":
    unittest.main()
