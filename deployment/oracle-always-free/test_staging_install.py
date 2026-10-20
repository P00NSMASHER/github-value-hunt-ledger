"""No-cloud regression tests for synthetic-only Oracle staging safeguards."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
INSTALLER = ROOT / "install-staging.sh"


class InstallerSafetyTests(unittest.TestCase):
    def test_preflight_before_mutation_and_atomic_promotion_after_health(self):
        script = INSTALLER.read_text(encoding="utf-8")
        self.assertLess(script.index('if [[ -e "$workspace_dir" || -L "$workspace_dir" ]]'),
                        script.index('sudo apt-get update'))
        self.assertLess(script.index('python3 -m recoveryworks.workbench_health'),
                        script.index('sudo mv -Tf -- "$candidate_link" /opt/retally/current'))
        self.assertLess(script.index('sudo systemctl daemon-reload'),
                        script.index('sudo mv -Tf -- "$candidate_link" /opt/retally/current'))
        self.assertIn('sudo mv -Tf -- "$candidate_link" /opt/retally/current', script)
        self.assertNotIn("sudo ln -sfn", script)
        self.assertNotIn("sudo rsync", script)
        # PYTHONPATH alone is insufficient: Python -m normally imports from the
        # current checkout first, including an ignored local module.
        self.assertEqual(script.count("sudo -u retally -- sh -c 'cd \"$1\" &&"), 2)
        self.assertNotIn("PYTHONPATH=$staging", script)
        self.assertIn('sudo mv -T -- "$staging" "$release_dir"', script)
        self.assertNotIn("sudo systemctl start", script)
        self.assertNotIn("sudo systemctl enable", script)

    def test_git_archive_excludes_ignored_local_secrets(self):
        script = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('git archive --format=tar "$actual_sha"', script)
        # Reproduce the exact committed-source archive mechanism offline.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo, out = root / "repo", root / "out"
            repo.mkdir()
            out.mkdir()

            def git(*args):
                return subprocess.run(["git", "-C", str(repo), *args],
                                      capture_output=True, check=True)

            git("init", "-q")
            git("config", "user.email", "ci@example.invalid")
            git("config", "user.name", "Synthetic CI")
            (repo / ".gitignore").write_text("credentials.json\nignored-secret.txt\n", encoding="utf-8")
            (repo / "allowed.py").write_text("print('synthetic')\n", encoding="utf-8")
            git("add", ".gitignore", "allowed.py")
            git("commit", "-q", "-m", "fixture")
            (repo / "credentials.json").write_text("SYNTHETIC_SECRET_NEVER_SHIP", encoding="utf-8")
            (repo / "ignored-secret.txt").write_text("ignored", encoding="utf-8")
            archive = git("archive", "--format=tar", "HEAD").stdout
            subprocess.run(["tar", "-xf", "-", "-C", str(out)],
                           input=archive, capture_output=True, check=True)
            self.assertTrue((out / "allowed.py").exists())
            self.assertFalse((out / "credentials.json").exists())
            self.assertFalse((out / "ignored-secret.txt").exists())


if __name__ == "__main__":
    unittest.main()
