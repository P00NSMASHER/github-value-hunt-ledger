"""GAO original adjudication negative control: protest remedy != award or paid cash.

TWO different, publicly accessible primary GAO adjudications:
2026-02-18 sustained protest, B-423993/B-423993.2:
https://www.gao.gov/products/b-423993,b-423993.2
2026-05-13 modified remedy, B-423993.4/B-423993.5:
https://www.gao.gov/products/b-423993.4,b-423993.5

GAO identifies U.S. Army Corps of Engineers RFQ W912DY-25-Q-A101,
the 2025-09-30 award to Export 220Volt, and the original recommendation
to reopen competition. On May 13 GAO *replaced* the recommendation
to reopen competition with a recommendation to reimburse protest and
quotation-preparation costs because contract performance was substantially
complete. This falsifies any interpretation of the later GAO decision as
an actual May 2026 reaward or a completed reimbursement.

Public human transcription only; GAO decisions are first-party evidence
of the protest disposition, NOT independently retrieved Army award
transaction/contract modification/payment records. Original decision
bytes/SHA and reuse rights not verified. Final QUOTATION is not an
obligation, loss, customer recovery or actual cash. NO VALIDATED
NOTICE-TO-AWARD BENCHMARK. No network, D1, customer data, feature code,
deployment, or changes to protected branches.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

ORIGINAL = {
    "official_source": "https://www.gao.gov/products/b-423993,b-423993.2",
    "gao_case": "B-423993;B-423993.2",
    "decision_date": "2026-02-18",
    "disposition": "SUSTAINED",
    "issuer": "Department of the Army",
    "office": "U.S. Army Corps of Engineers",
    "rfq": "W912DY-25-Q-A101",
    "rfq_issued": "2025-07-28",
    "original_award_date_reported": "2025-09-30",
    "awardee_reported": "Export 220Volt, Inc.",
    "protester": "Effective Communication Strategies, LLC",
    "awardee_evaluated_final_quote_usd": "2039912.11",
    "reopen_competition_recommended": True,
    "verified_army_award_contract_id": None,
    "verified_army_transaction_obligation_usd": None,
}
MODIFIED = {
    "official_source": "https://www.gao.gov/products/b-423993.4,b-423993.5",
    "gao_case": "B-423993.4;B-423993.5",
    "decision_date": "2026-05-13",
    "disposition": "REMEDY_MODIFIED",
    "issuer": "Department of the Army",
    "office": "U.S. Army Corps of Engineers",
    "rfq": "W912DY-25-Q-A101",
    "reported_original_awardee": "Export 220 Volt, Inc.",
    "reopen_competition_recommended": False,
    "replacement_recommendation": "QUOTATION_PREPARATION_AND_PROTEST_COSTS",
    "reason": "CONTRACT_SUBSTANTIALLY_COMPLETE",
    "actual_reaward_verified": None,
    "reimbursement_paid_usd": None,
    "verified_contract_modification": None,
    "original_source_bytes_sha256": None,
    "source_specific_reuse_rights_verified": False,
}
# Independent fixed transcription anchors resist mutating the very local
# source under test; they are NOT authentication of GAO's original bytes.
# Freeze EVERY transcribed field, including UNKNOWN cash, award and rights states.
# A checksum or local fixed anchor is still not original-file authentication.
# This boundary prevents a later claimed payment/award from passing simply
# because the fixture only pinned decision identity and dates.
ORIGINAL_ANCHOR = tuple(ORIGINAL.items())
MODIFIED_ANCHOR = tuple(MODIFIED.items())


def decide(source_original: dict, source_modified: dict, claim: dict) -> str:
    """Only adjudicate *what these GAO decisions establish*, not award truth."""
    if any(type(x) is not dict for x in (source_original, source_modified, claim)):
        return "UNKNOWN_MALFORMED_EVIDENCE"
    if (any(source_original.get(k) != v for k, v in ORIGINAL_ANCHOR)
            or any(source_modified.get(k) != v for k, v in MODIFIED_ANCHOR)):
        return "UNKNOWN_TAMPERED_TRANSCRIPTION"
    if (source_original["issuer"] != source_modified["issuer"]
            or source_original["office"] != source_modified["office"]
            or source_original["rfq"] != source_modified["rfq"]
            or source_original["awardee_reported"].upper().replace(" ", "")
            != source_modified["reported_original_awardee"].upper().replace(" ", "")):
        return "UNKNOWN_UNMATCHED_GAO_CASES"
    if (claim.get("issuer") != source_original["issuer"]
            or claim.get("office") != source_original["office"]
            or claim.get("rfq") != source_original["rfq"]):
        return "UNKNOWN_MISMATCHED_ISSUER_OR_RFQ"
    if claim.get("kind") == "GAO_MAY_REAWARD_OR_RECOMPETE_ORDER":
        # Only falsify an attempted reaward attribution for the actual
        # originally reported contractor, never a different or absent entity.
        if claim.get("contractor") != source_original["awardee_reported"]:
            return "UNKNOWN_MISMATCHED_REPORTED_AWARDEE"
        return "FALSIFIED_GAO_RECOMPETE_RECOMMENDATION_REPLACED"
    if claim.get("kind") == "ORIGINAL_2025_AWARDEE":
        if claim.get("contractor") != source_original["awardee_reported"]:
            return "FALSIFIED_WRONG_REPORTED_ORIGINAL_AWARDEE"
        return "GAO_REPORTED_AWARDEE_ONLY_TRANSACTION_UNKNOWN"
    if claim.get("kind") == "GAO_COSTS_REIMBURSEMENT":
        return "UNKNOWN_RECOMMENDED_COSTS_NOT_PROOF_OF_PAYMENT"
    if claim.get("kind") == "GAO_FINAL_QUOTE_AS_DISBURSEMENT":
        # A GAO quote can only falsify a claim for that exact evaluated amount.
        # An unrelated/missing price is UNKNOWN, not a source-proven failure.
        if (not isinstance(claim.get("amount_usd"), str)
                or claim["amount_usd"] != source_original["awardee_evaluated_final_quote_usd"]):
            return "UNKNOWN_UNMATCHED_EVALUATED_QUOTE_AMOUNT"
        return "FALSIFIED_EVALUATED_QUOTE_AS_OBLIGATION_OR_CASH"
    return "UNKNOWN_OUTSIDE_ORIGINAL_ADJUDICATION"


def claim(kind: str, **overrides: object) -> dict:
    result = {
        "kind": kind, "issuer": ORIGINAL["issuer"],
        "office": ORIGINAL["office"], "rfq": ORIGINAL["rfq"],
        "contractor": ORIGINAL["awardee_reported"],
    }
    if kind == "GAO_FINAL_QUOTE_AS_DISBURSEMENT":
        result["amount_usd"] = ORIGINAL["awardee_evaluated_final_quote_usd"]
    result.update(overrides)
    return result


class GAOECS2026WithdrawnRecompetitionNegativeControl(unittest.TestCase):
    def test_later_first_party_decision_withdraws_recompete_remedy(self):
        self.assertEqual(
            decide(ORIGINAL, MODIFIED, claim("GAO_MAY_REAWARD_OR_RECOMPETE_ORDER")),
            "FALSIFIED_GAO_RECOMPETE_RECOMMENDATION_REPLACED",
        )
        self.assertTrue(ORIGINAL["reopen_competition_recommended"])
        self.assertFalse(MODIFIED["reopen_competition_recommended"])
        self.assertEqual(MODIFIED["replacement_recommendation"],
                         "QUOTATION_PREPARATION_AND_PROTEST_COSTS")
        self.assertIsNone(MODIFIED["actual_reaward_verified"])

    def test_original_reported_awardee_but_no_transaction_or_wrong_awardee(self):
        self.assertEqual(
            decide(ORIGINAL, MODIFIED, claim("ORIGINAL_2025_AWARDEE")),
            "GAO_REPORTED_AWARDEE_ONLY_TRANSACTION_UNKNOWN",
        )
        self.assertEqual(
            decide(ORIGINAL, MODIFIED, claim("ORIGINAL_2025_AWARDEE",
                                              contractor=ORIGINAL["protester"])),
            "FALSIFIED_WRONG_REPORTED_ORIGINAL_AWARDEE",
        )
        self.assertIsNone(ORIGINAL["verified_army_award_contract_id"])
        self.assertIsNone(ORIGINAL["verified_army_transaction_obligation_usd"])
        self.assertIsNone(MODIFIED["verified_contract_modification"])

    def test_recommended_costs_and_evaluated_price_are_not_received_cash(self):
        self.assertEqual(
            decide(ORIGINAL, MODIFIED, claim("GAO_COSTS_REIMBURSEMENT")),
            "UNKNOWN_RECOMMENDED_COSTS_NOT_PROOF_OF_PAYMENT",
        )
        self.assertEqual(
            decide(ORIGINAL, MODIFIED, claim("GAO_FINAL_QUOTE_AS_DISBURSEMENT")),
            "FALSIFIED_EVALUATED_QUOTE_AS_OBLIGATION_OR_CASH",
        )
        # Negative controls: unrelated, absent, or numeric candidate prices
        # must not inherit the official evaluated-quote falsification.
        for wrong in ("9999999.99", None, 2039912.11):
            with self.subTest(candidate_amount=wrong):
                self.assertEqual(
                    decide(ORIGINAL, MODIFIED, claim("GAO_FINAL_QUOTE_AS_DISBURSEMENT", amount_usd=wrong)),
                    "UNKNOWN_UNMATCHED_EVALUATED_QUOTE_AMOUNT",
                )
        self.assertEqual(Decimal(ORIGINAL["awardee_evaluated_final_quote_usd"]),
                         Decimal("2039912.11"))
        self.assertIsNone(MODIFIED["reimbursement_paid_usd"])
        self.assertIsNone(MODIFIED["original_source_bytes_sha256"])
        self.assertFalse(MODIFIED["source_specific_reuse_rights_verified"])

    def test_mismatched_or_altered_original_cannot_inherit_disposition(self):
        for field, value in (
            ("issuer", "Department of Veterans Affairs"),
            ("office", "Unrelated Contracting Office"),
            ("rfq", "W912DY-25-Q-OTHER"),
        ):
            with self.subTest(field=field):
                self.assertEqual(
                    decide(ORIGINAL, MODIFIED, claim("GAO_MAY_REAWARD_OR_RECOMPETE_ORDER",
                                                  **{field: value})),
                    "UNKNOWN_MISMATCHED_ISSUER_OR_RFQ",
                )
        for source, field, value in (
            (ORIGINAL, "awardee_reported", ORIGINAL["protester"]),
            (MODIFIED, "reopen_competition_recommended", True),
            (MODIFIED, "decision_date", "2026-02-18"),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(source)
                changed[field] = value
                before = changed if source is ORIGINAL else ORIGINAL
                after = changed if source is MODIFIED else MODIFIED
                self.assertEqual(
                    decide(before, after, claim("GAO_MAY_REAWARD_OR_RECOMPETE_ORDER")),
                    "UNKNOWN_TAMPERED_TRANSCRIPTION",
                )

    def test_forged_original_source_payment_award_or_rights_is_quarantined(self):
        # Negative controls: source-matching identity/date fields cannot
        # make an invented verified award, amendment, payment or rights true.
        # Previously these fields were outside the fixture's anchor set.
        cases = (
            ("original", "verified_army_award_contract_id", "FAKE-CONTRACT"),
            ("original", "verified_army_transaction_obligation_usd", "2039912.11"),
            ("modified", "actual_reaward_verified", True),
            ("modified", "reimbursement_paid_usd", "2039912.11"),
            ("modified", "verified_contract_modification", "P0001"),
            ("modified", "source_specific_reuse_rights_verified", True),
        )
        for target, field, forged_value in cases:
            with self.subTest(target=target, field=field):
                original, modified = copy.deepcopy(ORIGINAL), copy.deepcopy(MODIFIED)
                (original if target == "original" else modified)[field] = forged_value
                self.assertEqual(
                    decide(original, modified,
                           claim("GAO_MAY_REAWARD_OR_RECOMPETE_ORDER")),
                    "UNKNOWN_TAMPERED_TRANSCRIPTION",
                )

    def test_unrelated_or_missing_awardee_cannot_inherit_gao_falsification(self):
        for incorrect in ("UNRELATED CONTRACTOR", None):
            with self.subTest(contractor=incorrect):
                self.assertEqual(
                    decide(ORIGINAL, MODIFIED,
                           claim("GAO_MAY_REAWARD_OR_RECOMPETE_ORDER",
                                 contractor=incorrect)),
                    "UNKNOWN_MISMATCHED_REPORTED_AWARDEE",
                )

    def test_late_observation_cannot_backfill_preaward_capture(self):
        notice = {
            "solicitation_number": ORIGINAL["rfq"],
            "agency_code": "DOD", "office": ORIGINAL["office"],
            "posted_date": ORIGINAL["rfq_issued"],
        }
        award = {
            "solicitation_identifier": ORIGINAL["rfq"],
            "matched_issuer_agency_code": "DOD",
            "matched_issuer_office": ORIGINAL["office"],
            "award_date_signed": ORIGINAL["original_award_date_reported"],
        }
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=datetime(2026, 11, 6, tzinfo=timezone.utc)),
            "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF",
        )
        # Hypothetical 2025 archive observation is NOT real evidence custody.
        self.assertEqual(
            assess_cross_source_chronology(
                notice, award, source_observed_at=datetime(2025, 8, 1, tzinfo=timezone.utc)),
            "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
