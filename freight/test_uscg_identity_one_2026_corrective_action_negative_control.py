"""Original GAO negative control: notice of intent is not a completed termination.

GAO B-424040.2/B-424040.3, April 13, 2026 (official first-party decision):
https://www.gao.gov/products/b-424040.2,b-424040.3

GAO records a 2025-09-30 US Coast Guard award to Parroco under RFP
70Z02325RFAC20001; 2025-11-13 stop-work; 2025-11-25 corrective action;
2025-12-10 notice of intent to terminate; 2026-01-30 DHS approval request.
At its decision, DHS approval was still awaited; the new solicitation was
intended for only the REMAINDER of the requirement. GAO denied the protest.

This is original GAO adjudication evidence, not Coast Guard award-transaction
authentication. GAO reports 2025-09-30 award date; a separately indexed SAM
notice reports 2025-09-29. Original SAM bytes were NOT authenticated, so the
difference remains UNKNOWN. Actual contract PIID, final termination status,
amount/obligations, modifications, settlement, paid recovery, original byte
checksum and reuse rights remain UNKNOWN. No D1, external write, production
change, or product-feature code.
"""
from __future__ import annotations

import copy
import unittest
from datetime import date

GAO = {
    "url": "https://www.gao.gov/products/b-424040.2,b-424040.3",
    "decision_ids": ("B-424040.2", "B-424040.3"),
    "decision_date": "2026-04-13",
    "decision_result": "DENIED",
    "issuing_agency": "Department of Homeland Security, United States Coast Guard",
    "rfp": "70Z02325RFAC20001",
    "initial_awardee": "Parroco Production Group, Inc.",
    "protester": "Identity One, LLC",
    "gao_reported_award_date": "2025-09-30",
    "stop_work_order_date": "2025-11-13",
    "corrective_action_announced": "2025-11-25",
    "notice_of_intent_to_terminate": "2025-12-10",
    "termination_approval_requested": "2026-01-30",
    "termination_at_decision": "AWAITING_DHS_APPROVAL",
    "planned_resolicitation_scope": "REMAINDER_ONLY",
    "original_contract_number": None,
    "verified_award_value_usd": None,
    "verified_modification": None,
    "verified_termination_settlement_usd": None,
    "verified_customer_recovery_usd": None,
    "original_bytes_sha256": None,
    "transaction_reconciled": False,
    "source_specific_reuse_approved": False,
}
# Human-transcribed fixture integrity control, NOT cryptographic source proof.
ANCHOR = tuple(GAO.items())


def candidate() -> dict:
    return {
        "issuing_agency": GAO["issuing_agency"],
        "rfp": GAO["rfp"],
        "awardee": GAO["initial_awardee"],
        "reported_award_date": GAO["gao_reported_award_date"],
        "termination_at_decision": GAO["termination_at_decision"],
        "resolicitation_scope": GAO["planned_resolicitation_scope"],
        "award_contract_number": None,
        "award_amount_usd": None,
        "modification_number": None,
        "settlement_paid_usd": None,
        "customer_recovery_usd": None,
    }


def adjudicate_gao_asof(original: dict, proposed: dict, observed_on: str) -> str:
    """Check published first-party facts only as of a supplied date.

    The decision is not proof of capture at publication or source-byte custody.
    """
    if type(original) is not dict or type(proposed) is not dict:
        return "UNKNOWN_MALFORMED_SOURCE_OR_CANDIDATE"
    if tuple(original.items()) != ANCHOR:
        return "UNKNOWN_UNAUTHENTICATED_ORIGINAL_TRANSCRIPTION"
    try:
        observed = date.fromisoformat(observed_on)
        published = date.fromisoformat(original["decision_date"])
    except (TypeError, ValueError, KeyError):
        return "UNKNOWN_ASOF_DATE"
    if observed < published:
        return "NO_GAO_DECISION_YET_ASOF"
    if (proposed.get("issuing_agency") != original["issuing_agency"]
            or proposed.get("rfp") != original["rfp"]):
        return "UNKNOWN_UNMATCHED_ISSUER_OR_RFP"
    if proposed.get("awardee") != original["initial_awardee"]:
        return "FALSIFIED_PROTESTER_OR_OTHER_FIRM_AS_INITIAL_AWARDEE"
    if proposed.get("reported_award_date") != original["gao_reported_award_date"]:
        return "UNKNOWN_CONFLICTING_AWARD_DATE_NEEDS_ISSUER_TRANSACTION"
    if proposed.get("termination_at_decision") == "COMPLETED":
        return "FALSIFIED_TERMINATION_COMPLETED_BY_GAO_DECISION"
    if proposed.get("termination_at_decision") != "AWAITING_DHS_APPROVAL":
        return "UNKNOWN_TERMINATION_STAGE"
    if proposed.get("resolicitation_scope") == "FULL_ORIGINAL_REQUIREMENT":
        return "FALSIFIED_FULL_REQUIREMENT_RESOLICITATION_AS_GAO_PLAN"
    if proposed.get("resolicitation_scope") != "REMAINDER_ONLY":
        return "UNKNOWN_RESOLICITATION_SCOPE"
    if any(proposed.get(key) is not None for key in (
            "award_contract_number", "award_amount_usd", "modification_number",
            "settlement_paid_usd", "customer_recovery_usd")):
        return "UNKNOWN_UNRECONCILED_TRANSACTION_MODIFICATION_OR_CASH"
    return "GAO_ASOF_CORRECTIVE_ACTION_SUPPORTED_TRANSACTION_UNKNOWN"


