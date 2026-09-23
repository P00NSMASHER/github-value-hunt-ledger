from recoveryworks.test_support import source_hash as H
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.tax import (
    TaxAssessment,
    TaxTransactionLine,
    audit_tax_lines,
    normalize_jurisdiction,
    normalize_tax_category,
)


def line(*, line_id="TL-1", purchaser="client", actual=10000, verified=True,
         date="2026-08-01", jurisdiction="US-PA", category="software"):
    return TaxTransactionLine(
        tax_line_id=line_id,
        invoice_id="INV-1",
        purchaser_id=purchaser,
        vendor_id="Vendor-1",
        transaction_date=date,
        jurisdiction=jurisdiction,
        tax_category=category,
        taxable_basis_cents=100000,
        actual_tax_cents=actual,
        source_hash=H(f"line-{line_id}"),
        source_locator=f"file://tax-lines.csv#{line_id}",
        verified=verified,
    )


def assessment(*, line_id="TL-1", expected=6000, verified=True,
               date="2026-08-01", jurisdiction="US-PA", category="software",
               reviewer="tax-reviewer-1", snapshot="2026-07-31"):
    return TaxAssessment(
        assessment_id=f"A-{line_id}",
        tax_line_id=line_id,
        transaction_date=date,
        jurisdiction=jurisdiction,
        tax_category=category,
        expected_tax_cents=expected,
        taxability_basis="Reviewed exemption/rate treatment",
        source_hash=H(f"assessment-{line_id}"),
        source_locator=f"file://assessments.csv#{line_id}",
        verified=verified,
        rule_snapshot_date=snapshot,
        professional_reviewer_id=reviewer,
    )


class TaxBranchTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_jurisdiction(" us-pa "), "US-PA")
        self.assertEqual(normalize_tax_category("cloud software"), "CLOUD_SOFTWARE")

    def test_verified_reviewed_assessment_produces_validated_overpayment(self):
        batch = audit_tax_lines(
            client_id="client",
            lines=(line(),),
            assessments=(assessment(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 6000)
        self.assertEqual(finding.actual_cents, 10000)
        self.assertEqual(finding.potential_recovery_cents, 4000)
        self.assertEqual(finding.reason, "TRANSACTION_TAX_OVERPAYMENT")

    def test_unverified_assessment_stays_review(self):
        batch = audit_tax_lines(
            client_id="client",
            lines=(line(),),
            assessments=(assessment(verified=False, reviewer=None, snapshot=None),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_verified_assessment_requires_reviewer_and_rule_snapshot(self):
        with self.assertRaises(ValueError):
            assessment(reviewer=None)
        with self.assertRaises(ValueError):
            assessment(snapshot=None)

    def test_identity_mismatch_fails_closed(self):
        batch = audit_tax_lines(
            client_id="client",
            lines=(line(),),
            assessments=(assessment(jurisdiction="US-NJ"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "TAX_ASSESSMENT_IDENTITY_MISMATCH",
        )

    def test_conflicting_assessments_fail_closed(self):
        batch = audit_tax_lines(
            client_id="client",
            lines=(line(),),
            assessments=(assessment(expected=6000), assessment(expected=5000)),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "CONFLICTING_TAX_ASSESSMENTS")

    def test_duplicate_tax_line_ids_are_all_excluded(self):
        batch = audit_tax_lines(
            client_id="client",
            lines=(line(line_id="DUP"), line(line_id="DUP")),
            assessments=(assessment(line_id="DUP"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "DUPLICATE_TAX_LINE_ID")

    def test_no_overpayment_produces_no_finding(self):
        batch = audit_tax_lines(
            client_id="client",
            lines=(line(actual=6000),),
            assessments=(assessment(expected=6000),),
        )
        self.assertEqual(batch.observations, ())


if __name__ == "__main__":
    unittest.main()
