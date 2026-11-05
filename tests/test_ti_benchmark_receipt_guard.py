"""Source-bound frozen benchmark restart: adversarial and real-corpus invariants."""
from pathlib import Path
import tempfile
import unittest

from tools.ti_benchmark_receipt_guard import (
    BenchmarkReceiptError, pair_tasks, validate_benchmark_receipts,
)


class BenchmarkReceiptGuardTests(unittest.TestCase):
    def fixture(self, root):
        target = root / "benchmark" / "results"
        target.mkdir(parents=True)
        for pair in range(1, 8):
            for arm in ("control", "experiment"):
                path = target / f"pair{pair}-{arm}.md"
                path.write_text("# Frozen benchmark\n", encoding="utf-8")
        target.joinpath("pair1-control.md").write_text(
            "# Control\nTASK: 01 — Example\nCONDITION: CONTROL\n",
            encoding="utf-8",
        )
        target.joinpath("pair1-experiment.md").write_text(
            "# Experiment\nTASK: 01 — Independent example\nCONDITION: EXPERIMENT\n",
            encoding="utf-8",
        )

    def test_scoreboard_counts_only_real_frozen_pairs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            score = ("Matched tasks scored: **1**\n"
                     "| Task | Condition | Score |\n"
                     "|---|---|---|\n"
                     "| 01 | CONTROL | 20 |\n"
                     "| 01 | EXPERIMENT | 19 |\n")
            report = validate_benchmark_receipts(root, score)
            self.assertEqual(report["matched_scored_tasks"], 1)
            self.assertEqual(report["raw_result_arm_records"], 2)
            self.assertEqual(report["activation_authority"], "NONE")

    def test_no_scoreboard_only_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            fake = ("Matched tasks scored: **2**\n"
                    "| 01 | CONTROL | 20 |\n"
                    "| 01 | EXPERIMENT | 19 |\n"
                    "| 02 | CONTROL | 20 |\n"
                    "| 02 | EXPERIMENT | 19 |\n")
            with self.assertRaisesRegex(BenchmarkReceiptError, "without underlying"):
                validate_benchmark_receipts(root, fake)

    def test_reject_fake_summary_count_and_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            for score in (
                "Matched tasks scored: **50**\n| 01 | CONTROL | 20 |\n| 01 | EXPERIMENT | 19 |\n",
                "Matched tasks scored: **1**\n| 01 | CONTROL | 20 |\n| 01 | CONTROL | 20 |\n| 01 | EXPERIMENT | 19 |\n",
            ):
                with self.subTest(score=score), self.assertRaises(BenchmarkReceiptError):
                    validate_benchmark_receipts(root, score)

    def test_reject_result_in_wrong_pair_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "benchmark" / "results" / "pair2-control.md").write_text(
                "TASK: 06 — Wrong pair\n", encoding="utf-8")
            with self.assertRaisesRegex(BenchmarkReceiptError, "wrong-pair"):
                validate_benchmark_receipts(root, "Matched tasks scored: **0**\n")

    def test_production_source_and_triggers_are_safe(self):
        root = Path(__file__).resolve().parents[1]
        report = validate_benchmark_receipts(
            root, (root / "benchmark" / "SCOREBOARD.md").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(report["matched_scored_tasks"], 47)
        workflow = (root / ".github" / "workflows" /
                    "technology-intelligence.yml").read_text(encoding="utf-8")
        for path in ("benchmark/results/**", "benchmark/SCOREBOARD.md"):
            self.assertEqual(workflow.count('"' + path + '"'), 2)
        self.assertNotIn("BENCHMARK_GOLD.md", workflow)
        build = (root / "tools" / "ti_build.py").read_text(encoding="utf-8")
        self.assertIn("ti_benchmark_receipt_guard.py", build)
        self.assertLess(build.index("ti_benchmark_receipt_guard.py"),
                        build.index("ti_restart_readiness.py"))
        scout = (root / ".github" / "workflows" /
                 "public-repo-hunter.yml").read_text(encoding="utf-8")
        self.assertEqual(scout.count("- cron:"), 15)

    def test_exact_original_pair_partition(self):
        self.assertEqual(pair_tasks(1), {f"{i:02d}" for i in range(1, 9)})
        self.assertEqual(pair_tasks(7), {f"{i:02d}" for i in range(44, 51)})
        with self.assertRaises(BenchmarkReceiptError):
            pair_tasks(8)


if __name__ == "__main__":
    unittest.main()
