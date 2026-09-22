import unittest

from production.learning_engine import (
    ExperienceKind,
    FailureDecision,
    FailureEvent,
    FleetAgentCandidate,
    HarnessMutationDecision,
    HarnessMutationEvidence,
    MemoryCandidate,
    PeerSkillEvidence,
    RepairCandidate,
    RepairDecision,
    SkillMutationDecision,
    SkillVariantEvidence,
    TrainingTrajectory,
    TransferDecision,
    ValueConfig,
    ValueMemory,
    assess_failure_for_repair,
    assess_harness_mutation,
    assess_peer_skill_transfer,
    assess_repair_candidate,
    assess_skill_variant,
    assess_training_export,
    build_training_manifest,
    learn_training_episode_memory,
    learn_value_memory,
    observed_search_reward,
    salvage_trajectory,
    select_fleet_parents,
    TrajectoryOutcome,
)


class ValueMemoryTests(unittest.TestCase):
    def test_q_value_updates_and_reranks_relevant_memory(self):
        memory = ValueMemory(ValueConfig(alpha=1.0, epsilon=0.0))
        memory.update("STRAT:a", ExperienceKind.STRATEGY, 0.9)
        memory.update("STRAT:b", ExperienceKind.STRATEGY, -0.8)
        ranked = memory.rank(
            [
                MemoryCandidate("STRAT:a", 0.75),
                MemoryCandidate("STRAT:b", 0.95),
            ],
            top_k=2,
            seed=1,
        )
        self.assertEqual(ranked[0]["key"], "STRAT:a")
        self.assertGreater(ranked[0]["score"], ranked[1]["score"])

    def test_bad_config_rejected(self):
        with self.assertRaises(ValueError):
            ValueMemory(ValueConfig(alpha=2.0))

    def test_search_reward_refuses_non_search_work(self):
        run = {
            "work_action": "execute_fixture",
            "measurement_quality": "prospective",
            "deep_inspected": 2,
            "retained_count": 1,
            "master_promoted_count": 0,
        }
        self.assertIsNone(observed_search_reward(run))

    def test_legacy_zero_candidate_execution_is_not_treated_as_search(self):
        run = {
            "work_action": None,
            "measurement_quality": "prospective",
            "candidate_count": 0,
            "deep_inspected": 0,
            "retained_count": 0,
            "master_promoted_count": 0,
        }
        self.assertIsNone(observed_search_reward(run))

    def test_search_reward_uses_measured_outcome(self):
        run = {
            "work_action": "search",
            "measurement_quality": "prospective",
            "deep_inspected": 3,
            "retained_count": 1,
            "master_promoted_count": 0,
            "new_capability_ids": ["CAP-101"],
            "candidate_preflight_checks": 4,
            "duplicate_deep_inspections_avoided": 2,
        }
        outcome = {
            "result": "SUCCESS",
            "origin_search_ids": ["RUN:1"],
            "revenue_usd": 1000,
        }
        observation = observed_search_reward(run, [outcome])
        self.assertIsNotNone(observation)
        self.assertGreater(observation.reward, 0.5)
        self.assertIn("downstream_outcomes", observation.components)

    def test_no_retained_penalty(self):
        run = {
            "work_action": "search",
            "measurement_quality": "benchmark",
            "deep_inspected": 4,
            "retained_count": 0,
            "master_promoted_count": 0,
            "new_capability_ids": [],
        }
        observation = observed_search_reward(run)
        self.assertLess(observation.reward, 0)

    def test_search_moves_receive_individual_not_whole_run_reward(self):
        episode = {
            "run_id": "RUN:moves",
            "split": "train",
            "state": {
                "search_objective_id": "OBJ:test",
            },
            "action": {
                "strategy_id": "STRAT:test",
                "query_family_id": "QF:test",
                "search_moves": [
                    {
                        "key": "MOVE:code_signature_search",
                        "move_type": "code_signature_search",
                        "result": "qualifying_hit",
                        "deep_inspected": 1,
                        "retained_count": 1,
                    },
                    {
                        "key": "MOVE:direct_domain_search",
                        "move_type": "direct_domain_search",
                        "result": "no_hit",
                        "deep_inspected": 0,
                        "retained_count": 0,
                    },
                ],
                "search_move_ids": [
                    "MOVE:code_signature_search",
                    "MOVE:direct_domain_search",
                ],
            },
            "reward": {
                "training_reward": 0.8,
                "reward_stage": "technical_proxy",
                "downstream": {"outcome_ids": []},
            },
            "provenance": {
                "timestamp": "2026-09-20T00:00:00Z",
            },
        }
        memory, _ = learn_training_episode_memory(
            [episode],
            config=ValueConfig(alpha=1.0, epsilon=0.0),
        )
        good = memory.get("MOVE:code_signature_search")
        weak = memory.get("MOVE:direct_domain_search")
        self.assertGreater(good.q_value, 0.5)
        self.assertLess(weak.q_value, 0.0)
        self.assertNotEqual(good.q_value, 0.8)
        self.assertNotEqual(weak.q_value, 0.8)

    def test_repeated_move_type_counts_once_per_hunt(self):
        episode = {
            "run_id": "RUN:repeat-move",
            "split": "train",
            "state": {
                "search_objective_id": "OBJ:test",
            },
            "action": {
                "strategy_id": "STRAT:test",
                "query_family_id": "QF:test",
                "search_moves": [
                    {
                        "key": "MOVE:code_signature_search",
                        "move_type": "code_signature_search",
                        "result": "qualifying_hit",
                        "deep_inspected": 1,
                        "retained_count": 1,
                    },
                    {
                        "key": "MOVE:code_signature_search",
                        "move_type": "code_signature_search",
                        "result": "no_hit",
                        "deep_inspected": 0,
                        "retained_count": 0,
                    },
                ],
            },
            "reward": {
                "training_reward": 0.8,
                "reward_stage": "technical_proxy",
                "downstream": {"outcome_ids": []},
            },
            "provenance": {
                "timestamp": "2026-09-20T00:00:00Z",
            },
        }
        memory, _ = learn_training_episode_memory(
            [episode],
            config=ValueConfig(alpha=1.0, epsilon=0.0),
        )
        record = memory.get("MOVE:code_signature_search")
        self.assertEqual(record.visits, 1)
        self.assertGreater(record.q_value, 0.0)
        self.assertLess(record.q_value, 0.8)

    def test_objective_conditioned_memory_separates_opposite_strategy_value(self):
        episodes = [
            {
                "run_id": "RUN:obj-a",
                "split": "train",
                "state": {
                    "search_objective_id": "OBJ:authority-lineage",
                },
                "action": {
                    "strategy_id": "STRAT:shared",
                    "query_family_id": "QF:shared",
                    "search_move_ids": ["symbol-search"],
                },
                "reward": {
                    "training_reward": 0.8,
                    "reward_stage": "technical_proxy",
                    "downstream": {"outcome_ids": []},
                },
                "provenance": {
                    "timestamp": "2026-09-20T00:00:00Z",
                },
            },
            {
                "run_id": "RUN:obj-b",
                "split": "train",
                "state": {
                    "search_objective_id": "OBJ:wildcard-discovery",
                },
                "action": {
                    "strategy_id": "STRAT:shared",
                    "query_family_id": "QF:shared",
                    "search_move_ids": ["symbol-search"],
                },
                "reward": {
                    "training_reward": -0.8,
                    "reward_stage": "technical_proxy",
                    "downstream": {"outcome_ids": []},
                },
                "provenance": {
                    "timestamp": "2026-09-21T00:00:00Z",
                },
            },
        ]
        memory, observations = learn_training_episode_memory(
            episodes,
            config=ValueConfig(alpha=1.0, epsilon=0.0),
        )
        authority_key = contextual_memory_key(
            "STRAT:shared",
            "OBJ:authority-lineage",
        )
        wildcard_key = contextual_memory_key(
            "STRAT:shared",
            "OBJ:wildcard-discovery",
        )
        self.assertEqual(memory.get(authority_key).q_value, 0.8)
        self.assertEqual(memory.get(wildcard_key).q_value, -0.8)
        self.assertEqual(memory.get(authority_key).visits, 1)
        self.assertEqual(memory.get(wildcard_key).visits, 1)
        self.assertIn(authority_key, observations[0]["updated_memory_keys"])
        self.assertIn(wildcard_key, observations[1]["updated_memory_keys"])

    def test_learning_updates_strategy_and_query_family(self):
        runs = [
            {
                "search_run_id": "RUN:1",
                "timestamp": "2026-09-20T00:00:00Z",
                "work_action": "search",
                "measurement_quality": "prospective",
                "strategy_id": "STRAT:test",
                "query_family_id": "QF:test",
                "deep_inspected": 2,
                "retained_count": 1,
                "master_promoted_count": 0,
                "new_capability_ids": [],
                "search_moves": [],
            }
        ]
        memory, observations = learn_value_memory(runs, [])
        self.assertEqual(len(observations), 1)
        self.assertEqual(memory.get("STRAT:test").visits, 1)
        self.assertEqual(memory.get("QF:test").visits, 1)


