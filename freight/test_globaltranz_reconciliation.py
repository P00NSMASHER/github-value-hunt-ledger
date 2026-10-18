"""Synthetic-only test cases. No real invoice numbers or customer documents."""
import unittest
from freight.research.statement_reconciliation import (
    ClaimSnapshot, SourceReferencedLiabilityTransfer, StatementLine,
    assess_claim_liability_transfer, compare,
)


def row(ref, invoice, open_amount=None, *, face=True, kind="BASE", parent=None, pro=None, bol=None):
    return StatementLine(
        invoice_ref=ref, kind=kind,
        invoice_face_cents=invoice if face else None,
        statement_original_cents=invoice,
        statement_open_cents=invoice if open_amount is None else open_amount,
        parent_ref=parent, shipment_pro=pro, shipment_bol=bol,
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
            row("EXAMPLE-1", 86109, pro="PRO-001", bol="BOL-001"),
            row("EXAMPLE-1-ADJ", 5644, kind="ADJUSTMENT", parent="EXAMPLE-1", pro="PRO-001", bol="BOL-001"),
        ], statement_control_cents=91753)
        self.assertEqual(result.row_count, 2)
        self.assertEqual(result.statement_open_cents, 91753)
        self.assertEqual(result.exception_codes, ())

    def test_adjustment_without_pro_bol_held(self):
        result = compare([
            row("BASE-1", 100),
            row("BASE-1 A", 20, kind="ADJUSTMENT", parent="BASE-1"),
        ], statement_control_cents=120)
        self.assertIn("ADJUSTMENT_SHIPMENT_IDENTITY_UNVERIFIED", result.exception_codes)
        self.assertEqual(result.verified_overcharge_cents, 0)

    def test_adjustment_pro_mismatch_held(self):
        result = compare([
            row("BASE-1", 100, pro="P-11", bol="B-11"),
            row("BASE-1 A", 20, kind="ADJUSTMENT", parent="BASE-1", pro="P-22", bol="B-11"),
        ], statement_control_cents=120)
        self.assertIn("ADJUSTMENT_SHIPMENT_IDENTITY_MISMATCH", result.exception_codes)

    def test_adjustment_bol_mismatch_held(self):
        result = compare([
            row("BASE-1", 100, pro="P-11", bol="B-11"),
            row("BASE-1 A", 20, kind="ADJUSTMENT", parent="BASE-1", pro="P-11", bol="B-22"),
        ], statement_control_cents=120)
        self.assertIn("ADJUSTMENT_SHIPMENT_IDENTITY_MISMATCH", result.exception_codes)

    def test_invoice_reference_dedup_normalizes_whitespace_and_case(self):
        with self.assertRaisesRegex(ValueError, "duplicate invoice"):
            compare([row("EXAMPLE", 100), row(" example  ", 200)], statement_control_cents=300)

    def test_parent_reference_normalization_still_requires_shipment_match(self):
        result = compare([
            row("BASE-1", 100, pro="pro-11", bol="bol-11"),
            row("BASE-1 A", 20, kind="ADJUSTMENT", parent=" base-1 ", pro="PRO-11", bol="BOL-11"),
        ], statement_control_cents=120)
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
            ClaimSnapshot("creditor_statement", 2595447, "WZ-DEBTOR", "BROKER-CREDITOR", "CLAIM-10002"),
            ClaimSnapshot("later_claim_register", 149652, "WZ-DEBTOR", "BROKER-CREDITOR", "CLAIM-10002"),
        ])
        self.assertEqual(result.statement_original_cents, 2602661)
        self.assertEqual(result.statement_open_cents, 2595447)
        self.assertIn("CONFLICTING_EXTERNAL_CLAIM_SNAPSHOTS", result.exception_codes)
        self.assertEqual(result.verified_recovered_cents, 0)
        # This is a synthetic aggregated example, not a two-invoice assertion.


    def test_different_debtors_cannot_be_called_claim_conflict(self):
        result = compare([row("EXAMPLE", 100)], statement_control_cents=100, claims=[
            ClaimSnapshot("s1", 100, "DEBTOR-WZ", "BROKER", "10002"),
            ClaimSnapshot("s2", 10, "DEBTOR-OTHER", "BROKER", "10002"),
        ])
        self.assertIn("CROSS_CLAIM_COMPARISON_BLOCKED", result.exception_codes)
        self.assertNotIn("CONFLICTING_EXTERNAL_CLAIM_SNAPSHOTS", result.exception_codes)
        self.assertEqual(result.verified_recovered_cents, 0)

    def test_different_creditors_cannot_be_called_claim_conflict(self):
        result = compare([row("EXAMPLE", 100)], statement_control_cents=100, claims=[
            ClaimSnapshot("broker", 100, "DEBTOR-WZ", "BROKER", "10002"),
            ClaimSnapshot("carrier", 10, "DEBTOR-WZ", "CARRIER-XPO", "10005"),
        ])
        self.assertIn("CROSS_CLAIM_COMPARISON_BLOCKED", result.exception_codes)
        self.assertNotIn("EXTERNAL_CLAIM_DIFFERS_FROM_STATEMENT", result.exception_codes)

    def test_distinct_claim_ids_cannot_be_conflated(self):
        result = compare([row("EXAMPLE", 100)], statement_control_cents=100, claims=[
            ClaimSnapshot("a", 100, "D", "C", "CLAIM-1"),
            ClaimSnapshot("b", 99, "D", "C", "CLAIM-2"),
        ])
        self.assertIn("CROSS_CLAIM_COMPARISON_BLOCKED", result.exception_codes)

    def test_unknown_claim_identity_requires_review(self):
        result = compare([row("EXAMPLE", 100)], statement_control_cents=100, claims=[
            ClaimSnapshot("unscoped", 25),
        ])
        self.assertIn("CLAIM_IDENTITY_UNVERIFIED", result.exception_codes)
        self.assertIn("CROSS_CLAIM_COMPARISON_BLOCKED", result.exception_codes)

    def test_case_normalized_same_claim_reconciles(self):
        result = compare([row("EXAMPLE", 100)], statement_control_cents=100, claims=[
            ClaimSnapshot("a", 100, "  debtor ", "Creditor", "00001 "),
            ClaimSnapshot("b", 100, "DEBTOR", " creditor ", "00001"),
        ])
        self.assertEqual(result.state, "RESEARCH_ARITHMETIC_ONLY")
        self.assertEqual(result.exception_codes, ())

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


