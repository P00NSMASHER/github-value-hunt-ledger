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


# Two *different* GAO first-party pages contain a second, independent
# cross-reference contradiction, distinct from the RFQ year typo above:
# https://www.gao.gov/products/b-423980.2,b-423980.4 -- Apr 1, 2026
# https://www.gao.gov/products/b-423980.5,b-423980.6 -- cites Mar 31,
# B-420983.4, even though the earlier docket is B-423980.4.
# These are human-transcribed published TEXT, not signed Air Force award data.
APRIL_GAO_DECISION = {
    "source_url": "https://www.gao.gov/products/b-423980.2,b-423980.4",
    "date": "2026-04-01",
    "case_ids": ("B-423980.2", "B-423980.4"),
}
MAY_GAO_CITATION_AS_WRITTEN = {
    "source_url": "https://www.gao.gov/products/b-423980.5,b-423980.6",
    "cites_date": "2026-03-31",
    "cites_case_ids": ("B-423980.2", "B-420983.4"),
}


def assess_exact_gao_reconsideration_citation(april, may):
    """Fail closed on altered transcriptions; never invent a separate award."""
    if (type(april) is not dict or type(may) is not dict
            or april != APRIL_GAO_DECISION
            or may != MAY_GAO_CITATION_AS_WRITTEN):
        return "UNKNOWN_ALTERED_PRIMARY_TRANSCRIPTION"
    if (april["date"] != may["cites_date"]
            or april["case_ids"] != may["cites_case_ids"]):
        return "FALSIFIED_EXACT_GAO_RECONSIDERATION_CROSS_REFERENCE"
    return "GAO_REFERENCE_MATCH_ONLY_NOT_AWARD_TRANSACTION"


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


    def test_may_reconsideration_cites_different_docket_and_date(self):
        # Same-publisher inconsistent cross-reference must not be joined as
        # a second procurement, a verified April date, or an Air Force award.
        self.assertEqual(
            assess_exact_gao_reconsideration_citation(
                APRIL_GAO_DECISION, MAY_GAO_CITATION_AS_WRITTEN),
            "FALSIFIED_EXACT_GAO_RECONSIDERATION_CROSS_REFERENCE",
        )
        self.assertNotEqual(APRIL_GAO_DECISION["case_ids"],
                            MAY_GAO_CITATION_AS_WRITTEN["cites_case_ids"])
        self.assertNotEqual(APRIL_GAO_DECISION["date"],
                            MAY_GAO_CITATION_AS_WRITTEN["cites_date"])
        corrected = copy.deepcopy(MAY_GAO_CITATION_AS_WRITTEN)
        corrected["cites_case_ids"] = APRIL_GAO_DECISION["case_ids"]
        corrected["cites_date"] = APRIL_GAO_DECISION["date"]
        self.assertEqual(
            assess_exact_gao_reconsideration_citation(
                APRIL_GAO_DECISION, corrected),
            "UNKNOWN_ALTERED_PRIMARY_TRANSCRIPTION",
        )
        altered = copy.deepcopy(APRIL_GAO_DECISION)
        altered["case_ids"] = MAY_GAO_CITATION_AS_WRITTEN["cites_case_ids"]
        self.assertEqual(
            assess_exact_gao_reconsideration_citation(
                altered, MAY_GAO_CITATION_AS_WRITTEN),
            "UNKNOWN_ALTERED_PRIMARY_TRANSCRIPTION",
        )


# Separate Sep 2026 primary GAO case, verified against both live GAO HTML
# publications 2026-11-07 (NOT independent issuing-agency contract records).
# https://www.gao.gov/products/b-424631
# https://www.gao.gov/docket/b-424631.1
# GAO decision B-424631 twice prints HC101925R007; GAO docket
# B-424631.1 prints HC101925R0007. Never invent a zero-padded join.
GAO_DISA_DECISION = {
    "source_url": "https://www.gao.gov/products/b-424631",
    "decision_date": "2026-09-30",
    "case_id": "B-424631",
    "issuing_agency": "Defense Information Systems Agency",
    "solicitation_as_published": "HC101925R007",
    "reported_awardee": "Modtech Solutions LLC",
    "original_contract_award_number": None,
    "original_award_amount": None,
    "contract_modification_number": None,
    "original_source_bytes_sha256": None,
}
GAO_DISA_DOCKET = {
    "source_url": "https://www.gao.gov/docket/b-424631.1",
    "decision_date": "2026-09-30",
    "case_id": "B-424631.1",
    "issuing_agency": "Defense Information Systems Agency",
    "solicitation_as_published": "HC101925R0007",
    "reported_awardee": None,
    "original_contract_award_number": None,
    "original_award_amount": None,
    "contract_modification_number": None,
    "original_source_bytes_sha256": None,
}