class EpisodeMemoryTests(unittest.TestCase):
    def episode(self, run_id, split, reward):
        return {
            "run_id": run_id,
            "split": split,
            "action": {
                "strategy_id": "STRAT:episode",
                "query_family_id": "QF:episode",
                "search_move_ids": ["pivot"],
            },
            "reward": {
                "training_reward": reward,
                "reward_stage": "technical_proxy",
                "downstream": {
                    "outcome_ids": ["OUT:1"],
                },
            },
            "provenance": {
                "timestamp": "2026-09-20T00:00:00Z",
            },
        }

    def test_only_train_episode_updates_memory(self):
        memory, observations = learn_training_episode_memory(
            [
                self.episode("RUN:train", "train", 0.6),
                self.episode("RUN:confirm", "confirm", 1.0),
                self.episode(
                    "RUN:evaluation",
                    "evaluation_only",
                    1.0,
                ),
            ],
            config=ValueConfig(alpha=1.0),
        )
        self.assertEqual(
            memory.get("STRAT:episode").visits,
            1,
        )
        self.assertEqual(
            memory.get("QF:episode").visits,
            1,
        )
        self.assertEqual(
            memory.get("MOVE:pivot").visits,
            1,
        )
        self.assertEqual(len(observations), 1)
        self.assertEqual(
            observations[0]["search_run_id"],
            "RUN:train",
        )


