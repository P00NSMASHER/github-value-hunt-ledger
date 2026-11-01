"""Prove the required release lane discovers new tests, not only a file list.

Subprocess probes use temporary invented tests and the actual workflow command.
They do not access customer data or certify production behavior.
"""
from pathlib import Path
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/repository-release-gate.yml"
STEP_NAME = "Run complete Freight pytest suite"


def discovery_step(source):
    """Read the one repository-style step; fail rather than guess changed YAML."""
    lane = re.search(r"(?ms)^  freight:\n.*?(?=^  [^ \n]|\Z)", source)
    if lane is None:
        raise AssertionError("Required Freight release lane is missing")
    step = re.search(
        rf"(?ms)^      - name: {re.escape(STEP_NAME)}\n.*?"
        r"(?=^      - |\Z)", lane.group(0)
    )
    if step is None:
        raise AssertionError("Complete recursive pytest release step is missing")
    return step.group(0)


def discovery_command(source):
    step = discovery_step(source)
    command = re.search(r"(?m)^        run: (.+)$", step)
    if command is None:
        raise AssertionError("Recursive discovery needs an explicit command")
    words = shlex.split(command.group(1))
    expected = ["PYTHONPATH=.", "python", "-m", "pytest", "-q", "freight"]
    if words != expected:
        raise AssertionError("Full Freight discovery must not filter or mask failures")
    # Use this interpreter while preserving all test-runner arguments.
    return [sys.executable, *words[2:]]


class ReleaseDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.source = WORKFLOW.read_text(encoding="utf-8")
        self.temporary = tempfile.TemporaryDirectory(prefix="retally-discovery-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "freight/commercial").mkdir(parents=True)

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def run_command(self, command):
        # No inherited tokens, pytest options, plugins, or shell startup files.
        env = {"PATH": os.defpath, "PYTHONPATH": ".",
               "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
        return subprocess.run(command, cwd=self.root, env=env,
                              capture_output=True, text=True, timeout=20, check=False)

    def run_discovery(self, *extra):
        return self.run_command([*discovery_command(self.source), *extra])

    def test_complete_discovery_is_mandatory_and_keeps_original_checks(self):
        step = discovery_step(self.source)
        self.assertEqual(discovery_command(self.source)[1:],
                         ["-m", "pytest", "-q", "freight"])
        for bypass in ("if:", "continue-on-error:", "working-directory:"):
            self.assertNotIn(bypass, step)
        self.assertIn('python -m unittest discover -s freight -p "test_*.py" -v',
                      self.source)
        self.assertIn('test "$FREIGHT_RESULT" = "success"', self.source)
        self.assertIn('test "$FREIGHT_COMMERCIAL_RESULT" = "success"', self.source)

    def test_old_unittest_discovery_misses_a_failing_function_test(self):
        self.write("freight/test_new_function.py", "def test_new_failure():\n    assert False\n")
        self.write("freight/test_existing_class.py", "import unittest\n"
                   "class ExistingCase(unittest.TestCase):\n"
                   "    def test_known(self):\n        self.assertTrue(True)\n")
        old = self.run_command([sys.executable, "-m", "unittest", "discover",
                                "-s", "freight", "-p", "test_*.py", "-v"])
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assertIn("Ran 1 test", old.stderr)
        self.assertEqual(self.run_discovery().returncode, 1)

    def test_collects_functions_parameters_classes_and_nested_new_files(self):
        self.write("freight/test_new_mixed.py", "import pytest\nimport unittest\n"
                   "def test_plain():\n    assert True\n"
                   "@pytest.mark.parametrize('value', [1, 2])\n"
                   "def test_parameter(value):\n    assert value > 0\n"
                   "class ExistingCase(unittest.TestCase):\n"
                   "    def test_class(self):\n        self.assertTrue(True)\n")
        self.write("freight/commercial/test_new_nested.py",
                   "def test_nested():\n    assert True\n")
        result = self.run_discovery("--collect-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        for node in ("test_plain", "test_parameter[1]", "test_parameter[2]",
                     "ExistingCase::test_class", "test_new_nested.py::test_nested"):
            self.assertIn(node, result.stdout)
        self.assertIn("5 tests collected", result.stdout)
        execution = self.run_discovery()
        self.assertEqual(execution.returncode, 0, execution.stderr)
        self.assertIn("5 passed", execution.stdout)

    def test_new_nested_failure_blocks_release(self):
        self.write("freight/test_known.py", "def test_known():\n    assert True\n")
        self.write("freight/commercial/test_unlisted.py",
                   "def test_unlisted():\n    assert False, 'UNLISTED_FAILURE'\n")
        result = self.run_discovery()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("UNLISTED_FAILURE", result.stdout)

    def test_empty_population_is_not_a_pass(self):
        result = self.run_discovery()
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

    def test_collection_error_is_not_a_pass(self):
        self.write("freight/test_bad_collection.py", "def broken(:\n")
        result = self.run_discovery()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("SyntaxError", result.stdout)

    def test_narrowed_or_error_masked_commands_are_rejected(self):
        # Validate the same command reader against deliberate scope regressions.
        discovery_command(self.source)
        normal = "PYTHONPATH=. python -m pytest -q freight"
        for replacement in (
            normal + " -k known", normal + " --ignore=freight/commercial",
            normal + " || true", normal + " --collect-only",
            normal.replace("-q freight", "-q freight/test_known.py"),
        ):
            with self.subTest(replacement=replacement):
                with self.assertRaises(AssertionError):
                    discovery_command(self.source.replace(normal, replacement))


if __name__ == "__main__":
    unittest.main()