class TestCourtLiabilityTransfer(unittest.TestCase):
    """Synthetic cents and identities; checks a *referenced* order, not its contents."""

    def example(self, **overrides):
        fields = dict(
            original=ClaimSnapshot("filed", 12345, "DEBTOR-A", "CREDITOR-B", "CLAIM-7"),
            revised=ClaimSnapshot("later_register", 2345, "DEBTOR-A", "CREDITOR-B", "CLAIM-7"),
            transferred_liability_cents=10000,
            receiving_entity="ASSET-BUYER-C",
            public_court_order_url=(
                "https://document.epiq11.com/document/getdocumentsbydocket/"
                "?docketId=12345&projectCode=DEMO&docketNumber=90&source=DM"
            ),
        )
        fields.update(overrides)
        return SourceReferencedLiabilityTransfer(**fields)

    def test_source_referenced_transfer_reconciles_without_cash_or_rights(self):
        outcome = assess_claim_liability_transfer(self.example())
        self.assertEqual(outcome.state, "SOURCE_REFERENCED_LIABILITY_TRANSFER")
        self.assertEqual(outcome.transferred_liability_cents, 10000)
        self.assertEqual(outcome.remaining_claim_cents, 2345)
        self.assertEqual(outcome.verified_recovered_cents, 0)
        self.assertEqual(outcome.verified_overcharge_cents, 0)
        self.assertFalse(outcome.commercial_reuse_authorized)
        self.assertEqual(outcome.exception_codes, ())

    def test_mismatched_claim_transfer_amount_remains_review_required(self):
        outcome = assess_claim_liability_transfer(
            self.example(transferred_liability_cents=9999))
        self.assertEqual(outcome.state, "REVIEW_REQUIRED")
        self.assertIn("CLAIM_TRANSFER_ARITHMETIC_MISMATCH", outcome.exception_codes)

    def test_different_debtor_disallows_transfer_attribution(self):
        outcome = assess_claim_liability_transfer(self.example(
            revised=ClaimSnapshot("later", 2345, "OTHER-DEBTOR", "CREDITOR-B", "CLAIM-7")))
        self.assertIn("CROSS_CLAIM_COMPARISON_BLOCKED", outcome.exception_codes)
        self.assertEqual(outcome.verified_recovered_cents, 0)

    def test_missing_official_order_reference_fails_closed(self):
        outcome = assess_claim_liability_transfer(
            self.example(public_court_order_url="https://example.com/unsupported"))
        self.assertIn("PUBLIC_COURT_ORDER_REFERENCE_MISSING", outcome.exception_codes)

    def test_missing_purchaser_held_for_review(self):
        outcome = assess_claim_liability_transfer(self.example(receiving_entity="  "))
        self.assertIn("TRANSFER_RECEIVING_ENTITY_UNVERIFIED", outcome.exception_codes)

    def test_negative_transfer_is_invalid(self):
        with self.assertRaises(ValueError):
            assess_claim_liability_transfer(
                self.example(transferred_liability_cents=-1))


if __name__ == "__main__":
    unittest.main()