class FailureLearningTests(unittest.TestCase):
    def good_failure(self, **overrides):
        body = dict(
            failure_id="FAIL:1",
            run_id="RUN:1",
            hunter_id="HUNTER-01",
            target_type="search_skill",
            target_id="search-inspector",
            failure_class="false_positive",
            observation="README looked complete but implementation was absent",
            reproduction_steps=("run the same query", "inspect source tree"),
            evidence_refs=("hunters/19.md#candidate",),
            proposed_regression_test=(
                "candidate must expose substantive source beyond README"
            ),
        )
        body.update(overrides)
        return FailureEvent(**body)

    def test_reproducible_failure_queued(self):
        assessment = assess_failure_for_repair(self.good_failure())
        self.assertEqual(assessment.decision, FailureDecision.QUEUED)
        self.assertEqual(len(assessment.signature), 64)

    def test_sensitive_failure_blocked(self):
        assessment = assess_failure_for_repair(
            self.good_failure(sensitive_material_involved=True)
        )
        self.assertEqual(assessment.decision, FailureDecision.BLOCKED)
        self.assertIn("sensitive_material_blocked", assessment.reasons)

    def test_malformed_failure_target_is_blocked(self):
        assessment = assess_failure_for_repair(
            self.good_failure(target_type="", target_id="")
        )
        self.assertEqual(assessment.decision, FailureDecision.BLOCKED)
        self.assertIn("invalid_target_type", assessment.reasons)
        self.assertIn("target_id_required", assessment.reasons)

    def test_repair_requires_regression_pass_and_history(self):
        candidate = RepairCandidate(
            failure_id="FAIL:1",
            skill_id="SKILL:search",
            candidate_version="v2",
            regression_tests_total=2,
            regression_tests_passed=2,
            diff_hash="abc",
            decision_history_ref="production/history/FAIL-1.json",
        )
        self.assertEqual(
            assess_repair_candidate(candidate).decision,
            RepairDecision.READY_FOR_SKILL_EVAL,
        )

    def test_unrelated_change_rejects_repair(self):
        candidate = RepairCandidate(
            failure_id="FAIL:1",
            skill_id="SKILL:search",
            candidate_version="v2",
            regression_tests_total=1,
            regression_tests_passed=1,
            diff_hash="abc",
            decision_history_ref="x",
            unrelated_files_changed=True,
        )
        self.assertEqual(
            assess_repair_candidate(candidate).decision,
            RepairDecision.REJECTED,
        )


