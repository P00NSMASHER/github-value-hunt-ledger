"""Source-bound *research-only* GAO remedy supersession negative control.

This is NOT an award-identity, refund, or paid-customer accuracy benchmark.
The two factsheets are hand-transcribed from original GAO decision pages; no
original HTML bytes, solicitation/award instruments, or bank records are held.
"""
import copy
import json
import unittest
from datetime import date
from pathlib import Path

FIXTURE = Path(__file__).with_name("fixtures") / "gao_b423993_remedy_source_v1.json"
FIRST = "https://www.gao.gov/products/b-423993,b-423993.2"
LATER = "https://www.gao.gov/products/b-423993.4,b-423993.5"
NEGATIVE = "FALSIFIED_STALE_RECOMPETITION_RECOMMENDATION"
UNKNOWN = "UNKNOWN_SOURCE_OR_IDENTITY_MISMATCH"
UNVERIFIED = "UNVERIFIED_AWARD_OR_CASH_PROMOTION"


def assess_gao_remedy_case(d):
    """Fail closed on missing identity, supersession, or original custody."""
    try:
        a, b = d["original_gao_decision"], d["later_gao_decision"]
        custody = d["custody"]
        source_ok = (
            d["schema_version"] == 1
            and d["source_issuer"] == "U.S. Government Accountability Office"
            and d["procurement_issuer"] == "U.S. Army Corps of Engineers"
            and d["solicitation"] == "W912DY-25-Q-A101"
            and d["awardee_name_reported"] == "Export 220Volt, Inc."
            and d["award_date_reported"] == "2025-09-30"
            and d["solicitation_amendment_count_reported"] == 10
            and a["url"] == FIRST and a["numbers"] == ["B-423993", "B-423993.2"]
            and b["url"] == LATER and b["numbers"] == ["B-423993.4", "B-423993.5"]
            and a["date"] == "2026-02-18" and b["date"] == "2026-05-13"
            and date.fromisoformat(d["award_date_reported"])
                < date.fromisoformat(a["date"]) < date.fromisoformat(b["date"])
            and a["protest_merits"] == "SUSTAINED"
            and b["protest_merits"] == "SUSTAINED_UNCHANGED"
            and a["recommendation"]
                == "REOPEN_REVISE_EVALUATE_AND_MAKE_NEW_AWARD_DECISION"
            and b["replaces_reopen_recommendation"] is True
            and b["recommendation"]
                == "REIMBURSE_QUOTATION_PREPARATION_AND_PROTEST_COSTS"
            and b["reason"]
                == "RECOMPETITION_NO_LONGER_FEASIBLE_AS_CONTRACT_SUBSTANTIALLY_PERFORMED"
            and a["awardee_final_quotation_usd"] == "2039912.11"
        )
    except (KeyError, TypeError, ValueError):
        return UNKNOWN
    if not source_ok:
        return UNKNOWN
    # In GAO's original source, the quote was NOT bank evidence or an
    # independently acquired signed contract award amount.
    if (d["awardee_uei"] is not None
        or d["award_contract_piid"] is not None
        or d["independently_verified_contract_award_amount_usd"] is not None
        or d["independently_verified_contract_modifications"] is not None
        or a["actual_award_payment_usd"] is not None
        or b["verified_costs_paid_usd"] is not None
        or b["verified_reaward_to_protester"] is not None):
        return UNVERIFIED
    if (custody["original_http_response_bytes_retained"]
        or custody["original_source_sha256"] is not None
        or custody["signed_original_award_instrument_available"]
        or custody["independent_award_transaction_row_available"]
        or custody["customer_recovery_receipt_available"]
        or custody["commercial_reuse_permission_independently_confirmed"]):
        return UNVERIFIED
    return NEGATIVE


class GAB423993DecisionSupersessionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_original_gao_pair_falsifies_stale_recompetition_prediction(self):
        d = self.source
        self.assertEqual(assess_gao_remedy_case(d), NEGATIVE)
        self.assertEqual(d["record_type"],
                         "HUMAN_TRANSCRIBED_OFFICIAL_GAO_DECISION_TIMELINE_NOT_CONTRACT_OR_AWARD_RECORD")
        self.assertEqual(d["bench_status"],
                         "DECISION_LEVEL_NEGATIVE_CONTROL_NOT_A_VALIDATED_NOTICE_AWARD_BENCHMARK")
        self.assertNotEqual(d["original_gao_decision"]["recommendation"],
                            d["later_gao_decision"]["recommendation"])
        self.assertIsNone(d["award_contract_piid"])
        self.assertIsNone(d["independently_verified_contract_modifications"])

    def test_wrong_solicitation_issuer_or_awardee_never_join(self):
        for key, replacement in (
            ("solicitation", "W912DY-25-Q-A102"),
            ("procurement_issuer", "U.S. Army Corps of Engineers, wrong office"),
            ("awardee_name_reported", "Effective Communication Strategies, LLC")
        ):
            with self.subTest(field=key):
                d = copy.deepcopy(self.source)
                d[key] = replacement
                self.assertEqual(assess_gao_remedy_case(d), UNKNOWN)

    def test_reversed_or_rewritten_decision_is_rejected(self):
        for key, val in (("date", "2026-01-01"), ("replaces_reopen_recommendation", False),
                         ("recommendation", "REAWARD_TO_PROTESTER")):
            with self.subTest(field=key):
                d = copy.deepcopy(self.source)
                d["later_gao_decision"][key] = val
                self.assertEqual(assess_gao_remedy_case(d), UNKNOWN)

    def test_dont_conflate_final_quotation_and_signed_award(self):
        d = copy.deepcopy(self.source)
        d["independently_verified_contract_award_amount_usd"] = "2039912.11"
        self.assertEqual(assess_gao_remedy_case(d), UNVERIFIED)

    def test_dont_infer_reaward_or_paid_costs_from_recommendation(self):
        for key, val in (("verified_reaward_to_protester", True),
                         ("verified_costs_paid_usd", "500.00")):
            with self.subTest(field=key):
                d = copy.deepcopy(self.source)
                d["later_gao_decision"][key] = val
                self.assertEqual(assess_gao_remedy_case(d), UNVERIFIED)

    def test_a_claimed_source_checksum_or_award_row_needs_originals(self):
        for key, val in (("original_source_sha256", "a" * 64),
                         ("independent_award_transaction_row_available", True)):
            with self.subTest(field=key):
                d = copy.deepcopy(self.source)
                d["custody"][key] = val
                self.assertEqual(assess_gao_remedy_case(d), UNVERIFIED)


if __name__ == "__main__":
    unittest.main()
