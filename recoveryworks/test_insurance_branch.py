import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.insurance import (
    InsuranceClaimLine,
    InsuranceCoverageAssessment,
    InsuranceSettlement,
    audit_insurance_claims,
    normalize_coverage_category,
)


def claim(*, claimed=10000000, verified=True, claimant="client-1",
          policy="POL-1", loss_date="2026-08-01", category="property"):
    return InsuranceClaimLine(
        claim_line_id="CL-1",
        claimant_id=claimant,
        insurer_id="Insurer-1",
        policy_id=policy,
        loss_date=loss_date,
        coverage_category=category,
        claimed_cents=claimed,
        source_hash="claim-hash",
        source_locator="file://claims.csv#row=2",
        verified=verified,
    )


def assessment(*, expected=8000000, verified=True, policy="POL-1",
               loss_date="2026-08-01", category="property",
               start="2026-01-01", end="2026-12-31",
               reviewer="adjuster-1", qualification="licensed claims reviewer",
               snapshot="2026-07-31"):
    return InsuranceCoverageAssessment(
        assessment_id="A-1",
        claim_line_id="CL-1",
        policy_id=policy,
        loss_date=loss_date,
        coverage_category=category,
        expected_net_payment_cents=expected,
        coverage_basis="Reviewed policy limits, deductible, and covered loss valuation",
        policy_effective_from=start,
        policy_effective_to=end,
        source_hash="assessment-hash",
        source_locator="file://assessments.csv#row=2",
        verified=verified,
        policy_snapshot_date=snapshot,
        qualified_reviewer_id=reviewer,
        qualification_basis=qualification,
    )


def settlement(*, sid="S-1", amount=5000000, date="2026-09-01", verified=True):
    return InsuranceSettlement(
        settlement_id=sid,
        claim_line_id="CL-1",
        amount_paid_cents=amount,
        payment_date=date,
        source_hash=f"settlement-{sid}",
        source_locator=f"file://settlements.csv#{sid}",
        verified=verified,
    )


class InsuranceBranchTests(unittest.TestCase):
    def test_normalize_coverage_category(self):
        self.assertEqual(
            normalize_coverage_category("business interruption"),
            "BUSINESS_INTERRUPTION",
        )

    def test_verified_reviewed_claim_underpayment_is_validated(self):
        batch = audit_insurance_claims(
            client_id="client-1",
            claim_lines=(claim(),),
            assessments=(assessment(),),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 8000000)
        self.assertEqual(finding.actual_cents, 5000000)
        self.assertEqual(finding.potential_recovery_cents, 3000000)
        self.assertEqual(finding.reason, "INSURANCE_CLAIM_UNDERPAYMENT")

    def test_unverified_settlement_keeps_candidate_review(self):
        batch = audit_insurance_claims(
            client_id="client-1",
            claim_lines=(claim(),),
            assessments=(assessment(),),
            settlements=(settlement(verified=False),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_verified_assessment_requires_reviewer_qualification_and_snapshot(self):
        with self.assertRaises(ValueError):
            assessment(reviewer=None)
        with self.assertRaises(ValueError):
            assessment(qualification=None)
        with self.assertRaises(ValueError):
            assessment(snapshot=None)

    def test_loss_must_be_inside_reviewed_policy_period(self):
        with self.assertRaises(ValueError):
            assessment(start="2026-09-01", end="2027-09-01")

    def test_expected_payment_cannot_exceed_claimed_amount(self):
        batch = audit_insurance_claims(
            client_id="client-1",
            claim_lines=(claim(claimed=7000000),),
            assessments=(assessment(expected=8000000),),
            settlements=(settlement(amount=5000000),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "EXPECTED_PAYMENT_EXCEEDS_CLAIMED",
        )

    def test_policy_identity_mismatch_fails_closed(self):
        batch = audit_insurance_claims(
            client_id="client-1",
            claim_lines=(claim(policy="POL-1"),),
            assessments=(assessment(policy="POL-2"),),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "COVERAGE_ASSESSMENT_IDENTITY_MISMATCH",
        )

    def test_duplicate_settlement_blocks_claim(self):
        batch = audit_insurance_claims(
            client_id="client-1",
            claim_lines=(claim(),),
            assessments=(assessment(),),
            settlements=(settlement(sid="DUP"), settlement(sid="DUP")),
        )
        self.assertEqual(batch.observations, ())
        codes = {item.code for item in batch.exceptions}
        self.assertIn("DUPLICATE_INSURANCE_SETTLEMENT_ID", codes)
        self.assertIn("CLAIM_BLOCKED_BY_DUPLICATE_SETTLEMENT", codes)

    def test_settlement_cannot_precede_loss(self):
        batch = audit_insurance_claims(
            client_id="client-1",
            claim_lines=(claim(loss_date="2026-08-01"),),
            assessments=(assessment(loss_date="2026-08-01"),),
            settlements=(settlement(date="2026-07-31"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "SETTLEMENT_PRECEDES_LOSS")


if __name__ == "__main__":
    unittest.main()
