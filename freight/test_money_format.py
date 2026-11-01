"""Regression coverage for exact monetary presentation boundaries."""
from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest

from freight.client_status_dashboard import money as dashboard_money
from freight.money_format import format_cents
from freight.pilot_reporting import dollars as pilot_dollars
from freight.recovery_claim_workflow import render_recovery_claim_batch_markdown
from freight.recovery_evidence_pack import money as evidence_pack_money
from freight.remediation_plan import _money as remediation_money


_RENDER_MODULES = (
    "audit_workflow.py",
    "carrier_action_payload.py",
    "carrier_action_workflow.py",
    "carrier_action_execution.py",
    "client_status_dashboard.py",
    "counter_review_workflow.py",
    "external_action_authorization.py",
    "pilot_reporting.py",
    "recovery_claim_workflow.py",
    "recovery_evidence_pack.py",
    "remediation_plan.py",
    "review_packet.py",
    "settlement_review_workflow.py",
    "synthetic_pilot_bundle.py",
)


class TestExactCentFormatting(unittest.TestCase):
    def test_exact_amounts_at_boundaries(self):
        examples = {
            0: "0.00",
            1: "0.01",
            99: "0.99",
            100: "1.00",
            101: "1.01",
            -1: "-0.01",
            -99: "-0.99",
            -100: "-1.00",
            -101: "-1.01",
            9_007_199_254_740_993: "90,071,992,547,409.93",
            9_223_372_036_854_775_807: "92,233,720,368,547,758.07",
            -(2**63): "-92,233,720,368,547,758.08",
        }
        for cents, expected in examples.items():
            with self.subTest(cents=cents):
                self.assertEqual(format_cents(cents), expected)

    def test_refuses_inexact_or_noninteger_inputs(self):
        for value in (True, False, 1.0, float("nan"), float("inf"),
                      Decimal("1"), "100", None):
            with self.subTest(value=repr(value)):
                with self.assertRaises(TypeError):
                    format_cents(value)

    def test_buyer_visible_surfaces_do_not_round_large_values(self):
        cents = 9_223_372_036_854_775_807
        self.assertEqual(dashboard_money(cents), "$92,233,720,368,547,758.07")
        self.assertEqual(pilot_dollars(cents), "$92,233,720,368,547,758.07")
        self.assertEqual(remediation_money(cents), "$92,233,720,368,547,758.07")
        self.assertEqual(remediation_money(None), "Not established")
        self.assertEqual(evidence_pack_money(-cents), "-$92,233,720,368,547,758.07")

    def test_claim_markdown_preserves_exact_amount(self):
        cents = 9_223_372_036_854_775_807
        record = SimpleNamespace(
            claim_id="SYNTHETIC-ONLY", finding_id="F1", currency="USD",
            amount_cents=cents, reference="R", payer_id="P", payee_id="C",
            fee_disqualified=False, finding_proof_hash="a" * 64,
            review_hash="b" * 64, record_hash="c" * 64,
        )
        batch = SimpleNamespace(
            buyer_id="synthetic", business_unit="test", state="CLAIMS_READY",
            confirmed_review_count=1, claim_count=1, fee_disqualified_count=0,
            issued_at="2026-10-21T00:00:00Z", batch_hash="d" * 64,
            records=[record],
        )
        rendered = render_recovery_claim_batch_markdown(batch)
        self.assertIn("USD 92,233,720,368,547,758.07", rendered)
        self.assertNotIn("USD 92,233,720,368,547,760.00", rendered)

    def test_money_renderers_have_no_implicit_float_division_of_cents(self):
        for name in _RENDER_MODULES:
            with self.subTest(name=name):
                tree = ast.parse(Path(__file__).with_name(name).read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (isinstance(node, ast.BinOp)
                            and isinstance(node.op, ast.Div)
                            and isinstance(node.right, ast.Constant)
                            and type(node.right.value) is int
                            and node.right.value == 100
                            and "cents" in ast.unparse(node.left)):
                        self.fail(f"{name}:{node.lineno}: cents division produces inexact display")


if __name__ == "__main__":
    unittest.main()
