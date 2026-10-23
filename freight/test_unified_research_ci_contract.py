"""Reject CI command folding that silently omits research evaluation exercises.

This checks executable lines inside the GitHub Actions verify job. It does not
claim independent ground-truth labels or approval of external source rights.
"""
from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "retally-unified-research-lab.yml"


class ResearchCIVerificationContract(unittest.TestCase):
    def test_node_bridge_and_frozen_pack_are_separate_executable_commands(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("\n  verify:\n"), 1)
        self.assertEqual(text.count("\n  discover:\n"), 1)
        verify = text.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        expected = (
            "          node --test freight/research_lab_worker.test.mjs",
            "          python -m unittest -q freight.test_research_eval_bridge freight.test_unified_research_ci_contract",
            "          python -m freight.real_world_eval_v1",
        )
        lines = verify.splitlines()
        for command in expected:
            with self.subTest(command=command.strip()):
                self.assertEqual(lines.count(command), 1, "Missing or folded CI evaluation command")
        self.assertIn("        run: |", verify)
        self.assertNotIn("node --test freight/research_lab_worker.test.mjs freight.test_research_eval_bridge", verify)


    def test_dob_source_scope_evidence_is_really_executed_on_pr_and_push(self):
        """Prevent green CI that silently omits the DOB provenance fixtures."""
        workflow = WORKFLOW.read_text(encoding="utf-8")
        verify = workflow.split("\n  verify:\n", 1)[1].split("\n  discover:\n", 1)[0]
        executable = "          python -m unittest -q freight.test_nyc_dob_source_scope_v1 freight.test_nyc_dob_excluded_scope_v1"
        self.assertEqual(verify.splitlines().count(executable), 1)
        triggers = workflow.split("\npermissions:\n", 1)[0]
        for pattern in (
            '      - "freight/fixtures/nyc_dob_*_v1.json"',
            '      - "freight/test_nyc_dob_*_v1.py"',
        ):
            with self.subTest(path=pattern):
                self.assertEqual(triggers.splitlines().count(pattern), 2)



if __name__ == "__main__":
    unittest.main()
