import hashlib
import unittest

from business_os.evidence.truth_engine import (
    Claim,
    EvidenceAction,
    EvidenceItem,
    ProofObligation,
    TruthEngine,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class TruthEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = TruthEngine()
        self.claim = Claim(
            "claim-1",
            "Freight invoice 100",
            "Invoice 100 contains a recoverable overcharge",
        )
        self.obligation = ProofObligation(
            key="contract_rate",
            description="Controlling contract rate supports the overcharge",
            allowed_authorities=("PRIMARY_CONTRACT", "VERIFIED_LEDGER"),
            max_age_seconds=1000,
        )

    def evidence(
        self,
        evidence_id,
        *,
        stance="SUPPORTS",
        authority="PRIMARY_CONTRACT",
        group="contract",
        observed_at=100,
        admissible=True,
        valid_until=None,
    ):
        return EvidenceItem(
            evidence_id=evidence_id,
            obligation_key="contract_rate",
            stance=stance,
            authority=authority,
            source_id=evidence_id,
            independence_group=group,
            observed_at=observed_at,
            source_ref=f"source/{evidence_id}",
            source_sha256=digest(evidence_id),
            admissible=admissible,
            valid_until=valid_until,
        )

    def test_no_evidence_is_unknown_not_false(self):
        receipt = self.engine.evaluate(
            self.claim, (self.obligation,), (), evaluated_at=200
        )
        self.assertEqual("UNKNOWN", receipt.verdict)
        self.assertEqual("MISSING", receipt.obligation_findings[0].status)

    def test_current_authoritative_support_proves_claim(self):
        receipt = self.engine.evaluate(
            self.claim,
            (self.obligation,),
            (self.evidence("e1"),),
            evaluated_at=200,
        )
        self.assertEqual("PROVEN", receipt.verdict)
        self.assertEqual("SATISFIED", receipt.obligation_findings[0].status)

    def test_stale_evidence_is_not_proof(self):
        receipt = self.engine.evaluate(
            self.claim,
            (self.obligation,),
            (self.evidence("e1", observed_at=0),),
            evaluated_at=2000,
        )
        self.assertEqual("NOT_PROVEN", receipt.verdict)
        finding = receipt.obligation_findings[0]
        self.assertEqual("STALE_OR_INADMISSIBLE", finding.status)
        self.assertEqual(("e1",), finding.rejected_evidence_ids)

    def test_unapproved_authority_is_not_proof(self):
        receipt = self.engine.evaluate(
            self.claim,
            (self.obligation,),
            (self.evidence("model", authority="MODEL"),),
            evaluated_at=200,
        )
        self.assertEqual("NOT_PROVEN", receipt.verdict)
        self.assertEqual(
            "STALE_OR_INADMISSIBLE", receipt.obligation_findings[0].status
        )

    def test_contradiction_is_preserved_and_contested(self):
        evidence = (
            self.evidence("support", stance="SUPPORTS", group="contract"),
            self.evidence("contradiction", stance="CONTRADICTS", group="ledger"),
        )
        receipt = self.engine.evaluate(
            self.claim, (self.obligation,), evidence, evaluated_at=200
        )
        self.assertEqual("CONTESTED", receipt.verdict)
        finding = receipt.obligation_findings[0]
        self.assertEqual("CONFLICTED", finding.status)
        self.assertEqual(("support",), finding.supporting_evidence_ids)
        self.assertEqual(
            ("contradiction",), finding.contradicting_evidence_ids
        )

    def test_independence_requirement_is_enforced(self):
        obligation = ProofObligation(
            key="contract_rate",
            description="Two independent corroborating sources",
            allowed_authorities=("PRIMARY_CONTRACT", "VERIFIED_LEDGER"),
            min_supporting_sources=2,
            min_independent_groups=2,
        )
        same_group = (
            self.evidence("e1", group="same"),
            self.evidence("e2", group="same"),
        )
        receipt = self.engine.evaluate(
            self.claim, (obligation,), same_group, evaluated_at=200
        )
        self.assertEqual("NOT_PROVEN", receipt.verdict)
        self.assertEqual(
            "INSUFFICIENT_INDEPENDENCE",
            receipt.obligation_findings[0].status,
        )

        independent = same_group + (
            self.evidence("e3", authority="VERIFIED_LEDGER", group="ledger"),
        )
        receipt = self.engine.evaluate(
            self.claim, (obligation,), independent, evaluated_at=200
        )
        self.assertEqual("PROVEN", receipt.verdict)

    def test_future_observation_is_rejected(self):
        receipt = self.engine.evaluate(
            self.claim,
            (self.obligation,),
            (self.evidence("future", observed_at=500),),
            evaluated_at=200,
        )
        self.assertEqual("NOT_PROVEN", receipt.verdict)
        self.assertEqual(
            ("future",), receipt.obligation_findings[0].rejected_evidence_ids
        )

    def test_bad_source_digest_fails_closed(self):
        with self.assertRaises(ValueError):
            EvidenceItem(
                evidence_id="bad",
                obligation_key="contract_rate",
                stance="SUPPORTS",
                authority="PRIMARY_CONTRACT",
                source_id="bad",
                independence_group="x",
                observed_at=100,
                source_ref="bad",
                source_sha256="not-a-digest",
            )

    def test_receipt_identity_changes_when_evidence_changes(self):
        a = self.engine.evaluate(
            self.claim,
            (self.obligation,),
            (self.evidence("e1"),),
            evaluated_at=200,
        )
        b = self.engine.evaluate(
            self.claim,
            (self.obligation,),
            (self.evidence("e2"),),
            evaluated_at=200,
        )
        self.assertNotEqual(a.evidence_set_sha256, b.evidence_set_sha256)
        self.assertNotEqual(a.sha256, b.sha256)

    def test_next_best_evidence_uses_counterfactual_proof_gain(self):
        second = ProofObligation(
            key="payment",
            description="Payment evidence establishes actual payment",
            allowed_authorities=("BANK",),
        )
        existing = (self.evidence("e1"),)
        actions = (
            EvidenceAction(
                "get-bank-proof",
                "payment",
                "Obtain bank settlement record",
                authority="BANK",
                independence_group="bank",
                cost_usd=5,
            ),
            EvidenceAction(
                "wrong-authority",
                "payment",
                "Ask an unverified model",
                authority="MODEL",
                independence_group="model",
                cost_usd=0,
            ),
            EvidenceAction(
                "unavailable",
                "payment",
                "Unavailable bank request",
                authority="BANK",
                independence_group="bank-2",
                cost_usd=1,
                available=False,
            ),
        )
        ranked = self.engine.rank_next_evidence(
            self.claim,
            (self.obligation, second),
            existing,
            actions,
            evaluated_at=200,
        )
        self.assertEqual(["get-bank-proof"], [x.action.action_id for x in ranked])
        self.assertEqual("NOT_PROVEN", ranked[0].baseline_verdict)
        self.assertEqual("PROVEN", ranked[0].counterfactual_verdict)
        self.assertGreater(ranked[0].potential_decision_gain, 0)

    def test_duplicate_independence_group_is_not_recommended(self):
        obligation = ProofObligation(
            key="contract_rate",
            description="Need two independent sources",
            allowed_authorities=("PRIMARY_CONTRACT", "VERIFIED_LEDGER"),
            min_supporting_sources=2,
            min_independent_groups=2,
        )
        existing = (self.evidence("e1", group="contract"),)
        actions = (
            EvidenceAction(
                "duplicate",
                "contract_rate",
                "Get another copy from same source family",
                authority="PRIMARY_CONTRACT",
                independence_group="contract",
                cost_usd=0,
            ),
            EvidenceAction(
                "independent",
                "contract_rate",
                "Get verified ledger corroboration",
                authority="VERIFIED_LEDGER",
                independence_group="ledger",
                cost_usd=1,
            ),
        )
        ranked = self.engine.rank_next_evidence(
            self.claim,
            (obligation,),
            existing,
            actions,
            evaluated_at=200,
        )
        self.assertEqual(["independent"], [x.action.action_id for x in ranked])


if __name__ == "__main__":
    unittest.main()
