"""Required repository release-lane acceptance for synthetic restore evidence.

No network, restoration, customer data, new accounts, or claims.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

RESEARCH = Path(__file__).resolve().parents[1] / 'research' / 'golden_goose' / 'restore_proof_competition'


class TestGoldenGooseRestoreEvidence(unittest.TestCase):
    def test_frozen_synthetic_evidence_and_margin_gate(self):
        run = subprocess.run(
            [sys.executable, '-m', 'unittest', '-q', 'test_restore_market_gate', 'test_restore_evidence_gate_029'],
            cwd=RESEARCH,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + '\n' + run.stderr)

    def test_no_real_revenue_or_recovery_accepted(self):
        sys.path.insert(0, str(RESEARCH))
        try:
            from restore_evidence_gate_029 import evaluate
            data = json.loads((RESEARCH / 'restore_evidence_fixture_029.json').read_text(encoding='utf-8'))
            report = evaluate(data)
        finally:
            sys.path.pop(0)
        self.assertEqual(report['synthetic_cases'], 20)
        self.assertEqual(report['consistent_unauthed'], 4)
        self.assertEqual(report['needs_review'], 8)
        self.assertEqual(report['explicit_problems'], 8)
        self.assertEqual(report['naive_backup_success_not_evidence_complete'], 15)
        self.assertEqual(report['verified_restores'], 0)
        self.assertEqual(report['verified_owner_revenue_usd'], '0.00')
        self.assertEqual(report['verified_collectible_usd'], '0.00')
        self.assertEqual(report['independent_incumbent_head_to_head'], 'NOT_RUN')
