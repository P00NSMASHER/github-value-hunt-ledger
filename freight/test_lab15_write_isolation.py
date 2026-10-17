"""Guard that recurring Lab 15 evidence discovery never writes protected main."""
from pathlib import Path
import unittest


WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github/workflows/retally-lab15-evidence-acquisition.yml"
)


class Lab15WriteIsolationTests(unittest.TestCase):
    def test_automatic_discovery_isolated_ledger_branch(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("EVIDENCE_BRANCH: research/retally-lab15-source-ledger", text)
        self.assertIn('git push origin "HEAD:refs/heads/$EVIDENCE_BRANCH"', text)
        self.assertNotIn("git push origin HEAD:main", text)
        self.assertNotIn("git pull --rebase origin main", text)

    def test_pr_runs_have_no_automatic_write_path(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event_name == 'schedule'", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn("needs: validate", text)
        self.assertIn("contents: write", text)

    def test_no_customer_invoices_or_nonmetadata_committed(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "git add -- freight/lab15/evidence_ledger.json freight/lab15/triage_queue.json",
            text,
        )
        self.assertIn("validate_queue", text)
        self.assertIn("cmp freight/lab15/triage_queue.json", text)
        self.assertNotIn("git add -A", text)
        self.assertNotIn("git push -f", text)


if __name__ == "__main__":
    unittest.main()
