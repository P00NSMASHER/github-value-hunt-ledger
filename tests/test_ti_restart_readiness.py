import unittest

from production.restart_readiness import (
    build_restart_readiness,
    count_shadow_runs,
    parse_matched_benchmark_tasks,
    unmatched_benchmark_tasks,
    validate_restart_readiness,
)


def packets():
    return {
        "mode": "precommit_only",
        "policy_effect": "none",
        "activates_work": False,
        "partition_selection_allowed": False,
        "unpaired_recommendations": [],
        "packets": [
            {
                "status": "PRECOMMITTED_ADVISORY",
                "execution_authority": False,
                "requires_generated_claim": True,
                "manual_work_can_complete_packet": False,
                "partition_unknown_until_ingestion": True,
            }
            for _ in range(3)
        ],
    }


def split_status(*, ready):
    if ready:
        return {
            "partition_method": "hmac-sha256-v1",
            "key_commitment_active": True,
            "secret_available": True,
            "issues": [],
            "pending_claim_ids": [],
            "receipts": 3,
        }
    return {
        "partition_method": "hmac-sha256-v1",
        "key_commitment_active": False,
        "secret_available": False,
        "issues": [
            {"reason": "split_key_commitment_unavailable"},
            {"reason": "split_key_commitment_unavailable"},
        ],
        "pending_claim_ids": ["CLAIM:a", "CLAIM:b"],
        "receipts": 0,
    }


def scoreboard(matched):
    detail = []
    for index in range(1, matched + 1):
        task_id = f"{index:02d}"
        detail.append(
            f"| {task_id} | CONTROL | 25 |"
        )
        detail.append(
            f"| {task_id} | EXPERIMENT | 25 |"
        )
    return (
        "# SCOREBOARD\n"
        f"- Matched tasks scored: **{matched}** — details.\n"
        + "\n".join(detail)
        + "\n"
    )


def shadows(total_per_lane=5):
    text = "\n".join(
        f"## Shadow run {i}"
        for i in range(1, total_per_lane + 1)
    )
    return {
        "ai": text,
        "science": text,
        "commercial": text,
    }


