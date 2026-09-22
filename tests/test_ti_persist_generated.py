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


if __name__ == "__main__":
    unittest.main()
