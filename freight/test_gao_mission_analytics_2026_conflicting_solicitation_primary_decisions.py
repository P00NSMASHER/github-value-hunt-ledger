"""GAO official-decision source conflict: one procurement, contradictory RFQ IDs.

Human-transcribed original public GAO decision text, checked Nov. 6, 2026:
  Jan. 14: https://www.gao.gov/products/b-423980
  Apr.  1: https://www.gao.gov/products/b-423980.2,b-423980.4
  May  21: https://www.gao.gov/products/b-423980.5,b-423980.6

Jan/Apr expressly name FA500425Q1001; May calls its reconsideration
FA500426Q1001, while referencing the same Sept. 2025 procurement and GAO
case B-423980. Do NOT auto-correct the May primary-source field or turn
either ID into an independently authenticated Air Force award join.

The May original GAO decision reports an Air Force purchase order to
Wingmann for $1,030,578 on Sept. 23, 2025. This is adjudicative narrative,
not original Air Force award bytes, an independently verified transaction,
obligations, modifications, payment or recoverable money. The May page also
recites the protester's contrary Sept. 29 SAM screenshot assertion; earlier
GAO decisions date the public notice Sept. 23. Preserve source attribution.

This file is an offline evidence-QA regression only; no original-body hash,
source-access attestation, commercial rights or validated benchmark.
"""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

DECISIONS = (
    {
        "case": "B-423980",
        "decision_date": "2026-01-14",
        "source_url": "https://www.gao.gov/products/b-423980",
        "rfq_as_written": "FA500425Q1001",
        "issuer": "Department of the Air Force",
        "reported_awardee": "Wingmann, LLC",
        "reported_award_date": "2025-09-23",
        "reported_purchase_order_usd": None,
    },
    {
        "case": "B-423980.2,B-423980.4",
        "decision_date": "2026-04-01",
        "source_url": "https://www.gao.gov/products/b-423980.2,b-423980.4",
        "rfq_as_written": "FA500425Q1001",
        "issuer": "Department of the Air Force",
        "reported_awardee": "Wingmann, LLC",
        "reported_award_date": "2025-09-23",
        "reported_purchase_order_usd": None,
    },
    {
        "case": "B-423980.5,B-423980.6",
        "decision_date": "2026-05-21",
        "source_url": "https://www.gao.gov/products/b-423980.5,b-423980.6",
        "rfq_as_written": "FA500426Q1001",
        "issuer": "Department of the Air Force",
        "reported_awardee": "Wingmann, LLC",
        "reported_award_date": "2025-09-23",
        "reported_purchase_order_usd": 1_030_578,
    },
)

# A fixed researcher transcription prevents both claim and source fixture
# being silently rewritten to invent unanimous publisher evidence. These
# constants are NOT hashes or original-byte custody.
TRANSCRIBED_ANCHORS = copy.deepcopy(DECISIONS)
PROTESTER = "Mission Analytics, LLC"
CONTRACT_ID_FROM_AIR_FORCE = None
MODIFICATION_NUMBERS_CONFIRMED = None
INDEPENDENT_AWARD_TRANSACTION = None
PAID_AMOUNT_CONFIRMED = None
CUSTOMER_RECOVERY_CONFIRMED = None


def adjudicate_decision_provenance(decisions, asserted_awardee=None):
    """Discriminate source conflict, never issue a validated award label."""
    if not isinstance(decisions, (tuple, list)) or len(decisions) != 3:
        return "UNKNOWN_INCOMPLETE_PRIMARY_CHAIN"
    if any(not isinstance(d, dict) for d in decisions):
        return "UNKNOWN_INCOMPLETE_PRIMARY_CHAIN"
    if any(d != anchor for d, anchor in zip(decisions, TRANSCRIBED_ANCHORS)):
        return "UNKNOWN_MUTATED_PRIMARY_TRANSCRIPTION"
    if asserted_awardee is not None and asserted_awardee != "Wingmann, LLC":
        return "REJECT_NON_AWARDEE_PROTESTER_OR_MISMATCH"
    if len({d["issuer"] for d in decisions}) != 1:
        return "UNKNOWN_UNMATCHED_ISSUERS"
    if len({d["reported_award_date"] for d in decisions}) != 1:
        return "UNKNOWN_CONFLICTING_AWARD_DATES"
    if len({d["rfq_as_written"] for d in decisions}) != 1:
        return "FALSIFIED_UNANIMOUS_GAO_RFQ_ID_CLAIM"
    return "SOURCE_CONSISTENT_NOT_AIR_FORCE_AWARD_VERIFIED"


