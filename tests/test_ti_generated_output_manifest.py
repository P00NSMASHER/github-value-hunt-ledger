"""Protect live TI build output completeness before generated evidence is published.

This check performs no provider calls or file writes. It scans the immutable
build step list and all literal intelligence/ output sinks in live generators.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

from tools.retally_writer_proposal_policy import generated_manifest, safe_relative_file


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools" / "ti_build.py"
MANIFEST = ROOT / ".github" / "technology-intelligence-generated-files.txt"
SOURCE = ROOT / "tools" / "ti_persist_generated.py"
EXPECTED_RECOVERED = {
    "intelligence/search_move_metrics.json",
    "intelligence/SEARCH_MOVE_REPORT.md",
    "intelligence/search_move_policy.json",
    "intelligence/SEARCH_MOVE_POLICY.md",
    "intelligence/coordination_metrics.json",
    "intelligence/COORDINATION_REPORT.md",
    "intelligence/efficiency_metrics.json",
    "intelligence/EFFICIENCY_REPORT.md",
}


def ordered_build_steps() -> tuple[str, ...]:
    tree = ast.parse(BUILD.read_text(encoding="utf-8"), filename=str(BUILD))
    for assignment in tree.body:
        if (isinstance(assignment, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "STEPS"
                        for t in assignment.targets)):
            assert isinstance(assignment.value, ast.Tuple), (
                "TI build STEPS structure changed; re-audit outputs"
            )
            steps = []
            for row in assignment.value.elts:
                assert isinstance(row, ast.List) and row.elts, (
                    "TI build contains an uninspectable execution step"
                )
                script = row.elts[0]
                assert isinstance(script, ast.Constant) and isinstance(
                    script.value, str
                ) and script.value.startswith("tools/ti_") and script.value.endswith(
                    ".py"
                ), "TI build step is no longer a literal, approved generator"
                steps.append(script.value)
            return tuple(steps)
    raise AssertionError("TI build step list missing")


def explicitly_generated_outputs() -> dict[str, set[str]]:
    writers: dict[str, set[str]] = {}
    for script in ordered_build_steps():
        path = ROOT / script
        assert path.is_file(), f"Expected generator source missing: {script}"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=script)
        for call in ast.walk(tree):
            if not (isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr in {"write_text", "write_bytes"}):
                continue
            receiver = call.func.value
            if not (isinstance(receiver, ast.BinOp)
                    and isinstance(receiver.op, ast.Div)
                    and isinstance(receiver.left, ast.Name)
                    and receiver.left.id == "INTEL"
                    and isinstance(receiver.right, ast.Constant)
                    and isinstance(receiver.right.value, str)):
                continue
            rel = "intelligence/" + receiver.right.value
            assert safe_relative_file(rel), f"Unsafe generated output: {rel}"
            writers.setdefault(script, set()).add(rel)
    return writers


class GeneratedOutputManifestTests(unittest.TestCase):
    def test_all_literal_ti_build_outputs_are_persisted(self):
        writers = explicitly_generated_outputs()
        expected = {p for paths in writers.values() for p in paths}
        self.assertGreaterEqual(len(ordered_build_steps()), 70)
        self.assertGreaterEqual(len(expected), 85)
        covered = generated_manifest(MANIFEST)
        missing = sorted(expected - covered)
        self.assertFalse(missing, "Live TI build generates files missing from "
                         "the source-persistence manifest: " + ", ".join(missing))

    def test_all_eight_previously_omitted_outputs_are_now_covered(self):
        output_paths = {p for paths in explicitly_generated_outputs().values()
                        for p in paths}
        manifest = generated_manifest(MANIFEST)
        self.assertTrue(EXPECTED_RECOVERED <= output_paths)
        self.assertTrue(EXPECTED_RECOVERED <= manifest)

    def test_manifest_has_unique_safe_authorized_data_paths(self):
        rows = [s.strip() for s in MANIFEST.read_text(encoding="utf-8").splitlines()
                if s.strip() and not s.lstrip().startswith("#")]
        self.assertEqual(len(rows), len(set(rows)))
        self.assertTrue(all(s.startswith("intelligence/") and
                            safe_relative_file(s) for s in rows))
        self.assertTrue(all(Path(s).suffix.lower() in
                            {".json", ".jsonl", ".md", ".txt", ".csv"}
                            for s in rows))

    def test_missing_generated_sink_is_detected_without_network_access(self):
        generators = explicitly_generated_outputs()
        expected = {p for paths in generators.values() for p in paths}
        self.assertIn("intelligence/efficiency_metrics.json", expected)
        incomplete = generated_manifest(MANIFEST) - {
            "intelligence/efficiency_metrics.json"
        }
        self.assertEqual(
            sorted(expected - incomplete),
            ["intelligence/efficiency_metrics.json"],
        )

    def test_dependency_order_preserves_generated_evidence_authority(self):
        # Guard against an apparently green build persisting metrics that
        # were computed before their own prerequisite intake/derivation.
        ordered = ordered_build_steps()
        # The intake source is synchronized once before and again after
        # importing new runs. This deliberate two-phase sync is the sole
        # permitted repeated generator step.
        self.assertEqual(
            ordered[:3],
            ("tools/ti_sync.py", "tools/ti_ingest_runs.py", "tools/ti_sync.py"),
        )
        self.assertEqual(
            [i for i, script in enumerate(ordered)
             if script == "tools/ti_sync.py"],
            [0, 2],
        )
        self.assertEqual(len(ordered) - len(set(ordered)), 1)
        precedences = (
            ("tools/ti_search_move_learning.py", "tools/ti_search_move_policy.py"),
            ("tools/ti_registry.py", "tools/ti_efficiency_report.py"),
            ("tools/ti_coordination_report.py", "tools/ti_attribution.py"),
            ("tools/ti_learning_state.py", "tools/ti_learning_state_validate.py"),
            ("tools/ti_training_environment.py",
             "tools/ti_training_environment_validate.py"),
            ("tools/ti_dispatch.py", "tools/ti_dispatch_validate.py"),
        )
        for producer, consumer in precedences:
            with self.subTest(producer=producer, consumer=consumer):
                self.assertIn(producer, ordered)
                self.assertIn(consumer, ordered)
                self.assertLess(ordered.index(producer), ordered.index(consumer))

    def test_publisher_consumes_the_same_checked_manifest(self):
        publisher = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"technology-intelligence-generated-files.txt"', publisher)
        self.assertIn("stage_generated(repo, generated_paths)", publisher)
        self.assertIn("proposal_branch", publisher)
        workflow = (ROOT / ".github/workflows/technology-intelligence.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("tools/ti_persist_generated.py", workflow)
        self.assertIn("RETALLY_TECHNOLOGY_PR_ENABLED", workflow)
        policy = (ROOT / "recoveryworks/CODE_RELEASE_POLICY.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("production_release=HOLD", policy)


if __name__ == "__main__":
    unittest.main()
