"""Repository CI must exercise local-only Golden Goose #031 private freight falsifier.

No customer data, network, carrier contact or revenue claims.
"""
from pathlib import Path
import subprocess
import sys
import unittest

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "golden_goose" / "private_freight_cash_gate_031"

class TestGoldenGoosePrivateFreightCash(unittest.TestCase):
    def test_adversarial_fee_cases(self):
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "-q", "test_private_freight_cash_gate_031"],
            cwd=RESEARCH,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + "\n" + completed.stderr)