def adjudicate_gao_disa_identifier_conflict(decision, docket, *, asserted_solicitation):
    """One source-bound falsification; not an issuer award or money benchmark."""
    if (type(decision) is not dict or type(docket) is not dict
            or decision != GAO_DISA_DECISION or docket != GAO_DISA_DOCKET):
        return "UNKNOWN_CHANGED_OR_UNREAD_PRIMARY_TRANSCRIPTION"
    if (type(asserted_solicitation) is not str
            or asserted_solicitation not in
            (decision["solicitation_as_published"], docket["solicitation_as_published"])):
        return "REJECT_IDENTIFIER_NOT_FOUND_IN_GAO_PAGES"
    if decision["issuing_agency"] != docket["issuing_agency"]:
        return "UNKNOWN_UNMATCHED_ISSUER"
    if decision["solicitation_as_published"] != docket["solicitation_as_published"]:
        return "FALSIFIED_UNANIMOUS_GAO_EXACT_SOLICITATION_ID"
    return "SAME_GAO_ID_NOT_INDEPENDENT_ISSUER_AWARD"


class GAODisaSeptember2026SolicitationNegativeControl(unittest.TestCase):
    def test_two_original_gao_publications_disagree_exact_identifier(self):
        self.assertEqual(GAO_DISA_DECISION["solicitation_as_published"],
                         "HC101925R007")
        self.assertEqual(GAO_DISA_DOCKET["solicitation_as_published"],
                         "HC101925R0007")
        self.assertEqual(
            adjudicate_gao_disa_identifier_conflict(
                GAO_DISA_DECISION, GAO_DISA_DOCKET,
                asserted_solicitation="HC101925R0007"),
            "FALSIFIED_UNANIMOUS_GAO_EXACT_SOLICITATION_ID")
        self.assertEqual(
            adjudicate_gao_disa_identifier_conflict(
                GAO_DISA_DECISION, GAO_DISA_DOCKET,
                asserted_solicitation="HC101925R007"),
            "FALSIFIED_UNANIMOUS_GAO_EXACT_SOLICITATION_ID")

    def test_dont_pad_identifiers_or_silently_rewrite_source_evidence(self):
        harmonized = copy.deepcopy(GAO_DISA_DECISION)
        harmonized["solicitation_as_published"] = "HC101925R0007"
        self.assertEqual(
            adjudicate_gao_disa_identifier_conflict(
                harmonized, GAO_DISA_DOCKET,
                asserted_solicitation="HC101925R0007"),
            "UNKNOWN_CHANGED_OR_UNREAD_PRIMARY_TRANSCRIPTION")
        self.assertEqual(
            adjudicate_gao_disa_identifier_conflict(
                GAO_DISA_DECISION, GAO_DISA_DOCKET,
                asserted_solicitation="HC101925R0008"),
            "REJECT_IDENTIFIER_NOT_FOUND_IN_GAO_PAGES")

    def test_issuer_award_amount_modifications_and_cash_remain_unknown(self):
        for source in (GAO_DISA_DECISION, GAO_DISA_DOCKET):
            for field in ("original_contract_award_number", "original_award_amount",
                          "contract_modification_number", "original_source_bytes_sha256"):
                self.assertIsNone(source[field])
        self.assertEqual(GAO_DISA_DECISION["reported_awardee"], "Modtech Solutions LLC")
        self.assertEqual(GAO_DISA_DECISION["issuing_agency"],
                         GAO_DISA_DOCKET["issuing_agency"])


if __name__ == "__main__":
    unittest.main()
