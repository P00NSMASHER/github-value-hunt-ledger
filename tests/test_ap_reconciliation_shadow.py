import unittest

from recoveryworks.branches.ap import (
    APObligation,
    APPayment,
    APVendorStatementLine,
)
from recoveryworks.branches.ap_shadow import shadow_ap_reconciliation


def payment(payment_id, amount, *, invoice="INV-1", day="2026-02-01"):
    return APPayment(
        payment_id=payment_id,
        vendor_id="VENDOR-A",
        invoice_number=invoice,
        amount_cents=amount,
        payment_date=day,
        source_hash=f"pay-{payment_id}",
        source_locator=f"payments.csv#{payment_id}",
        verified=True,
    )


def obligation(amount, *, invoice="INV-1", day="2026-01-01"):
    return APObligation(
        vendor_id="VENDOR-A",
        invoice_number=invoice,
        expected_cents=amount,
        source_hash=f"obligation-{invoice}",
        source_locator=f"invoices.csv#{invoice}",
        effective_from=day,
        verified=True,
    )


class APReconciliationShadowTests(unittest.TestCase):
    def test_split_payment_fully_reconciles_without_legacy_candidate(self):
        report = shadow_ap_reconciliation(
            client_id="CLIENT-1",
            payments=[payment("P1", 6000), payment("P2", 4000)],
            obligations=[obligation(10000)],
        )
        self.assertEqual(report.legacy_candidates, ())
        self.assertEqual(report.disagreements, ())
        self.assertEqual(report.kernel_matched_references, ("VENDOR-A/INV-1",))
        self.assertEqual(report.kernel_residual_payment_references, ())
        self.assertEqual(report.kernel_result.matches[0].receipt.rule, "many-to-one")

    def test_overpayment_candidate_has_kernel_residual(self):
        report = shadow_ap_reconciliation(
            client_id="CLIENT-1",
            payments=[payment("P1", 10000), payment("P2", 10000)],
            obligations=[obligation(10000)],
        )
        self.assertEqual(len(report.legacy_candidates), 1)
        self.assertEqual(
            report.legacy_candidates[0].reason,
            "AP_OBLIGATION_OVERPAYMENT",
        )
        self.assertEqual(
            report.legacy_candidates[0].potential_recovery_cents,
            10000,
        )
        self.assertEqual(report.disagreements, ())
        self.assertEqual(
            report.kernel_residual_payment_references,
            ("VENDOR-A/INV-1",),
        )

    def test_suspected_duplicate_without_obligation_is_shadowed_as_residual(self):
        report = shadow_ap_reconciliation(
            client_id="CLIENT-1",
            payments=[payment("P1", 7500), payment("P2", 7500)],
        )
        self.assertEqual(len(report.legacy_candidates), 1)
        self.assertEqual(
            report.legacy_candidates[0].reason,
            "SUSPECTED_DUPLICATE_PAYMENT",
        )
        self.assertEqual(report.disagreements, ())
        self.assertEqual(
            report.kernel_residual_payment_references,
            ("VENDOR-A/INV-1",),
        )

    def test_missing_payment_date_marks_shadow_incomplete_not_disagreement(self):
        missing_date = APPayment(
            payment_id="P2",
            vendor_id="VENDOR-A",
            invoice_number="INV-1",
            amount_cents=10000,
            payment_date=None,
            source_hash="pay-P2",
            source_locator="payments.csv#P2",
            verified=True,
        )
        report = shadow_ap_reconciliation(
            client_id="CLIENT-1",
            payments=[payment("P1", 10000), missing_date],
            obligations=[obligation(10000)],
        )
        self.assertFalse(report.comparison_complete)
        self.assertEqual(report.disagreements, ())
        self.assertEqual(len(report.exclusions), 1)
        self.assertEqual(
            report.exclusions[0].code,
            "MISSING_PAYMENT_DATE_FOR_SHADOW",
        )

    def test_statement_only_credit_stays_outside_kernel_comparison_scope(self):
        statement = APVendorStatementLine(
            vendor_id="VENDOR-A",
            invoice_number="INV-1",
            balance_cents=-2500,
            statement_date="2026-03-01",
            source_hash="statement",
            source_locator="statement.csv#2",
            verified=True,
        )
        report = shadow_ap_reconciliation(
            client_id="CLIENT-1",
            payments=[],
            statements=[statement],
        )
        self.assertEqual(report.legacy_candidates, ())
        self.assertEqual(report.disagreements, ())
        self.assertEqual(report.kernel_result.matches, ())

    def test_shadow_does_not_change_legacy_result_on_date_window_difference(self):
        report = shadow_ap_reconciliation(
            client_id="CLIENT-1",
            payments=[
                payment("P1", 10000, day="2026-12-31"),
                payment("P2", 10000, day="2026-12-31"),
            ],
            obligations=[obligation(10000, day="2026-01-01")],
            date_window_days=30,
        )
        self.assertEqual(len(report.legacy_candidates), 1)
        self.assertEqual(report.disagreements, ())
        self.assertIn("VENDOR-A/INV-1", report.kernel_residual_payment_references)


if __name__ == "__main__":
    unittest.main()
