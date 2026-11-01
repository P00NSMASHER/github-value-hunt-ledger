"""Fail-closed source versus generated-only change classification for technology CI."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import ti_generated_source_gate as gate


class TechnologySourceGateTests(unittest.TestCase):
    def test_generated_only_has_no_second_proposal(self):
        generated = frozenset({"intelligence/ACTIVATION_BOARD.md", "intelligence/routing_metrics.json"})
        self.assertFalse(gate.requires_refresh(tuple(generated), generated))

    def test_real_scout_queue_change_rebuilds(self):
        self.assertTrue(gate.requires_refresh(
            ("intelligence/ACTIVATION_BOARD.md", "intelligence/scout_queue/HUNTER-09.json"),
            frozenset({"intelligence/ACTIVATION_BOARD.md"})))

    def test_code_and_workflow_changes_still_rebuild(self):
        generated = frozenset({"intelligence/ACTIVATION_BOARD.md"})
        for source in ("tools/ti_build.py", ".github/workflows/technology-intelligence.yml",
                       "tests/test_ti_build.py", "hunters/README.md"):
            with self.subTest(source=source):
                self.assertTrue(gate.requires_refresh((source,), generated))

    def test_empty_or_unauthorized_allowlist_conservatively_rebuilds(self):
        self.assertTrue(gate.requires_refresh((), frozenset({"a"})))
        self.assertTrue(gate.requires_refresh(("a",), frozenset()))

    def test_allowlist_rejects_traversal_and_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            name = root / gate.MANIFEST
            name.parent.mkdir(parents=True)
            for value in ("../secret", "/tmp/escape", "intelligence/a\nintelligence/a"):
                with self.subTest(value=value):
                    name.write_text(value + "\n", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        gate.generated_paths(root)

    def test_real_allowlist_contains_generated_evidence_not_scout_queue(self):
        names = gate.generated_paths()
        self.assertIn("intelligence/ACTIVATION_BOARD.md", names)
        self.assertNotIn("intelligence/scout_queue/HUNTER-09.json", names)
        self.assertNotIn("tools/ti_build.py", names)

    def test_exact_diff_rejects_invalid_sha_and_failed_git(self):
        with self.assertRaises(ValueError):
            gate.changed_paths("bad", "a"*40)
        with patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout=b"", stderr=b"auth details omitted")):
            with self.assertRaises(ValueError):
                gate.changed_paths("a"*40, "b"*40)

    def test_diff_parses_zero_delimited_paths_without_rename_shortcut(self):
        with patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess(
                args=[], returncode=0,
                stdout=b"intelligence/ACTIVATION_BOARD.md\0intelligence/scout_queue/HUNTER-09.json\0",
                stderr=b"")) as mock_run:
            paths = gate.changed_paths("a"*40, "b"*40)
        self.assertEqual(paths, ("intelligence/ACTIVATION_BOARD.md",
                                 "intelligence/scout_queue/HUNTER-09.json"))
        self.assertIn("--no-renames", mock_run.call_args.args[0])

    def test_incomplete_diff_must_not_suppress_source(self):
        with patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess(
                args=[], returncode=1, stdout=b"", stderr=b"")):
            self.assertEqual(gate.decision("a"*40, "b"*40),
                             (True, "unverified_delta_rebuild"))

    def test_derived_only_decision_is_explicit(self):
        with patch.object(gate, "changed_paths", return_value=("intelligence/ACTIVATION_BOARD.md",)):
            with patch.object(gate, "generated_paths",
                              return_value=frozenset({"intelligence/ACTIVATION_BOARD.md"})):
                self.assertEqual(gate.decision("a"*40, "b"*40), (False, "derived_only"))


if __name__ == "__main__":
    unittest.main()