class RestartReadinessTests(unittest.TestCase):
    def test_parsers(self):
        self.assertEqual(
            parse_matched_benchmark_tasks(
                scoreboard(47)
            ),
            47,
        )
        self.assertEqual(
            count_shadow_runs(
                "## Run 1\nx\n## Shadow Science Run 2\n"
            ),
            2,
        )

    def test_unmatched_task_parser_reports_missing_arm_only(self):
        text = (
            "# SCOREBOARD\n"
            "- Matched tasks scored: **47** — details.\n"
            "| 01 | CONTROL | 25 |\n"
            "| 01 | EXPERIMENT | 25 |\n"
            "| 06 | CONTROL | 25 |\n"
            "| 07 | CONTROL | 25 |\n"
            "| 08 | CONTROL | 25 |\n"
        )
        debt = unmatched_benchmark_tasks(
            text,
            expected_tasks=8,
        )
        by_id = {
            row["task_id"]: row
            for row in debt
        }
        self.assertNotIn("01", by_id)
        self.assertEqual(
            by_id["06"]["missing_arms"],
            ["EXPERIMENT"],
        )
        self.assertEqual(
            by_id["07"]["missing_arms"],
            ["EXPERIMENT"],
        )
        self.assertEqual(
            by_id["08"]["missing_arms"],
            ["EXPERIMENT"],
        )

    def test_current_blocker_pattern_is_blocked(self):
        report = build_restart_readiness(
            split_status=split_status(ready=False),
            activation_metrics={
                "current_activations": 0
            },
            packets=packets(),
            scoreboard_text=scoreboard(47),
            shadow_results=shadows(20),
        )
        self.assertEqual(report["state"], "BLOCKED")
        codes = {
            row["code"]
            for row in report["blockers"]
        }
        self.assertIn(
            "split_key_commitment_inactive",
            codes,
        )
        self.assertIn(
            "split_secret_unavailable",
            codes,
        )
        self.assertIn(
            "split_receipt_debt",
            codes,
        )
        self.assertIn(
            "frozen_benchmark_incomplete",
            codes,
        )
        benchmark_blocker = next(
            row
            for row in report["blockers"]
            if row["code"] == "frozen_benchmark_incomplete"
        )
        self.assertEqual(
            benchmark_blocker["unmatched_task_ids"],
            ["48", "49", "50"],
        )
        self.assertNotIn(
            "shadow_run_gate_incomplete",
            codes,
        )
        self.assertFalse(report["activates_work"])
        self.assertFalse(
            report["changes_automation_state"]
        )
        self.assertEqual(
            validate_restart_readiness(report),
            [],
        )

    def test_stale_50_of_50_summary_cannot_hide_missing_detail(self):
        stale = scoreboard(50).replace(
            "| 06 | EXPERIMENT | 25 |\n",
            "",
        )
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={"current_activations": 0},
            packets=packets(),
            scoreboard_text=stale,
            shadow_results=shadows(5),
        )
        self.assertFalse(
            report["gates"]["benchmark_complete"]
        )
        self.assertEqual(
            report["evidence"]["unmatched_benchmark_task_ids"],
            ["06"],
        )

    def test_all_machine_gates_still_wait_for_user_approval(self):
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={
                "current_activations": 0
            },
            packets=packets(),
            scoreboard_text=scoreboard(50),
            shadow_results=shadows(5),
        )
        self.assertEqual(
            report["state"],
            "AWAITING_EXPLICIT_USER_APPROVAL",
        )
        self.assertEqual(report["blockers"], [])
        self.assertTrue(
            all(report["gates"].values())
        )
        self.assertTrue(
            report["explicit_user_approval_required"]
        )
        self.assertFalse(report["activates_work"])

    def test_existing_activation_blocks_canary(self):
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={
                "current_activations": 1
            },
            packets=packets(),
            scoreboard_text=scoreboard(50),
            shadow_results=shadows(5),
        )
        self.assertEqual(report["state"], "BLOCKED")
        self.assertIn(
            "existing_generated_activations_present",
            {
                row["code"]
                for row in report["blockers"]
            },
        )

    def test_active_generated_claim_blocks_canary(self):
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={
                "current_activations": 0
            },
            packets=packets(),
            scoreboard_text=scoreboard(50),
            shadow_results=shadows(5),
            execution_claim_history=[
                {
                    "claim_id": "CLAIM:aaaaaaaaaaaa",
                    "routing_mode": "generated",
                    "status": "RUNNING",
                }
            ],
        )
        self.assertEqual(report["state"], "BLOCKED")
        self.assertFalse(
            report["gates"]["no_active_generated_claims"]
        )
        self.assertEqual(
            report["evidence"]["active_generated_claim_ids"],
            ["CLAIM:aaaaaaaaaaaa"],
        )
        blocker = next(
            row
            for row in report["blockers"]
            if row["code"] == "active_generated_claims_present"
        )
        self.assertEqual(
            blocker["active_generated_claim_count"],
            1,
        )
        self.assertEqual(
            validate_restart_readiness(report),
            [],
        )

    def test_manual_override_claim_does_not_count_as_generated_debt(self):
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={
                "current_activations": 0
            },
            packets=packets(),
            scoreboard_text=scoreboard(50),
            shadow_results=shadows(5),
            execution_claim_history=[
                {
                    "claim_id": "CLAIM:bbbbbbbbbbbb",
                    "routing_mode": "manual_override",
                    "status": "RUNNING",
                }
            ],
        )
        self.assertEqual(
            report["state"],
            "AWAITING_EXPLICIT_USER_APPROVAL",
        )
        self.assertTrue(
            report["gates"]["no_active_generated_claims"]
        )
        self.assertEqual(
            report["evidence"]["active_generated_claim_ids"],
            [],
        )

    def test_missing_or_unpaired_packets_block_canary(self):
        bad = packets()
        bad["packets"] = []
        bad["unpaired_recommendations"] = [
            {
                "strategy_id": "STRAT:x",
                "reason": "no_seed",
            }
        ]
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={
                "current_activations": 0
            },
            packets=bad,
            scoreboard_text=scoreboard(50),
            shadow_results=shadows(5),
        )
        self.assertIn(
            "measurement_packets_not_ready",
            {
                row["code"]
                for row in report["blockers"]
            },
        )

    def test_shadow_gate_is_real_but_already_separate(self):
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={
                "current_activations": 0
            },
            packets=packets(),
            scoreboard_text=scoreboard(50),
            shadow_results=shadows(4),
        )
        self.assertFalse(
            report["gates"]["shadow_run_gate_complete"]
        )
        self.assertIn(
            "shadow_run_gate_incomplete",
            {
                row["code"]
                for row in report["blockers"]
            },
        )

    def test_validator_rejects_self_authorized_state(self):
        report = build_restart_readiness(
            split_status=split_status(ready=True),
            activation_metrics={
                "current_activations": 0
            },
            packets=packets(),
            scoreboard_text=scoreboard(50),
            shadow_results=shadows(5),
        )
        report["state"] = "READY_FOR_CANARY_ACTIVATION"
        self.assertIn(
            "restart_state_mismatch",
            validate_restart_readiness(report),
        )


if __name__ == "__main__":
    unittest.main()
