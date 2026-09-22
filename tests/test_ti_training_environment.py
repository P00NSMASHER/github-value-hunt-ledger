import unittest

from production.training_environment import (
    TrainingEnvironmentConfig,
    build_outcome_credit,
    build_training_environment,
    outcome_signal,
    partition_for_id,
    split_for_run,
    telemetry_consistency_errors,
    validate_training_environment,
)


def search_run(
    run_id,
    *,
    quality="prospective",
    experiment_id="EXP-1",
    capability_ids=("CAP-001",),
    repository="org/repo",
    retained=1,
    deep=2,
):
    return {
        "schema_version": 16,
        "search_run_id": run_id,
        "timestamp": "2026-09-20T00:00:00Z",
        "measurement_quality": quality,
        "work_action": "search",
        "allocation_mode": "generated",
        "routing_mode": "generated",
        "assignment_id": f"ASSIGN:{run_id}",
        "execution_claim_id": f"CLAIM:{run_id}",
        "strategy_id": "STRAT:x",
        "query_family_id": "QF:x",
        "query_family": "x",
        "candidate_count": 2,
        "deep_inspected": deep,
        "retained_count": retained,
        "master_promoted_count": 0,
        "strengthened_capability_ids": list(
            capability_ids
        ),
        "new_capability_ids": [],
        "experiment_ids": (
            [experiment_id]
            if experiment_id
            else []
        ),
        "candidate_dispositions": (
            [
                {
                    "repository": repository,
                    "status": "strong-component",
                    "capability_ids": list(
                        capability_ids
                    ),
                }
            ]
            if repository
            else []
        ),
    }


def outcome(
    origins,
    *,
    result="PARTIAL",
    experiment_id="EXP-1",
    capability_ids=("CAP-001",),
    repository="org/repo@abc",
    revenue=None,
):
    return {
        "outcome_id": "OUT:1",
        "date": "2026-09-21",
        "experiment_id": experiment_id,
        "result": result,
        "origin_search_ids": list(origins),
        "contributing_capability_ids": list(
            capability_ids
        ),
        "contributing_repositories": (
            [repository]
            if repository
            else []
        ),
        "revenue_usd": revenue,
        "customer_value_usd": None,
        "engineering_days_saved_low": None,
        "engineering_days_saved_high": None,
    }


