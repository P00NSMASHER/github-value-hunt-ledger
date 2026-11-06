"""USACE Baltimore primary-source negative control: one RFQ, multiple BPAs.

Official SAM.gov issuer records (read from public publisher-indexed pages,
2026-11-06; human transcription, original source bytes NOT preserved):
  2026-06-29 solicitation / 2026-07-08 amendment:
  https://sam.gov/opp/4a9d13247570492ab775b43226a901b1/view
  2026-09-17 published award notice for Greenfield:
  https://sam.gov/opp/1924a376df164e929725277d85d4e355/view
  2026-09-17 published award notice for Integrity:
  https://sam.gov/opp/5f9f3aec382f4c41970a1682e94350a5/view

Both first-party AWARD notices explicitly reference solicitation W912DR26QA051
and say they are one of THREE master agreements. Two independently named
contractors/UEIs and amounts falsify a one-solicitation-one-awardee join.
These are BPA values, NOT confirmed payments or customer recoveries.
A third award's identity, actual orders, modifications, obligations, original
PDF digests, transaction reconciliation and reuse rights remain UNKNOWN.
Offline research QA only; no D1 reads, downstream release or outreach.
"""
import copy
import unittest
from datetime import datetime, timezone

from freight.capturebrief_sam_fy2027_asof import assess_cross_source_chronology

SOL = {
    "notice": "W912DR26QA051", "issuer": "DEPT OF THE ARMY",
    "office": "W2SD ENDIST BALTIMORE", "posted": "2026-06-29",
    "updated": "2026-07-08",
}
AWARDS = (
    {
        "notice": "W912DR26AA003", "award": "W912DR26AA003",
        "related": "W912DR26QA051",
        "issuer": "DEPT OF THE ARMY", "office": "W2SD ENDIST BALTIMORE",
        "uei": "F839PKJPFLZ4", "contractor": "GREENFIELD INTERNATIONAL CORP.",
        "ceiling_usd": 4_979_445, "signed": "2026-09-16",
        "published": "2026-09-17",
        "modification": None,
    },
    {
        "notice": "W912DR26AA004", "award": "W912DR26AA004",
        "related": "W912DR26QA051",
        "issuer": "DEPT OF THE ARMY", "office": "W2SD ENDIST BALTIMORE",
        "uei": "S64BBMTMJTB5", "contractor": "Integrity Core Alliance LLC",
        "ceiling_usd": 2_853_298, "signed": "2026-09-17",
        "published": "2026-09-17",
        "modification": None,
    },
)
OBSERVED = datetime(2026, 11, 6, 9, 47, tzinfo=timezone.utc)

# Publisher-indexed primary-notice transcription anchors, independently
# checked against the three official SAM.gov pages on 2026-11-06.
# This prevents a claimant from changing BOTH the test source and the claim
# to invent two matching awards. Not a hash or source-rights clearance.
SOL_SOURCE_ANCHORS = {
    "notice": "W912DR26QA051", "issuer": "DEPT OF THE ARMY",
    "office": "W2SD ENDIST BALTIMORE", "posted": "2026-06-29",
    "updated": "2026-07-08",
}
AWARD_SOURCE_ANCHORS = {
    "W912DR26AA003": {
        "notice": "W912DR26AA003", "award": "W912DR26AA003",
        "related": "W912DR26QA051", "issuer": "DEPT OF THE ARMY",
        "office": "W2SD ENDIST BALTIMORE", "uei": "F839PKJPFLZ4",
        "contractor": "GREENFIELD INTERNATIONAL CORP.",
        "ceiling_usd": 4_979_445, "signed": "2026-09-16",
        "published": "2026-09-17",
    },
    "W912DR26AA004": {
        "notice": "W912DR26AA004", "award": "W912DR26AA004",
        "related": "W912DR26QA051", "issuer": "DEPT OF THE ARMY",
        "office": "W2SD ENDIST BALTIMORE", "uei": "S64BBMTMJTB5",
        "contractor": "Integrity Core Alliance LLC",
        "ceiling_usd": 2_853_298, "signed": "2026-09-17",
        "published": "2026-09-17",
    },
}

