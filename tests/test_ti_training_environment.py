import unittest

from production.training_environment import (
    TrainingEnvironmentConfig,
    build_outcome_credit,
    build_training_environment,
    outcome_signal,
    split_for_run,
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
        "search_run_id": run_id,
        "timestamp": "2026-09-20T00:00:00Z",
        "measurement_quality": quality,
        "work_action": "search",
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