class SalvageTests(unittest.TestCase):
    def test_failed_trajectory_can_be_salvaged_from_verified_actual_outcome(self):
        result = salvage_trajectory(
            TrajectoryOutcome(
                run_id="RUN:1",
                original_goal_success=False,
                verified_alternate_outcome="Found entity-resolution engine",
                alternate_evidence_refs=("hunters/18.md#repo",),
                observed_reward=0.9,
            )
        )
        self.assertTrue(result.eligible)
        self.assertEqual(
            result.memory_scope,
            "LOCAL_ONLY_UNTIL_INDEPENDENTLY_VALIDATED",
        )
        self.assertLessEqual(result.reward, 0.40)

    def test_unverified_alternate_outcome_not_salvaged(self):
        result = salvage_trajectory(
            TrajectoryOutcome(
                run_id="RUN:1",
                original_goal_success=False,
            )
        )
        self.assertFalse(result.eligible)


class SkillEvolutionTests(unittest.TestCase):
    def base(self, **overrides):
        body = dict(
            skill_id="SKILL:search",
            baseline_version="v1",
            candidate_version="v2",
            mutate_dev_examples=6,
            promotion_test_examples=6,
            baseline_dev_score=0.50,
            candidate_dev_score=0.65,
            champion_test_score=0.55,
            candidate_test_score=0.62,
            hard_regressions=0,
            split_fingerprints_disjoint=True,
            provenance_complete=True,
        )
        body.update(overrides)
        return SkillVariantEvidence(**body)

    def test_candidate_can_only_stage_after_disjoint_holdout_improvement(self):
        result = assess_skill_variant(self.base())
        self.assertEqual(
            result.decision,
            SkillMutationDecision.STAGED_MUTATION,
        )

    def test_split_leakage_rejects_candidate(self):
        result = assess_skill_variant(
            self.base(split_fingerprints_disjoint=False)
        )
        self.assertEqual(result.decision, SkillMutationDecision.REJECTED)
        self.assertIn("dev_test_split_leakage", result.reasons)

    def test_regression_rejects_candidate(self):
        result = assess_skill_variant(self.base(hard_regressions=1))
        self.assertEqual(result.decision, SkillMutationDecision.REJECTED)


class FederatedTransferTests(unittest.TestCase):
    def test_verified_compatible_same_runtime_skill_can_absorb_locally(self):
        evidence = PeerSkillEvidence(
            skill_id="SKILL:x",
            source_hunter="H1",
            target_hunter="H2",
            source_state="VERIFIED",
            source_distinct_successes=3,
            source_regressions=0,
            compatibility_score=0.9,
            target_failure_overlap=0.8,
            same_runtime=True,
            evidence_refs=("e1", "e2"),
        )
        result = assess_peer_skill_transfer(evidence)
        self.assertEqual(result.decision, TransferDecision.ABSORB_LOCAL)

    def test_heterogeneous_skill_adapts_instead_of_blind_copy(self):
        evidence = PeerSkillEvidence(
            skill_id="SKILL:x",
            source_hunter="H1",
            target_hunter="H2",
            source_state="STAGED",
            source_distinct_successes=2,
            source_regressions=0,
            compatibility_score=0.7,
            target_failure_overlap=0.8,
            same_runtime=False,
            evidence_refs=("e1",),
        )
        self.assertEqual(
            assess_peer_skill_transfer(evidence).decision,
            TransferDecision.ADAPT_LOCAL,
        )

    def test_regressing_skill_rejected(self):
        evidence = PeerSkillEvidence(
            skill_id="SKILL:x",
            source_hunter="H1",
            target_hunter="H2",
            source_state="GLOBAL",
            source_distinct_successes=5,
            source_regressions=1,
            compatibility_score=0.9,
            target_failure_overlap=0.8,
            same_runtime=True,
            evidence_refs=("e1",),
        )
        self.assertEqual(
            assess_peer_skill_transfer(evidence).decision,
            TransferDecision.REJECT,
        )