def source_bound_candidates(sol, awards):
    """Count issuer/office/related-ID-consistent issuer notices, not transactions."""
    if not isinstance(sol, dict) or not isinstance(awards, (list, tuple)):
        return None
    if not all(isinstance(sol.get(k), str) and sol[k] for k in
               ("notice", "issuer", "office", "posted")):
        return None
    # A coordinated source+claim substitution must not inherit the verified
    # notice-bound conclusion. Only these two checked public award notices are
    # admissible in this fixture; the reported third award stays UNKNOWN.
    if any(sol.get(k) != v for k, v in SOL_SOURCE_ANCHORS.items()):
        return None
    if len(awards) != len(AWARD_SOURCE_ANCHORS):
        return None
    result = []
    for a in awards:
        if not isinstance(a, dict):
            return None
        expected = AWARD_SOURCE_ANCHORS.get(a.get("award"))
        if expected is None or any(a.get(k) != v for k, v in expected.items()):
            return None
        if any(not isinstance(a.get(k), str) or not a[k] for k in
               ("notice", "award", "related", "issuer", "office",
                "uei", "contractor", "signed", "published")):
            return None
        if type(a.get("ceiling_usd")) is not int or a["ceiling_usd"] <= 0:
            return None
        if a["issuer"] != sol["issuer"] or a["office"] != sol["office"]:
            return None
        if a["notice"] != a["award"] or a["related"] != sol["notice"]:
            return None
        if not sol["posted"] < a["signed"] <= a["published"]:
            return None
        result.append(a)
    if len({a["award"] for a in result}) != len(result):
        return None
    return result

def adjudicate_claim(sol, awards, proposed=None):
    """Fail closed: missing recipient does not mean no award, matching is not payment."""
    matches = source_bound_candidates(sol, awards)
    if matches is None or len(matches) == 0:
        return "UNKNOWN_OR_CONFLICTING_ORIGINAL"
    if proposed is None:
        return ("FALSIFIED_UNIQUE_AWARDEE_JOIN" if len(matches) > 1
                else "SINGLE_ISSUER_NOTICE_NOT_TRANSACTION")
    required = ("award", "uei", "contractor", "ceiling_usd", "signed")
    if not isinstance(proposed, dict) or any(k not in proposed for k in required):
        return "UNKNOWN_INCOMPLETE_PROPOSED_IDENTITY"
    matches = [a for a in matches
               if all(type(proposed[k]) is type(a[k]) and proposed[k] == a[k]
                      for k in required)]
    return ("ISSUER_NOTICE_CONSISTENT_TRANSACTION_UNKNOWN"
            if len(matches) == 1 else "UNKNOWN_OR_MISMATCHED_AWARDEE")