class CoastGuardIdentityOne2026OriginalDecisionNegativeControl(unittest.TestCase):
    def test_gao_decision_cannot_be_used_before_2026_04_13(self):
        # Regression: a later adjudication must not become a 2025 lead or
        # retroactively prove that corrective action was completed.
        for asof in ("2025-09-30", "2025-11-25", "2026-04-12"):
            with self.subTest(asof=asof):
                self.assertEqual(adjudicate_gao_asof(
                    GAO, candidate(), observed_on=asof),
                    "NO_GAO_DECISION_YET_ASOF")
        self.assertEqual(adjudicate_gao_asof(
            GAO, candidate(), observed_on="2026-04-13"),
            "GAO_ASOF_CORRECTIVE_ACTION_SUPPORTED_TRANSACTION_UNKNOWN")
        for invalid in ("nonsense", "2026-02-30", None):
            with self.subTest(invalid=invalid):
                self.assertEqual(adjudicate_gao_asof(
                    GAO, candidate(), observed_on=invalid),
                    "UNKNOWN_ASOF_DATE")

    def test_gao_case_supports_past_award_and_pending_action_only(self):
        self.assertEqual(adjudicate_gao_asof(GAO, candidate(), observed_on="2026-11-06"),
            "GAO_ASOF_CORRECTIVE_ACTION_SUPPORTED_TRANSACTION_UNKNOWN")
        self.assertEqual(GAO["stop_work_order_date"], "2025-11-13")
        self.assertEqual(GAO["notice_of_intent_to_terminate"], "2025-12-10")
        self.assertEqual(GAO["termination_approval_requested"], "2026-01-30")
        self.assertFalse(GAO["transaction_reconciled"])

    def test_intent_does_not_prove_completed_termination(self):
        bad = candidate()
        bad["termination_at_decision"] = "COMPLETED"
        self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"),
            "FALSIFIED_TERMINATION_COMPLETED_BY_GAO_DECISION")
        bad["termination_at_decision"] = None
        self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"), "UNKNOWN_TERMINATION_STAGE")

    def test_recompete_remainder_not_entire_original_scope(self):
        bad = candidate()
        bad["resolicitation_scope"] = "FULL_ORIGINAL_REQUIREMENT"
        self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"),
            "FALSIFIED_FULL_REQUIREMENT_RESOLICITATION_AS_GAO_PLAN")
        bad["resolicitation_scope"] = None
        self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"),
            "UNKNOWN_RESOLICITATION_SCOPE")

    def test_protester_and_unrelated_issuer_do_not_become_awardee(self):
        bad = candidate()
        bad["awardee"] = GAO["protester"]
        self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"),
            "FALSIFIED_PROTESTER_OR_OTHER_FIRM_AS_INITIAL_AWARDEE")
        for field, wrong in (("issuing_agency", "Department of the Army"),
                             ("rfp", "70Z02325RFAC20002")):
            bad = candidate()
            bad[field] = wrong
            self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"),
                "UNKNOWN_UNMATCHED_ISSUER_OR_RFP")

    def test_award_date_conflict_stays_unknown_without_issuer_transaction(self):
        bad = candidate()
        bad["reported_award_date"] = "2025-09-29"
        self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"),
            "UNKNOWN_CONFLICTING_AWARD_DATE_NEEDS_ISSUER_TRANSACTION")
        changed_original = copy.deepcopy(GAO)
        changed_original["gao_reported_award_date"] = "2025-09-29"
        self.assertEqual(adjudicate_gao_asof(changed_original, candidate(), observed_on="2026-11-06"),
            "UNKNOWN_UNAUTHENTICATED_ORIGINAL_TRANSCRIPTION")

    def test_contract_amount_modifications_and_cash_remain_unknown(self):
        for key, unsupported in (
            ("award_contract_number", "70Z02325CFAC20001"),
            ("award_amount_usd", 1853343.74),
            ("modification_number", "P00001"),
            ("settlement_paid_usd", 1),
            ("customer_recovery_usd", 1),
        ):
            with self.subTest(key=key):
                bad = candidate()
                bad[key] = unsupported
                self.assertEqual(adjudicate_gao_asof(GAO, bad, observed_on="2026-11-06"),
                    "UNKNOWN_UNRECONCILED_TRANSACTION_MODIFICATION_OR_CASH")
        self.assertIsNone(GAO["original_contract_number"])
        self.assertIsNone(GAO["original_bytes_sha256"])
        self.assertFalse(GAO["source_specific_reuse_approved"])


if __name__ == "__main__":
    unittest.main()
