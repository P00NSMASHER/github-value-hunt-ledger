import hashlib
import unittest

from business_os.learning.promotion import (
    EvaluationEvidence,
    GlobalSkillRegistry,
    PromotionError,
    PromotionGate,
    SkillCandidate,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


class PromotionGateTests(unittest.TestCase):
    def setUp(self):
        self.candidate = SkillCandidate(
            candidate_id="cand-1",
            skill_id="prospect-search",
            baseline_version="v1",
            candidate_version="v2",
            artifact_sha256=digest("artifact-v2"),
            mutation_scope="query_strategy",
            proposer="research-agent",
        )
        self.gate = PromotionGate(minimum_delta=0.05)

    def good_evidence(self, include_canary=False):
        rows = [
            EvaluationEvidence(
                "confirm", digest("confirm"), 0.60, 0.70, True, verifier="verifier-a"
            ),
            EvaluationEvidence(
                "heldout", digest("heldout"), 0.55, 0.66, True, verifier="verifier-b"
            ),
            EvaluationEvidence(
                "adversarial",
                digest("adversarial"),
                0.50,
                0.58,
                True,
                verifier="verifier-c",
            ),
        ]
        if include_canary:
            rows.append(
                EvaluationEvidence(
                    "canary",
                    digest("canary"),
                    0.62,
                    0.69,
                    True,
                    verifier="verifier-d",
                )
            )
        return tuple(rows)

    def test_requires_heldout_evidence(self):
        evidence = (
            EvaluationEvidence(
                "train", digest("train"), 0.4, 0.9, True, verifier="verifier"
            ),
        )
        decision = self.gate.evaluate(self.candidate, evidence)
        self.assertEqual("REJECTED", decision.state)
        self.assertIn("missing required split", decision.reasons[0])

    def test_good_candidate_becomes_ready_for_canary_not_global(self):
        decision = self.gate.evaluate(self.candidate, self.good_evidence())
        self.assertEqual("READY_FOR_CANARY", decision.state)

    def test_canary_makes_candidate_global_eligible_but_not_promoted(self):
        decision = self.gate.evaluate(
            self.candidate,
            self.good_evidence(include_canary=True),
        )
        self.assertEqual("GLOBAL_ELIGIBLE", decision.state)
        registry = GlobalSkillRegistry()
        self.assertIsNone(registry.current_version("prospect-search"))

    def test_integrator_must_explicitly_promote(self):
        decision = self.gate.evaluate(
            self.candidate,
            self.good_evidence(include_canary=True),
        )
        registry = GlobalSkillRegistry()
        with self.assertRaises(PermissionError):
            registry.promote(
                self.candidate,
                decision,
                approver_role="EXECUTOR",
                approver_id="agent-x",
            )
        receipt = registry.promote(
            self.candidate,
            decision,
            approver_role="INTEGRATOR",
            approver_id="human-review",
        )
        self.assertEqual("v2", registry.current_version("prospect-search"))
        self.assertEqual(64, len(receipt["sha256"]))

    def test_hard_regression_rejects(self):
        rows = list(self.good_evidence())
        rows[1] = EvaluationEvidence(
            "heldout",
            digest("heldout"),
            0.55,
            0.90,
            True,
            hard_regressions=1,
            verifier="verifier-b",
        )
        decision = self.gate.evaluate(self.candidate, tuple(rows))
        self.assertEqual("REJECTED", decision.state)
        self.assertTrue(any("hard regression" in x for x in decision.reasons))

    def test_shared_dataset_between_splits_rejects(self):
        shared = digest("same")
        rows = (
            EvaluationEvidence("confirm", shared, 0.5, 0.7, True, verifier="a"),
            EvaluationEvidence("heldout", shared, 0.5, 0.7, True, verifier="b"),
            EvaluationEvidence(
                "adversarial", digest("adv"), 0.5, 0.7, True, verifier="c"
            ),
        )
        decision = self.gate.evaluate(self.candidate, rows)
        self.assertEqual("REJECTED", decision.state)
        self.assertTrue(any("not independent" in x for x in decision.reasons))

    def test_proposer_cannot_verify_own_promotion(self):
        rows = list(self.good_evidence())
        rows[0] = EvaluationEvidence(
            "confirm",
            digest("confirm"),
            0.60,
            0.80,
            True,
            verifier="research-agent",
        )
        decision = self.gate.evaluate(self.candidate, tuple(rows))
        self.assertEqual("REJECTED", decision.state)
        self.assertTrue(any("independently" in x for x in decision.reasons))

    def test_candidate_must_change_version(self):
        with self.assertRaises(PromotionError):
            SkillCandidate(
                candidate_id="bad",
                skill_id="x",
                baseline_version="v1",
                candidate_version="v1",
                artifact_sha256=digest("x"),
                mutation_scope="prompt",
                proposer="a",
            )


if __name__ == "__main__":
    unittest.main()
