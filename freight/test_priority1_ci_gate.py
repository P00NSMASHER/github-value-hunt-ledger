"""Ensure required hosted Freight unittest discovery actually runs P1 pytest gates.

No customer data, external network, payment, secrets, or new scheduler.
This is an existing-CI bridge, not an additional hosted workflow.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


class Priority1FinancialAssuranceHostedGate(unittest.TestCase):
    def test_exact_priority1_financial_adversarial_suite(self):
        root = Path(__file__).resolve().parents[1]
        command = [
            sys.executable, "-m", "pytest", "-q",
            "freight/test_priority1_financial_assurance.py",
            "--tb=short",
        ]
        result = subprocess.run(
            command, cwd=root, text=True,
            capture_output=True, timeout=180, check=False,
        )
        self.assertEqual(
            result.returncode, 0,
            "Priority 1 source-only financial regression failed:\n"
            + result.stdout[-6500:] + "\n" + result.stderr[-2500:],
        )
        self.assertIn("passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
