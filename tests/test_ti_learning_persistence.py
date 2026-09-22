from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "technology-intelligence.yml"
BUILD = ROOT / "tools" / "ti_build.py"


class LearningPersistenceTests(unittest.TestCase):
    def test_build_generates_learning_state_and_network_priors(self):
        text = BUILD.read_text(encoding="utf-8")
        learning = "tools/ti_learning_state.py"
        priors = "tools/ti_network_priors.py"
        self.assertIn(learning, text)
        self.assertIn(priors, text)
        self.assertLess(text.index(learning), text.index(priors))

    def test_main_persistence_stages_all_live_learning_artifacts(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        required = [
            "intelligence/LEARNING_STATE.json",
            "intelligence/learning_curriculum.json",
            "intelligence/LEARNING_CURRICULUM.md",
            "intelligence/TRAINING_ENVIRONMENT.json",
            "intelligence/training_episodes.jsonl",
            "intelligence/NETWORK_PRIORS.md",
        ]
        for path in required:
            with self.subTest(path=path):
                self.assertIn(path, text)

    def test_generated_persistence_remains_main_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "github.event_name == 'push' && github.ref == 'refs/heads/main'",
            text,
        )

    def test_pr_validation_cancels_only_superseded_pr_runs(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "cancel-in-progress: ${{ github.event_name == 'pull_request' }}",
            text,
        )
        self.assertIn(
            "github.event_name == 'push' && github.ref == 'refs/heads/main'",
            text,
        )


if __name__ == "__main__":
    unittest.main()
