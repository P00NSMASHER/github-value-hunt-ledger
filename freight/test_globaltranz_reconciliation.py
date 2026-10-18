"""Synthetic-only test cases. No real invoice numbers or customer documents."""
import unittest
from freight.research.statement_reconciliation import ClaimSnapshot, StatementLine, compare


def row(ref, invoice, open_amount=None, *, face=True, kind="BASE", parent=None):
    return StatementLine(
        invoice_ref=ref, kind=kind,
        invoice_face_cents=invoice if face else None,
        statement_original_cents=invoice,
        statement_open_cents=invoice if open_amount is None else open_amount,
        parent_ref=parent,
    )


class TestReconciliation(unittest.TestCase):
    def test_exact_total_is_arithmetic_not_cash(self):
        result = compare([row("EXAMPLE-1", 500), row("EXAMPLE-2", 1000)], statement_control_cents=1500)
        self.assertEqual(result.state, "RESEARCH_ARITHMETIC_ONLY")
        self.assertEqual(result.verified_recovered_cents, 0)
        self.assertEqual(result.verified_overcharge_cents, 0)
        self.assertIsNone(result.invoice_family_count)
        self.assertFalse(result.commercial_reuse_authorized)

    def test_partial_open_balance_no_recovery_claim(self):
        result = compare([row("EXAMPLE-1", 20140, 12926)], statement_control_cents=12926)
        self.assertIn("UNEXPLAINED_BALANCE_CHANGE_NO_RECOVERY_CLAIM", result.exception_codes)
        self.assertEqual(result.verified_recovered_cents, 0)

    def test_orphan_adjustment_held(self):
        result = compare([row("EXAMPLE-ADJ", 2813, kind="ADJUSTMENT", parent="MISSING")], statement_control_cents=2813)
        self.assertIn("UNRESOLVED_ADJUSTMENT_PARENT", result.exception_codes)

    def test_known_adjustment_not_collapsed_into_base(self):
        result = compare([
            row("EXAMPLE-1", 86109),
            row("EXAMPLE-1-ADJ", 5644, kind="ADJUSTMENT", parent="EXAMPLE-1"),
        ], statement_control_cents=91753)
        self.assertEqual(result.row_count, 2)
        self.assertEqual(result.statement_open_cents, 91753)
        self.assertEqual(result.exception_codes, ())

    def test_face_mismatch_blocks(self):
        r = StatementLine("EXAMPLE-1", "BASE", 500, 600, 600)
        result = compare([r], statement_control_cents=600)
        self.assertIn("INVOICE_FACE_STATEMENT_MISMATCH", result.exception_codes)

    def test_missing_face_blocks(self):
        result = compare([row("EXAMPLE-1", 500, face=False)], statement_control_cents=500)
        self.assertIn("MISSING_INVOICE_FACE", result.exception_codes)

    def test_wrong_control_total_blocks(self):
        result = compare([row("EXAMPLE-1", 500)], statement_control_cents=499)
        self.assertFalse(result.open_balance_reconciles)
        self.assertIn("STATEMENT_CONTROL_TOTAL_MISMATCH", result.exception_codes)

    def test_claim_register_conflict_not_categorized_as_refund(self):
        result = compare([
            row("AGGREGATE-PLACEHOLDER-1", 1000000),
            row("AGGREGATE-PLACEHOLDER-2", 1602661, 1595447),
        ], statement_control_cents=2595447, claims=[
            ClaimSnapshot("creditor_statement", 2595447),
            ClaimSnapshot("later_claim_register", 149652),
        ])
        self.assertEqual(result.statement_original_cents, 2602661)
        self.assertEqual(result.statement_open_cents, 2595447)
        self.assertIn("CONFLICTING_EXTERNAL_CLAIM_SNAPSHOTS", result.exception_codes)
        self.assertEqual(result.verified_recovered_cents, 0)
        # This is a synthetic aggregated example, not a two-invoice assertion.

    def test_duplicate_reference_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate invoice"):
            compare([row("EXAMPLE", 100), row("EXAMPLE", 200)], statement_control_cents=300)

    def test_float_and_bool_rejected(self):
        with self.assertRaises(ValueError):
            compare([row("EXAMPLE", 12.34)], statement_control_cents=1234)
        with self.assertRaises(ValueError):
            compare([row("EXAMPLE", True)], statement_control_cents=1)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            compare([row("EXAMPLE", -100)], statement_control_cents=0)

    def test_claim_snapshots_cannot_have_same_source_label(self):
        with self.assertRaises(ValueError):
            compare([row("EXAMPLE", 100)], statement_control_cents=100, claims=[
                ClaimSnapshot("duplicate", 100), ClaimSnapshot("duplicate", 50),
            ])

    def test_empty_statement_not_accepted(self):
        with self.assertRaises(ValueError):
            compare([], statement_control_cents=0)

    def test_open_balance_increase_holds(self):
        result = compare([row("EXAMPLE", 100, 101)], statement_control_cents=101)
        self.assertIn("BALANCE_INCREASE_REQUIRES_SOURCE_EVIDENCE", result.exception_codes)

    def test_base_parent_mislabel_blocks(self):
        result = compare([row("EXAMPLE", 100, parent="EXAMPLE")], statement_control_cents=100)
        self.assertIn("BASE_CANNOT_HAVE_PARENT", result.exception_codes)


if __name__ == "__main__":
    unittest.main()