class FleetEvolutionTests(unittest.TestCase):
    def test_performance_novelty_preserves_different_behavior(self):
        rows = [
            FleetAgentCandidate("clone-a", 0.90, (1, 1, 0, 0)),
            FleetAgentCandidate("clone-b", 0.89, (1, 1, 0, 0)),
            FleetAgentCandidate("novel", 0.80, (0, 0, 1, 1)),
        ]
        selected = select_fleet_parents(
            rows,
            top_k=2,
            nearest_neighbors=1,
        )
        ids = {row.agent_id for row in selected}
        self.assertIn("novel", ids)

    def test_vector_dimension_mismatch_rejected(self):
        rows = [
            FleetAgentCandidate("a", 1, (1, 0)),
            FleetAgentCandidate("b", 1, (1, 0, 0)),
        ]
        with self.assertRaises(ValueError):
            select_fleet_parents(rows, 1)


class HarnessMutationTests(unittest.TestCase):
    def good(self, **overrides):
        body = dict(
            mutation_id="MUT:1",
            touched_paths=("skills/search/SKILL.md",),
            allowed_paths=(
                "skills/search/SKILL.md",
                "skills/search/helpers.py",
            ),
            selection_tasks=8,
            baseline_score=0.50,
            candidate_score=0.60,
            regressions=0,
            diff_hash="abc",
        )
        body.update(overrides)
        return HarnessMutationEvidence(**body)

    def test_good_harness_mutation_is_canary_only(self):
        self.assertEqual(
            assess_harness_mutation(self.good()).decision,
            HarnessMutationDecision.CANARY_ONLY,
        )

    def test_evaluator_mutation_is_rejected(self):
        result = assess_harness_mutation(
            self.good(evaluator_modified=True)
        )
        self.assertEqual(result.decision, HarnessMutationDecision.REJECT)
        self.assertIn("evaluator_is_immutable", result.reasons)

    def test_out_of_lease_path_is_rejected(self):
        result = assess_harness_mutation(
            self.good(touched_paths=("production/controller.py",))
        )
        self.assertEqual(result.decision, HarnessMutationDecision.REJECT)


class TrainingExportTests(unittest.TestCase):
    def test_only_verified_clean_trajectory_exported(self):
        good = TrainingTrajectory(
            run_id="RUN:1",
            reward=0.8,
            verified=True,
            evidence_refs=("e1",),
            payload_ref="sha256:abc",
        )
        bad = TrainingTrajectory(
            run_id="RUN:2",
            reward=0.2,
            verified=False,
            evidence_refs=(),
            payload_ref=None,
        )
        manifest = build_training_manifest([good, bad])
        self.assertEqual(
            [row["run_id"] for row in manifest["accepted"]],
            ["RUN:1"],
        )
        self.assertEqual(
            [row["run_id"] for row in manifest["rejected"]],
            ["RUN:2"],
        )
        self.assertEqual(len(manifest["manifest_sha256"]), 64)

    def test_sensitive_trajectory_not_exported(self):
        trajectory = TrainingTrajectory(
            run_id="RUN:1",
            reward=0.8,
            verified=True,
            evidence_refs=("e1",),
            payload_ref="sha256:abc",
            sensitive_material_involved=True,
        )
        self.assertFalse(assess_training_export(trajectory).eligible)


if __name__ == "__main__":
    unittest.main()
