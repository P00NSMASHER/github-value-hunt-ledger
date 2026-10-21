"""Never replay historical Catalog/Integrator instructions after a new payload push."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import retally_payload_incremental as inc


ROOT = Path(__file__).resolve().parents[1]


class IncrementalPayloadTests(unittest.TestCase):
    def test_actual_integrator_history_produces_only_one_new_operation(self):
        old = (ROOT / ".github/integrator_sync_payload.md").read_text(encoding="utf-8")
        self.assertGreater(old.count("=== APPEND "), 5)
        pilot = (
            "\n\n=== APPEND lanes/retally-pr-publishing-canary-20261021.md ===\n"
            "# RETALLY GUARDED PUBLISHING PILOT — SYNTHETIC ONLY\n"
            "No customer records; financial and production acceptance HOLD.\n"
        )
        delta, count = inc.integrator_delta(old, old + pilot)
        self.assertEqual(count, 1)
        self.assertEqual(delta.count("=== APPEND "), 1)
        self.assertIn("retally-pr-publishing-canary-20261021.md", delta)
        self.assertNotIn("=== APPEND SEARCH_QUEUE.md ===", delta)
        self.assertNotIn("=== SUBSTITUTE CAPABILITIES.md ===", delta)
        self.assertEqual(delta.splitlines()[0], old.splitlines()[0])

    def test_integrator_history_never_executes_if_replaced_or_mutated(self):
        old = (ROOT / ".github/integrator_sync_payload.md").read_text(encoding="utf-8")
        sample = "\n\n=== APPEND lanes/synthetic-test-only.md ===\nNew marker payload\n"
        invalid = (
            old, old + " silent extra text", old + "\n\n",
            old.replace("MARKER:", "REWRITTEN:", 1) + sample,
            old[:-40] + sample,
            old + "\n\n=== APPEND .github/workflows/recoveryworks.yml ===\nunsafe\n",
            old + "\n\n=== REPLACE tools/ti_build.py ===\nunsafe\n",
            old + "\n\n=== APPEND lanes/synthetic-test-only.md ===\n   \n",
        )
        for current in invalid:
            with self.subTest(current_tail=current[-70:]):
                with self.assertRaises(inc.Refused):
                    inc.integrator_delta(old, current)

    def test_actual_catalog_history_only_processes_new_exact_target(self):
        old = (ROOT / ".github/catalog_append_payload.json").read_text(encoding="utf-8")
        current = json.loads(old)
        self.assertGreater(len(current["append"]), 0)
        target = "lanes/retally-canary-20261021.md"
        self.assertNotIn(target, current["append"])
        current["append"][target] = "TEST_ONLY: PR smoke; no financial claims."
        delta, count = inc.catalog_delta(old, json.dumps(current))
        result = json.loads(delta)
        self.assertEqual(count, 1)
        self.assertEqual(result["marker"], current["marker"])
        self.assertEqual(result["append"], {target: current["append"][target]})
        self.assertTrue(all(x not in result["append"]
                            for x in json.loads(old)["append"]))

    def test_catalog_refuses_replaced_existing_entries_or_duplicate_keys(self):
        old = '{"marker":"old","append":{"CAPABILITIES.md":"original"}}'
        variants = (
            '{"marker":"new","append":{"CAPABILITIES.md":"changed","lanes/extra.md":"new"}}',
            '{"marker":"new","append":{"lanes/extra.md":"new"}}',
            '{"marker":"old","append":{"CAPABILITIES.md":"original"}}',
            '{"marker":"old","append":{"CAPABILITIES.md":"original","CAPABILITIES.md":"changed","lanes/extra.md":"new"}}',
            '{"marker":"old","append":{"CAPABILITIES.md":"original","tools/code.py":"bad"}}',
            '{"marker":"old","append":{"CAPABILITIES.md":"original","lanes/../unsafe.md":"bad"}}',
            '{"marker":"old","append":{"CAPABILITIES.md":"original","lanes/new.md":""}}',
            '{"marker":"old","append":{"CAPABILITIES.md":"original","lanes/new.md":"new"},"extra":true}',
        )
        for value in variants:
            with self.subTest(value=value):
                with self.assertRaises(inc.Refused):
                    inc.catalog_delta(old, value)

    def test_changed_marker_does_not_replay_prior_catalog_operations(self):
        old = '{"marker":"old","append":{"CAPABILITIES.md":"original"}}'
        fresh = '{"marker":"new","append":{"CAPABILITIES.md":"original","lanes/test-only.md":"pilot"}}'
        delta, count = inc.catalog_delta(old, fresh)
        self.assertEqual(count, 1)
        self.assertEqual(json.loads(delta), {
            "marker": "new", "append": {"lanes/test-only.md": "pilot"}})

    def test_source_locked_event_refuses_changed_capture_and_zero_sha(self):
        with tempfile.TemporaryDirectory(prefix="retally-payload-delta-") as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"],
                           cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Bounded Test"],
                           cwd=repo, check=True)
            source = repo / ".github/catalog_append_payload.json"
            source.parent.mkdir()
            before = '{"marker":"old","append":{"CAPABILITIES.md":"original"}}'
            source.write_text(before, encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "--quiet", "-m", "before"],
                           cwd=repo, check=True)
            before_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            after = ('{"marker":"old","append":{"CAPABILITIES.md":"original",'
                     '"lanes/synthetic.md":"pilot"}}')
            source.write_text(after, encoding="utf-8")
            subprocess.run(["git", "commit", "--quiet", "-am", "after"],
                           cwd=repo, check=True)
            after_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            frozen = repo / "triggered.json"
            frozen.write_text(after, encoding="utf-8")
            delta, count = inc.extract_event_delta(
                "catalog", before_sha, after_sha, frozen, repo=repo)
            self.assertEqual(count, 1)
            self.assertEqual(tuple(json.loads(delta)["append"]), ("lanes/synthetic.md",))
            frozen.write_text(after.replace("pilot", "forged"), encoding="utf-8")
            with self.assertRaises(inc.Refused):
                inc.extract_event_delta("catalog", before_sha, after_sha, frozen, repo=repo)
            with self.assertRaises(inc.Refused):
                inc.extract_event_delta("catalog", "0" * 40, after_sha, frozen, repo=repo)
            with self.assertRaises(inc.Refused):
                inc.extract_event_delta("catalog", after_sha, after_sha, frozen, repo=repo)

    def test_two_workflows_explicitly_use_frozen_incremental_events(self):
        for name, kind in (("catalog-append.yml", "catalog"),
                           ("integrator-sync.yml", "integrator")):
            workflow = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertIn("python -m tools.retally_payload_incremental", workflow)
                self.assertIn(f"--kind {kind}", workflow)
                self.assertIn("github.event.before", workflow)
                self.assertIn("github.sha", workflow)
                self.assertIn("RETALLY_BEFORE_SHA", workflow)
                self.assertIn("RETALLY_SOURCE_SHA", workflow)
                self.assertIn("--input /tmp/", workflow)
                self.assertIn("--output /tmp/", workflow)
                self.assertNotIn(
                    "Path('/tmp/" + ("catalog_append_payload.json"
                                     if kind == "catalog"
                                     else "integrator_sync_payload.md") + "').read_text()",
                    workflow,
                )


if __name__ == "__main__":
    unittest.main()
