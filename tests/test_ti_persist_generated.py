import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ti_persist_generated import (  # noqa: E402
    is_non_fast_forward_failure,
    persist_generated,
)


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(repo, "git", *args)


class PersistGeneratedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            prefix="ti-persist-race-"
        )
        self.root = Path(self.tmp.name)
        self.remote = self.root / "remote.git"
        self.worker = self.root / "worker"
        self.racer = self.root / "racer"

        run(
            self.root,
            "git",
            "init",
            "--bare",
            str(self.remote),
        )
        run(
            self.root,
            "git",
            "clone",
            str(self.remote),
            str(self.worker),
        )
        git(self.worker, "switch", "-c", "main")
        git(self.worker, "config", "user.name", "test")
        git(self.worker, "config", "user.email", "test@example.com")
        (self.worker / "source.txt").write_text(
            "base\n",
            encoding="utf-8",
        )
        (self.worker / "generated.txt").write_text(
            "old\n",
            encoding="utf-8",
        )
        (self.worker / "unrelated.txt").write_text(
            "clean\n",
            encoding="utf-8",
        )
        git(self.worker, "add", ".")
        git(self.worker, "commit", "-m", "initial")
        git(self.worker, "push", "-u", "origin", "main")

        run(
            self.root,
            "git",
            "clone",
            "--branch",
            "main",
            str(self.remote),
            str(self.racer),
        )
        git(self.racer, "config", "user.name", "racer")
        git(self.racer, "config", "user.email", "racer@example.com")

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def rebuild(repo: Path) -> None:
        source = (repo / "source.txt").read_text(
            encoding="utf-8"
        ).strip()
        (repo / "generated.txt").write_text(
            f"generated:{source}\n",
            encoding="utf-8",
        )

    def test_non_fast_forward_race_rebuilds_on_new_main(self):
        self.rebuild(self.worker)

        def race(attempt: int) -> None:
            if attempt != 1:
                return
            (self.racer / "source.txt").write_text(
                "new-main\n",
                encoding="utf-8",
            )
            git(self.racer, "add", "source.txt")
            git(self.racer, "commit", "-m", "concurrent main")
            git(self.racer, "push", "origin", "main")

        result = persist_generated(
            self.worker,
            ["generated.txt"],
            max_attempts=3,
            rebuild_fn=self.rebuild,
            before_push=race,
        )

        self.assertEqual(result["status"], "pushed")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["rebuilt_attempts"], 1)

        verify = self.root / "verify"
        run(
            self.root,
            "git",
            "clone",
            "--branch",
            "main",
            str(self.remote),
            str(verify),
        )
        self.assertEqual(
            (verify / "source.txt").read_text(encoding="utf-8"),
            "new-main\n",
        )
        self.assertEqual(
            (verify / "generated.txt").read_text(
                encoding="utf-8"
            ),
            "generated:new-main\n",
        )

    def test_race_retry_can_clean_untracked_build_contamination(self):
        contaminant = self.worker / "contaminant.txt"
        contaminant.write_text(
            "stale-from-lost-attempt\n",
            encoding="utf-8",
        )

        def contaminated_rebuild(repo: Path) -> None:
            source = (repo / "source.txt").read_text(
                encoding="utf-8"
            ).strip()
            stale = (
                (repo / "contaminant.txt").read_text(
                    encoding="utf-8"
                ).strip()
                if (repo / "contaminant.txt").exists()
                else ""
            )
            (repo / "generated.txt").write_text(
                f"generated:{source}:{stale}\n",
                encoding="utf-8",
            )

        contaminated_rebuild(self.worker)

        def race(attempt: int) -> None:
            if attempt != 1:
                return
            (self.racer / "source.txt").write_text(
                "new-main\n",
                encoding="utf-8",
            )
            git(self.racer, "add", "source.txt")
            git(self.racer, "commit", "-m", "concurrent main")
            git(self.racer, "push", "origin", "main")

        result = persist_generated(
            self.worker,
            ["generated.txt"],
            max_attempts=3,
            rebuild_fn=contaminated_rebuild,
            before_push=race,
            clean_untracked_on_rebuild=True,
        )

        self.assertEqual(result["status"], "pushed")
        self.assertFalse(contaminant.exists())

        verify = self.root / "verify-clean-race"
        run(
            self.root,
            "git",
            "clone",
            "--branch",
            "main",
            str(self.remote),
            str(verify),
        )
        self.assertEqual(
            (verify / "generated.txt").read_text(
                encoding="utf-8"
            ),
            "generated:new-main:\n",
        )

    def test_local_default_does_not_clean_untracked_files(self):
        local_only = self.worker / "local-only.txt"
        local_only.write_text("keep-me\n", encoding="utf-8")
        self.rebuild(self.worker)

        result = persist_generated(
            self.worker,
            ["generated.txt"],
            max_attempts=2,
            rebuild_fn=self.rebuild,
        )

        self.assertEqual(result["status"], "pushed")
        self.assertTrue(local_only.exists())

    def test_only_whitelisted_generated_paths_are_committed(self):
        self.rebuild(self.worker)
        (self.worker / "unrelated.txt").write_text(
            "dirty-local-only\n",
            encoding="utf-8",
        )

        result = persist_generated(
            self.worker,
            ["generated.txt"],
            max_attempts=2,
            rebuild_fn=self.rebuild,
        )
        self.assertEqual(result["status"], "pushed")

        verify = self.root / "verify-whitelist"
        run(
            self.root,
            "git",
            "clone",
            "--branch",
            "main",
            str(self.remote),
            str(verify),
        )
        self.assertEqual(
            (verify / "unrelated.txt").read_text(
                encoding="utf-8"
            ),
            "clean\n",
        )

    def test_clean_generated_state_is_noop(self):
        result = persist_generated(
            self.worker,
            ["generated.txt"],
            max_attempts=2,
            rebuild_fn=self.rebuild,
        )
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["attempts"], 1)

    def test_non_fast_forward_detection_is_narrow(self):
        rejected = subprocess.CompletedProcess(
            args=["git", "push"],
            returncode=1,
            stdout="",
            stderr="! [rejected] HEAD -> main (fetch first)",
        )
        auth = subprocess.CompletedProcess(
            args=["git", "push"],
            returncode=1,
            stdout="",
            stderr="fatal: authentication failed",
        )
        self.assertTrue(is_non_fast_forward_failure(rejected))
        self.assertFalse(is_non_fast_forward_failure(auth))


    def test_isolated_technology_proposal_preserves_current_main(self):
        branch = "automation/retally-technology-39603064849-1"
        original_main = git(self.worker, "rev-parse", "HEAD").stdout.strip()
        self.rebuild(self.worker)
        result = persist_generated(
            self.worker, ["generated.txt"], proposal_branch=branch,
            rebuild_fn=self.rebuild, max_attempts=3,
        )
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(result["branch"], branch)
        self.assertEqual(result["base_sha"], original_main)
        self.assertEqual(result["attempts"], 1)
        # No implicit fallback or mirror push to main.
        after_main = git(self.worker, "ls-remote", "--heads", "origin", "main")
        self.assertEqual(after_main.stdout.split()[0], original_main)
        after_branch = git(self.worker, "ls-remote", "--heads", "origin", branch)
        self.assertEqual(after_branch.stdout.split()[0], result["head_sha"])

    def test_refuse_unapproved_proposal_branch_without_remote_write(self):
        self.rebuild(self.worker)
        original_main = git(self.worker, "rev-parse", "HEAD").stdout.strip()
        for branch in ("main", "automation/retally-scout-39603064849-1",
                       "automation/retally-technology-0-1",
                       "automation/retally-technology-39603064849-1/extra"):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                persist_generated(self.worker, ["generated.txt"],
                                  proposal_branch=branch, rebuild_fn=self.rebuild)
        after_main = git(self.worker, "ls-remote", "--heads", "origin", "main")
        self.assertEqual(after_main.stdout.split()[0], original_main)

    def test_existing_remote_proposal_is_not_overwritten_or_force_pushed(self):
        branch = "automation/retally-technology-39603064849-1"
        original_main = git(self.worker, "rev-parse", "HEAD").stdout.strip()
        git(self.racer, "switch", "-c", branch)
        (self.racer / "generated.txt").write_text("existing evidence\n", encoding="utf-8")
        git(self.racer, "add", "generated.txt")
        git(self.racer, "commit", "-m", "pre-existing external proposal")
        git(self.racer, "push", "origin", "HEAD:refs/heads/" + branch)
        original_proposal = git(self.racer, "rev-parse", "HEAD").stdout.strip()
        self.rebuild(self.worker)
        with self.assertRaisesRegex(RuntimeError, "isolated technology evidence branch push failed"):
            persist_generated(self.worker, ["generated.txt"],
                              proposal_branch=branch, rebuild_fn=self.rebuild)
        after_branch = git(self.worker, "ls-remote", "--heads", "origin", branch)
        self.assertEqual(after_branch.stdout.split()[0], original_proposal)
        after_main = git(self.worker, "ls-remote", "--heads", "origin", "main")
        self.assertEqual(after_main.stdout.split()[0], original_main)


if __name__ == "__main__":
    unittest.main()
