import hashlib
import tempfile
import unittest
from pathlib import Path

from ai_business_os.persistent_agents.runtime import AgentRuntime
from ai_business_os.self_improvement import SelfImprovementGate, SkillPromotionError


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SelfImprovementGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = AgentRuntime(Path(self.tmp.name) / "runtime.sqlite3")
        self.gate = SelfImprovementGate(self.runtime)
        self.curator = self.runtime.register_agent("skill-curator")
        self.proposer = self.runtime.register_agent("skill-proposer")
        self.verifier = self.runtime.register_agent("skill-verifier")
        self.gate.register_champion(
            skill_key="lead-research",
            version="v1",
            artifact_hash=sha("champion-v1"),
            curator_agent_id=self.curator,
            evidence={"source": "baseline benchmark"},
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def _candidate(self, min_delta=0.01):
        candidate = self.gate.propose_candidate(
            skill_key="lead-research",
            candidate_version="v2",
            candidate_artifact_hash=sha("candidate-v2"),
            mutation={"change": "use a narrower account qualification query"},
            proposer_agent_id=self.proposer,
            verifier_agent_id=self.verifier,
            curator_agent_id=self.curator,
            min_heldout_delta=min_delta,
        )
        self.gate.freeze_evaluation_manifest(
            candidate,
            dev_task_ids=["dev-1", "dev-2"],
            heldout_task_ids=["h-1", "h-2", "h-3", "h-4", "h-5"],
        )
        return candidate

    def _score_all(self, candidate, heldout_delta=0.10, hard_regression_task=None):
        for task in ["dev-1", "dev-2"]:
            self.gate.record_evaluation(
                candidate,
                verifier_agent_id=self.verifier,
                split="dev",
                task_id=task,
                baseline_score=0.50,
                candidate_score=0.60,
                hard_regression=(task == hard_regression_task),
                evidence={"run": task},
            )
        for task in ["h-1", "h-2", "h-3", "h-4", "h-5"]:
            self.gate.record_evaluation(
                candidate,
                verifier_agent_id=self.verifier,
                split="heldout",
                task_id=task,
                baseline_score=0.50,
                candidate_score=0.50 + heldout_delta,
                hard_regression=(task == hard_regression_task),
                evidence={"run": task},
            )

    def test_candidate_is_inert_until_full_promotion(self):
        candidate = self._candidate()
        self._score_all(candidate)
        verified = self.gate.assess_candidate(
            candidate,
            verifier_agent_id=self.verifier,
        )
        self.assertEqual(verified["status"], "VERIFIED")
        self.assertEqual(self.gate.get_active_skill("lead-research")["version"], "v1")

    def test_proposer_cannot_be_verifier(self):
        with self.assertRaises(SkillPromotionError):
            self.gate.propose_candidate(
                skill_key="lead-research",
                candidate_version="v2",
                candidate_artifact_hash=sha("candidate-v2"),
                mutation={"change": "x"},
                proposer_agent_id=self.proposer,
                verifier_agent_id=self.proposer,
                curator_agent_id=self.curator,
            )

    def test_split_leakage_fails_closed(self):
        candidate = self.gate.propose_candidate(
            skill_key="lead-research",
            candidate_version="v2",
            candidate_artifact_hash=sha("candidate-v2"),
            mutation={"change": "x"},
            proposer_agent_id=self.proposer,
            verifier_agent_id=self.verifier,
            curator_agent_id=self.curator,
        )
        with self.assertRaises(SkillPromotionError):
            self.gate.freeze_evaluation_manifest(
                candidate,
                dev_task_ids=["shared", "dev-2"],
                heldout_task_ids=["shared", "h-2", "h-3", "h-4", "h-5"],
            )

    def test_unfrozen_task_cannot_be_scored(self):
        candidate = self._candidate()
        with self.assertRaises(SkillPromotionError):
            self.gate.record_evaluation(
                candidate,
                verifier_agent_id=self.verifier,
                split="heldout",
                task_id="not-in-manifest",
                baseline_score=0.4,
                candidate_score=0.8,
                hard_regression=False,
                evidence={"run": "bad"},
            )

    def test_missing_results_block_assessment(self):
        candidate = self._candidate()
        self.gate.record_evaluation(
            candidate,
            verifier_agent_id=self.verifier,
            split="dev",
            task_id="dev-1",
            baseline_score=0.5,
            candidate_score=0.6,
            hard_regression=False,
            evidence={"run": "partial"},
        )
        with self.assertRaises(SkillPromotionError):
            self.gate.assess_candidate(candidate, verifier_agent_id=self.verifier)

    def test_hard_regression_quarantines_candidate(self):
        candidate = self._candidate()
        self._score_all(candidate, hard_regression_task="h-3")
        assessed = self.gate.assess_candidate(
            candidate,
            verifier_agent_id=self.verifier,
        )
        self.assertEqual(assessed["status"], "QUARANTINED")
        self.assertEqual(self.gate.get_active_skill("lead-research")["version"], "v1")

    def test_heldout_underperformance_rejects_candidate(self):
        candidate = self._candidate(min_delta=0.05)
        self._score_all(candidate, heldout_delta=0.01)
        assessed = self.gate.assess_candidate(
            candidate,
            verifier_agent_id=self.verifier,
        )
        self.assertEqual(assessed["status"], "REJECTED")
        self.assertEqual(self.gate.get_active_skill("lead-research")["version"], "v1")

    def test_three_independent_canaries_then_curator_promotion(self):
        candidate = self._candidate()
        self._score_all(candidate)
        assessed = self.gate.assess_candidate(
            candidate,
            verifier_agent_id=self.verifier,
        )
        self.assertEqual(assessed["status"], "VERIFIED")

        canaries = [
            self.runtime.register_agent("canary-1"),
            self.runtime.register_agent("canary-2"),
            self.runtime.register_agent("canary-3"),
        ]
        for idx, agent in enumerate(canaries):
            state = self.gate.record_canary(
                candidate,
                agent_id=agent,
                success=True,
                regression=False,
                evidence={"canary_run": idx},
            )
        self.assertEqual(state["status"], "GLOBAL_ELIGIBLE")
        self.assertEqual(self.gate.get_active_skill("lead-research")["version"], "v1")

        promoted = self.gate.promote_global(
            candidate,
            curator_agent_id=self.curator,
            evidence={"approval": "heldout + canary package reviewed"},
            reason="verified improvement with zero observed regressions",
        )
        self.assertEqual(promoted["version"], "v2")
        self.assertEqual(promoted["artifact_hash"], sha("candidate-v2"))

    def test_canary_regression_quarantines(self):
        candidate = self._candidate()
        self._score_all(candidate)
        self.gate.assess_candidate(candidate, verifier_agent_id=self.verifier)
        canary = self.runtime.register_agent("canary")
        result = self.gate.record_canary(
            candidate,
            agent_id=canary,
            success=False,
            regression=True,
            evidence={"failure": "regression reproduced"},
        )
        self.assertEqual(result["status"], "QUARANTINED")
        self.assertEqual(self.gate.get_active_skill("lead-research")["version"], "v1")

    def test_wrong_curator_cannot_promote_or_rollback(self):
        candidate = self._candidate()
        self._score_all(candidate)
        self.gate.assess_candidate(candidate, verifier_agent_id=self.verifier)
        canaries = [self.runtime.register_agent(f"canary-{i}") for i in range(3)]
        for agent in canaries:
            self.gate.record_canary(
                candidate,
                agent_id=agent,
                success=True,
                regression=False,
                evidence={"ok": True},
            )
        outsider = self.runtime.register_agent("outsider-curator")
        with self.assertRaises(SkillPromotionError):
            self.gate.promote_global(
                candidate,
                curator_agent_id=outsider,
                evidence={"approval": True},
                reason="unauthorized",
            )
        self.gate.promote_global(
            candidate,
            curator_agent_id=self.curator,
            evidence={"approval": True},
            reason="authorized",
        )
        with self.assertRaises(SkillPromotionError):
            self.gate.rollback(
                skill_key="lead-research",
                to_version="v1",
                curator_agent_id=outsider,
                reason="unauthorized rollback",
                evidence={"incident": "none"},
            )

    def test_authorized_rollback_restores_prior_champion(self):
        candidate = self._candidate()
        self._score_all(candidate)
        self.gate.assess_candidate(candidate, verifier_agent_id=self.verifier)
        for i in range(3):
            agent = self.runtime.register_agent(f"canary-rb-{i}")
            self.gate.record_canary(
                candidate,
                agent_id=agent,
                success=True,
                regression=False,
                evidence={"ok": i},
            )
        self.gate.promote_global(
            candidate,
            curator_agent_id=self.curator,
            evidence={"approval": True},
            reason="promote for rollback test",
        )
        rolled = self.gate.rollback(
            skill_key="lead-research",
            to_version="v1",
            curator_agent_id=self.curator,
            reason="post-promotion production regression",
            evidence={"incident": "INC-1"},
        )
        self.assertEqual(rolled["version"], "v1")


if __name__ == "__main__":
    unittest.main()