class TrainingEnvironmentTests(unittest.TestCase):
    def test_split_is_deterministic_and_benchmark_eval_only(self):
        run = search_run("RUN:det")
        self.assertEqual(
            split_for_run(run),
            split_for_run(run),
        )
        self.assertEqual(
            split_for_run(
                search_run(
                    "RUN:b",
                    quality="benchmark",
                )
            ),
            "evaluation_only",
        )

    def test_legacy_zero_candidate_record_is_excluded(self):
        legacy = search_run("RUN:legacy")
        legacy["work_action"] = None
        legacy["candidate_count"] = 0
        legacy["deep_inspected"] = 0
        legacy["retained_count"] = 0
        legacy["master_promoted_count"] = 0
        self.assertEqual(
            split_for_run(legacy),
            "excluded",
        )

    def test_impossible_denominators_are_excluded_from_training(self):
        bad = search_run(
            "RUN:bad-denominators",
            deep=1,
            retained=2,
        )
        self.assertIn(
            "retained_exceeds_deep_inspected",
            telemetry_consistency_errors(bad),
        )
        self.assertEqual(
            split_for_run(bad),
            "excluded",
        )
        environment = build_training_environment(
            [bad],
            [],
        )
        self.assertEqual(environment["episodes"], [])
        self.assertIn(
            "retained_exceeds_deep_inspected",
            environment["excluded_runs"][0]["reason"],
        )

    def test_duplicate_avoidance_cannot_exceed_preflight_checks(self):
        bad = search_run("RUN:bad-preflight")
        bad["candidate_preflight_checks"] = 2
        bad["known_candidate_preflight_hits"] = 1
        bad["duplicate_deep_inspections_avoided"] = 3
        self.assertIn(
            "duplicate_avoidance_exceeds_checks",
            telemetry_consistency_errors(bad),
        )
        self.assertEqual(
            split_for_run(bad),
            "excluded",
        )

    def test_credit_conserves_and_reserves_direct_origin_budget(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=1,
        )
        ids = []
        for index in range(100):
            run_id = f"RUN:{index}"
            if (
                split_for_run(
                    search_run(run_id),
                    config=config,
                )
                == "train"
            ):
                ids.append(run_id)
            if len(ids) == 2:
                break

        direct, support = ids
        edges, excluded = build_outcome_credit(
            [
                search_run(direct),
                search_run(support),
            ],
            [outcome([direct])],
            config=config,
        )
        self.assertFalse(excluded)
        self.assertAlmostEqual(
            sum(edge["credit"] for edge in edges),
            1.0,
        )

        direct_edge = next(
            edge
            for edge in edges
            if edge["run_id"] == direct
        )
        support_edge = next(
            edge
            for edge in edges
            if edge["run_id"] == support
        )
        self.assertAlmostEqual(
            direct_edge["credit"],
            0.60,
        )
        self.assertAlmostEqual(
            support_edge["credit"],
            0.40,
        )
        self.assertTrue(
            any(
                path["kind"]
                == "retained_repository"
                for path in support_edge[
                    "path_evidence"
                ]
            )
        )

    def test_shared_experiment_alone_does_not_receive_support_credit(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=1,
        )
        ids = []
        for index in range(100):
            run_id = f"RUN:experiment-only:{index}"
            candidate = search_run(run_id)
            if split_for_run(candidate, config=config) == "train":
                ids.append(run_id)
            if len(ids) == 2:
                break

        direct_id, support_id = ids
        direct = search_run(
            direct_id,
            capability_ids=("CAP-001",),
            repository="org/direct",
        )
        support = search_run(
            support_id,
            capability_ids=("CAP-999",),
            repository="org/unrelated",
        )
        out = outcome(
            [direct_id],
            capability_ids=("CAP-001",),
            repository="org/direct@abc",
        )
        edges, excluded = build_outcome_credit(
            [direct, support],
            [out],
            config=config,
        )
        self.assertFalse(excluded)
        self.assertEqual(
            {edge["run_id"] for edge in edges},
            {direct_id},
        )
        self.assertAlmostEqual(edges[0]["credit"], 1.0)

    def test_credit_does_not_cross_train_confirm_split(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        train_id = None
        confirm_id = None
        for index in range(100):
            run_id = f"RUN:{index}"
            split = split_for_run(
                search_run(run_id),
                config=config,
            )
            if (
                split == "train"
                and train_id is None
            ):
                train_id = run_id
            if (
                split == "confirm"
                and confirm_id is None
            ):
                confirm_id = run_id
            if train_id and confirm_id:
                break

        edges, excluded = build_outcome_credit(
            [
                search_run(train_id),
                search_run(confirm_id),
            ],
            [outcome([confirm_id])],
            config=config,
        )
        self.assertFalse(excluded)
        self.assertEqual(
            {
                edge["run_id"]
                for edge in edges
            },
            {confirm_id},
        )
        self.assertEqual(
            {
                edge["split"]
                for edge in edges
            },
            {"confirm"},
        )

    def test_excluded_execution_origin_can_anchor_support_credit(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        execution_origin = "RUN:execution-origin"
        execution = search_run(
            execution_origin,
        )
        execution["work_action"] = "execute_fixture"
        anchor_split = partition_for_id(
            execution["assignment_id"],
            config=config,
        )
        support_id = None
        opposite_id = None
        for index in range(100):
            run_id = f"RUN:support:{index}"
            split = split_for_run(
                search_run(run_id),
                config=config,
            )
            if split == anchor_split and support_id is None:
                support_id = run_id
            if split != anchor_split and opposite_id is None:
                opposite_id = run_id
            if support_id and opposite_id:
                break

        edges, excluded = build_outcome_credit(
            [
                execution,
                search_run(support_id),
                search_run(opposite_id),
            ],
            [outcome([execution_origin])],
            config=config,
        )
        self.assertFalse(excluded)
        self.assertEqual(
            {edge["run_id"] for edge in edges},
            {support_id},
        )
        self.assertAlmostEqual(
            edges[0]["credit"],
            1.0,
        )
        self.assertEqual(
            edges[0]["credit_anchor"]["kind"],
            "excluded_direct_origin_precommit",
        )
        self.assertEqual(
            edges[0]["credit_anchor"]["split"],
            anchor_split,
        )
        self.assertNotEqual(
            split_for_run(
                execution,
                config=config,
            ),
            anchor_split,
        )

    def test_retry_changes_claim_but_not_train_confirm_partition(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        run = search_run("RUN:retry-stable")
        first = split_for_run(run, config=config)
        run["execution_claim_id"] = "CLAIM:different-retry"
        second = split_for_run(run, config=config)
        self.assertEqual(first, second)
        environment = build_training_environment(
            [run],
            [],
            config=config,
        )
        basis = environment["episodes"][0]["provenance"][
            "partition_basis"
        ]
        self.assertEqual(basis["source"], "assignment_id")
        self.assertEqual(
            basis["identifier"],
            run["assignment_id"],
        )

    def test_manual_run_is_train_only_even_if_run_id_hashes_to_confirm(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        chosen = None
        for index in range(100):
            run_id = f"RUN:manual:{index}"
            if partition_for_id(run_id, config=config) == "confirm":
                chosen = search_run(run_id)
                break
        self.assertIsNotNone(chosen)
        chosen["allocation_mode"] = "manual_override"
        chosen["execution_claim_id"] = None
        self.assertEqual(
            split_for_run(chosen, config=config),
            "train",
        )

    def test_untrusted_excluded_origin_cannot_anchor_support_credit(self):
        execution = search_run("RUN:manual-execution")
        execution["work_action"] = "execute_fixture"
        execution["allocation_mode"] = "manual_override"
        execution["execution_claim_id"] = None
        support = search_run("RUN:generated-support")
        out = outcome(["RUN:manual-execution"])

        edges, excluded = build_outcome_credit(
            [execution, support],
            [out],
        )
        self.assertEqual(edges, [])
        self.assertEqual(
            excluded[0]["reason"],
            "untrusted_excluded_direct_origin_partition",
        )

    def test_date_only_outcome_does_not_credit_same_day_indirect_support(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        direct_id = None
        support_id = None
        for index in range(100):
            run_id = f"RUN:temporal:{index}"
            if (
                split_for_run(
                    search_run(run_id),
                    config=config,
                )
                == "train"
            ):
                if direct_id is None:
                    direct_id = run_id
                elif support_id is None:
                    support_id = run_id
                    break

        direct = search_run(direct_id)
        support = search_run(support_id)
        direct["timestamp"] = "2026-09-21T08:00:00Z"
        support["timestamp"] = "2026-09-21T07:00:00Z"
        out = outcome([direct_id])
        out["date"] = "2026-09-21"

        edges, excluded = build_outcome_credit(
            [direct, support],
            [out],
            config=config,
        )
        self.assertFalse(excluded)
        self.assertEqual(
            {edge["run_id"] for edge in edges},
            {direct_id},
        )

    def test_timestamped_outcome_can_credit_earlier_same_day_support(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        ids = []
        for index in range(100):
            run_id = f"RUN:clock:{index}"
            if (
                split_for_run(
                    search_run(run_id),
                    config=config,
                )
                == "train"
            ):
                ids.append(run_id)
            if len(ids) == 2:
                break

        direct_id, support_id = ids
        direct = search_run(direct_id)
        support = search_run(support_id)
        direct["timestamp"] = "2026-09-21T08:00:00Z"
        support["timestamp"] = "2026-09-21T07:00:00Z"
        out = outcome([direct_id])
        out["timestamp"] = "2026-09-21T09:00:00Z"

        edges, excluded = build_outcome_credit(
            [direct, support],
            [out],
            config=config,
        )
        self.assertFalse(excluded)
        self.assertEqual(
            {edge["run_id"] for edge in edges},
            {direct_id, support_id},
        )

    def test_direct_origin_after_outcome_is_excluded(self):
        run = search_run("RUN:future-origin")
        run["timestamp"] = "2026-09-22T12:00:00Z"
        out = outcome(["RUN:future-origin"])
        out["timestamp"] = "2026-09-21T12:00:00Z"

        edges, excluded = build_outcome_credit(
            [run],
            [out],
        )
        self.assertEqual(edges, [])
        self.assertEqual(
            excluded[0]["reason"],
            "direct_origin_after_outcome",
        )

    def test_mixed_direct_origin_splits_are_excluded(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        train_id = None
        confirm_id = None
        for index in range(100):
            run_id = f"RUN:{index}"
            split = split_for_run(
                search_run(run_id),
                config=config,
            )
            if (
                split == "train"
                and train_id is None
            ):
                train_id = run_id
            if (
                split == "confirm"
                and confirm_id is None
            ):
                confirm_id = run_id
            if train_id and confirm_id:
                break

        edges, excluded = build_outcome_credit(
            [
                search_run(train_id),
                search_run(confirm_id),
            ],
            [
                outcome(
                    [train_id, confirm_id]
                )
            ],
            config=config,
        )
        self.assertEqual(edges, [])
        self.assertEqual(
            excluded[0]["reason"],
            "mixed_direct_origin_splits",
        )

    def test_technical_proxy_cannot_impersonate_commercial_value(self):
        technical = outcome_signal(
            outcome(
                ["RUN:1"],
                result="PASSED",
                revenue=None,
            )
        )
        commercial = outcome_signal(
            outcome(
                ["RUN:1"],
                result="PARTIAL",
                revenue=1000,
            )
        )
        self.assertEqual(
            technical["value_stage"],
            "technical_proxy",
        )
        self.assertLessEqual(
            technical["scalar"],
            0.40,
        )
        self.assertEqual(
            commercial["value_stage"],
            "realized_economic",
        )
        self.assertGreater(
            commercial["scalar"],
            technical["scalar"],
        )

    def test_realized_commercial_reward_is_magnitude_aware_and_bounded(self):
        small = outcome_signal(
            outcome(
                ["RUN:1"],
                result="PARTIAL",
                revenue=1000,
            )
        )
        large = outcome_signal(
            outcome(
                ["RUN:1"],
                result="PARTIAL",
                revenue=1_000_000,
            )
        )
        huge = outcome_signal(
            outcome(
                ["RUN:1"],
                result="PARTIAL",
                revenue=1_000_000_000,
            )
        )
        self.assertLess(
            small["commercial"],
            large["commercial"],
        )
        self.assertEqual(
            large["commercial"],
            1.0,
        )
        self.assertEqual(
            huge["commercial"],
            1.0,
        )
        self.assertEqual(
            small["economic_value_usd"],
            1000.0,
        )

    def test_training_episode_preserves_schema_native_move_telemetry(self):
        run = search_run("RUN:moves")
        run["search_moves"] = [
            {
                "move_type": "code_signature_search",
                "surface": "GitHub code search",
                "query_or_action": "distinctive symbol",
                "result": "qualifying_hit",
                "candidate_count": 2,
                "deep_inspected": 1,
                "retained_count": 1,
            },
            {
                "move_type": "direct_domain_search",
                "surface": "GitHub repository search",
                "query_or_action": "broad phrase",
                "result": "no_hit",
                "candidate_count": 0,
                "deep_inspected": 0,
                "retained_count": 0,
            },
        ]
        environment = build_training_environment(
            [run],
            [],
        )
        episode = environment["episodes"][0]
        self.assertEqual(
            episode["action"]["search_move_ids"],
            [
                "MOVE:code_signature_search",
                "MOVE:direct_domain_search",
            ],
        )
        self.assertEqual(
            [
                move["result"]
                for move in episode["action"]["search_moves"]
            ],
            ["qualifying_hit", "no_hit"],
        )

    def test_environment_is_hash_stable_and_valid(self):
        runs = [
            search_run("RUN:1"),
            search_run(
                "RUN:2",
                experiment_id="EXP-2",
                capability_ids=("CAP-002",),
                repository="org/other",
            ),
        ]
        first = build_training_environment(
            runs,
            [outcome(["RUN:1"])],
        )
        second = build_training_environment(
            runs,
            [outcome(["RUN:1"])],
        )
        self.assertEqual(
            first["source_snapshot_sha256"],
            second["source_snapshot_sha256"],
        )
        self.assertEqual(
            [
                row["episode_sha256"]
                for row in first["episodes"]
            ],
            [
                row["episode_sha256"]
                for row in second["episodes"]
            ],
        )
        self.assertEqual(
            validate_training_environment(
                first
            ),
            [],
        )

    def test_validator_rejects_untrusted_confirm_episode(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        confirm_run = None
        for index in range(100):
            candidate = search_run(f"RUN:confirm-tamper:{index}")
            if split_for_run(candidate, config=config) == "confirm":
                confirm_run = candidate
                break
        self.assertIsNotNone(confirm_run)
        environment = build_training_environment(
            [confirm_run],
            [],
            config=config,
        )
        episode = environment["episodes"][0]
        episode["provenance"]["partition_basis"] = {
            "trusted": False,
            "source": "run_id_fallback_train_only",
            "identifier": episode["run_id"],
        }
        errors = validate_training_environment(environment)
        self.assertIn(
            f"untrusted_confirm_partition:{episode['run_id']}",
            errors,
        )

    def test_validator_rejects_trusted_partition_source_tamper(self):
        run = search_run("RUN:trusted-source-tamper")
        environment = build_training_environment(
            [run],
            [],
        )
        episode = environment["episodes"][0]
        episode["provenance"]["partition_basis"]["source"] = (
            "execution_claim_id"
        )
        errors = validate_training_environment(environment)
        self.assertIn(
            f"invalid_trusted_partition_source:{episode['run_id']}",
            errors,
        )

    def test_validator_rejects_partition_provenance_contract_tamper(self):
        run = search_run("RUN:trusted-contract-tamper")
        environment = build_training_environment(
            [run],
            [],
        )
        episode = environment["episodes"][0]
        episode["provenance"]["partition_basis"][
            "provenance_contract"
        ] = "invented_contract"
        errors = validate_training_environment(environment)
        self.assertIn(
            f"invalid_partition_provenance_contract:{episode['run_id']}",
            errors,
        )

    def test_validator_rejects_partition_hash_tamper(self):
        config = TrainingEnvironmentConfig(
            confirm_modulus=2,
            confirm_bucket=0,
        )
        chosen = None
        opposite_identifier = None
        for index in range(100):
            candidate = search_run(f"RUN:partition:{index}")
            split = split_for_run(candidate, config=config)
            if chosen is None:
                chosen = candidate
                expected = split
            fake = f"ASSIGN:fake:{index}"
            if partition_for_id(fake, config=config) != expected:
                opposite_identifier = fake
                break
        environment = build_training_environment(
            [chosen],
            [],
            config=config,
        )
        episode = environment["episodes"][0]
        episode["provenance"]["partition_basis"]["identifier"] = (
            opposite_identifier
        )
        errors = validate_training_environment(environment)
        self.assertIn(
            f"partition_hash_mismatch:{episode['run_id']}",
            errors,
        )

    def test_validator_rejects_malformed_move_telemetry(self):
        run = search_run("RUN:bad-move")
        run["search_moves"] = [
            {
                "move_type": "code_signature_search",
                "result": "qualifying_hit",
                "candidate_count": 1,
                "deep_inspected": 1,
                "retained_count": 1,
            }
        ]
        environment = build_training_environment(
            [run],
            [],
        )
        environment["episodes"][0]["action"]["search_moves"][0][
            "result"
        ] = "invented_result"
        errors = validate_training_environment(environment)
        self.assertTrue(
            any(
                error.startswith("invalid_move_result:")
                for error in errors
            )
        )

    def test_immediate_only_episode_is_capped(self):
        environment = build_training_environment(
            [
                search_run(
                    "RUN:solo",
                    retained=2,
                    deep=2,
                )
            ],
            [],
        )
        episode = environment["episodes"][0]
        self.assertEqual(
            episode["reward"]["reward_stage"],
            "discovery_only",
        )
        self.assertLessEqual(
            episode["reward"][
                "training_reward"
            ],
            0.40,
        )


if __name__ == "__main__":
    unittest.main()