class GAOPrimaryDecisionSolicitationConflict(unittest.TestCase):
    def test_original_decisions_disagree_on_identical_procurement_rfq(self):
        self.assertEqual(
            [d["rfq_as_written"] for d in DECISIONS],
            ["FA500425Q1001", "FA500425Q1001", "FA500426Q1001"],
        )
        self.assertEqual(adjudicate_decision_provenance(DECISIONS),
                         "FALSIFIED_UNANIMOUS_GAO_RFQ_ID_CLAIM")
        self.assertEqual(len({d["reported_awardee"] for d in DECISIONS}), 1)

    def test_claimant_cannot_silently_harmonize_or_forge_both_source_and_claim(self):
        changed = copy.deepcopy(DECISIONS)
        changed[2]["rfq_as_written"] = "FA500425Q1001"
        self.assertEqual(adjudicate_decision_provenance(changed),
                         "UNKNOWN_MUTATED_PRIMARY_TRANSCRIPTION")
        for field, forged in (("issuer", "NASA"),
                              ("reported_awardee", PROTESTER),
                              ("reported_purchase_order_usd", 12_000_000)):
            with self.subTest(field=field):
                changed = copy.deepcopy(DECISIONS)
                changed[2][field] = forged
                self.assertEqual(adjudicate_decision_provenance(changed),
                                 "UNKNOWN_MUTATED_PRIMARY_TRANSCRIPTION")
        self.assertEqual(adjudicate_decision_provenance(DECISIONS, PROTESTER),
                         "REJECT_NON_AWARDEE_PROTESTER_OR_MISMATCH")

    def test_actual_cross_source_chronology_gate_abstains_on_conflicting_ids(self):
        # The real date of observation is AFTER the 2025 award; never backfill
        # an imaginary contemporaneous preaward notice capture.
        award = {
            "solicitation_identifier": DECISIONS[2]["rfq_as_written"],
            "matched_issuer_agency_code": "DOD",
            "matched_issuer_office": "AIR FORCE",
            "award_date_signed": "2025-09-23",
        }
        notice = {
            "solicitation_number": DECISIONS[0]["rfq_as_written"],
            "agency_code": "DOD",
            "office": "AIR FORCE",
            "posted_date": "2025-09-11",
        }
        observed = datetime(2026, 11, 6, tzinfo=timezone.utc)
        self.assertEqual(assess_cross_source_chronology(
            notice, award, source_observed_at=observed), "UNMATCHED_OR_UNKNOWN")
        award["solicitation_identifier"] = DECISIONS[0]["rfq_as_written"]
        self.assertEqual(assess_cross_source_chronology(
            notice, award, source_observed_at=observed),
            "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF")
        # Deliberately hypothetical positive control, NOT observed data.
        self.assertEqual(assess_cross_source_chronology(
            notice, award, source_observed_at=datetime(
                2025, 9, 12, tzinfo=timezone.utc)),
            "PREAWARD_CHRONOLOGY_CANDIDATE_ONLY")

    def test_adjudication_amount_is_not_original_air_force_award_or_cash(self):
        self.assertEqual(DECISIONS[2]["reported_purchase_order_usd"], 1_030_578)
        self.assertIsNone(DECISIONS[0]["reported_purchase_order_usd"])
        self.assertIsNone(CONTRACT_ID_FROM_AIR_FORCE)
        self.assertIsNone(MODIFICATION_NUMBERS_CONFIRMED)
        self.assertIsNone(INDEPENDENT_AWARD_TRANSACTION)
        self.assertIsNone(PAID_AMOUNT_CONFIRMED)
        self.assertIsNone(CUSTOMER_RECOVERY_CONFIRMED)
        self.assertEqual(DECISIONS[2]["reported_awardee"], "Wingmann, LLC")
        self.assertNotEqual(PROTESTER, DECISIONS[2]["reported_awardee"])

    def test_unreviewed_repeated_decision_is_not_independent_award_label(self):
        self.assertEqual({d["issuer"] for d in DECISIONS},
                         {"Department of the Air Force"})
        self.assertTrue(all(d["source_url"].startswith("https://www.gao.gov/")
                            for d in DECISIONS))
        self.assertTrue(all(d["case"].startswith("B-423980") for d in DECISIONS))
        self.assertEqual(adjudicate_decision_provenance(DECISIONS[:2]),
                         "UNKNOWN_INCOMPLETE_PRIMARY_CHAIN")
        self.assertIsNone(INDEPENDENT_AWARD_TRANSACTION)


if __name__ == "__main__":
    unittest.main()