class UsaceMultipleBpaOriginalSourceNegativeControl(unittest.TestCase):
    def test_two_official_original_awards_falsify_unique_awardee_join(self):
        self.assertEqual(adjudicate_claim(SOL, AWARDS),
                         "FALSIFIED_UNIQUE_AWARDEE_JOIN")
        self.assertEqual({a["related"] for a in AWARDS}, {SOL["notice"]})
        self.assertEqual(len({a["uei"] for a in AWARDS}), 2)
        self.assertEqual(len({a["award"] for a in AWARDS}), 2)

    def test_exact_award_identity_distinguishes_each_record_without_cash_claim(self):
        for a in AWARDS:
            self.assertEqual(adjudicate_claim(SOL, AWARDS, a),
                             "ISSUER_NOTICE_CONSISTENT_TRANSACTION_UNKNOWN")
        self.assertNotEqual(AWARDS[0]["ceiling_usd"], AWARDS[1]["ceiling_usd"])

    def test_naive_join_must_not_attribute_one_recipient_to_other_award(self):
        mixed = copy.deepcopy(AWARDS[0])
        mixed["uei"] = AWARDS[1]["uei"]
        self.assertEqual(adjudicate_claim(SOL, AWARDS, mixed),
                         "UNKNOWN_OR_MISMATCHED_AWARDEE")
        mixed = copy.deepcopy(AWARDS[1])
        mixed["ceiling_usd"] = AWARDS[0]["ceiling_usd"]
        self.assertEqual(adjudicate_claim(SOL, AWARDS, mixed),
                         "UNKNOWN_OR_MISMATCHED_AWARDEE")

    def test_issuer_or_solicitation_mismatch_fails_closed(self):
        altered = [copy.deepcopy(a) for a in AWARDS]
        altered[1]["related"] = "W912DR26QA052"
        self.assertEqual(adjudicate_claim(SOL, altered),
                         "UNKNOWN_OR_CONFLICTING_ORIGINAL")
        altered = [copy.deepcopy(a) for a in AWARDS]
        altered[1]["office"] = "UNRELATED CONTRACTING OFFICE"
        self.assertEqual(adjudicate_claim(SOL, altered),
                         "UNKNOWN_OR_CONFLICTING_ORIGINAL")

    def test_coordinated_source_and_claim_mutations_fail_closed(self):
        # Before this guard, changing BOTH a local award source and its
        # proposed recipient or amount left FALSIFIED_UNIQUE_AWARDEE_JOIN
        # unchanged, even though those bytes were never original evidence.
        for field, fake in (
            ("contractor", "FABRICATED COMPANY INC."),
            ("uei", "FAKEENTITY000"),
            ("ceiling_usd", 9_999_999),
            ("award", "W912DR26AA005"),
            ("related", "W912DR26QA052"),
            ("signed", "2026-09-18"),
        ):
            with self.subTest(field=field):
                changed = [copy.deepcopy(a) for a in AWARDS]
                changed[0][field] = fake
                if field == "award":
                    changed[0]["notice"] = fake
                self.assertEqual(adjudicate_claim(SOL, changed),
                                 "UNKNOWN_OR_CONFLICTING_ORIGINAL")
        changed_sol = copy.deepcopy(SOL)
        changed_sol["notice"] = "W912DR26QA052"
        changed = [copy.deepcopy(a) for a in AWARDS]
        for a in changed:
            a["related"] = changed_sol["notice"]
        self.assertEqual(adjudicate_claim(changed_sol, changed),
                         "UNKNOWN_OR_CONFLICTING_ORIGINAL")

    def test_unverified_third_award_cannot_inherit_original_source_label(self):
        third = copy.deepcopy(AWARDS[0])
        third["award"] = third["notice"] = "W912DR26AA005"
        third["uei"] = "UNVERIFIED"
        self.assertEqual(adjudicate_claim(SOL, (*AWARDS, third)),
                         "UNKNOWN_OR_CONFLICTING_ORIGINAL")

    def test_real_observation_after_award_not_historical_preaward_capture(self):
        notice = {"solicitation_number": SOL["notice"], "agency_code": "DOD",
                  "office": SOL["office"], "posted_date": SOL["updated"]}
        for a in AWARDS:
            award = {"solicitation_identifier": a["related"],
                     "matched_issuer_agency_code": "DOD",
                     "matched_issuer_office": a["office"],
                     "award_date_signed": a["signed"]}
            self.assertEqual(assess_cross_source_chronology(
                notice, award, source_observed_at=OBSERVED),
                "ARCHIVE_OBSERVED_AFTER_AWARD_NOT_ASOF")

    def test_missing_third_award_and_modifications_are_unknown_not_zero(self):
        self.assertEqual(len(AWARDS), 2)
        self.assertTrue(all(a["modification"] is None for a in AWARDS))
        self.assertNotIn("actual_paid_usd", AWARDS[0])
        self.assertNotIn("verified_customer_recovery_usd", AWARDS[1])
        self.assertEqual(adjudicate_claim(SOL, AWARDS, {"award": AWARDS[0]["award"]}),
                         "UNKNOWN_INCOMPLETE_PROPOSED_IDENTITY")

if __name__ == "__main__":
    unittest.main()
