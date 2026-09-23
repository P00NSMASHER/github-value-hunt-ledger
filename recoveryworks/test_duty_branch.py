from recoveryworks.test_support import source_hash as H
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.duty import (
    DutyAssessment,
    DutyEntryLine,
    audit_duty_entries,
    normalize_hts,
)


def entry(*, actual=30000, verified=True, hts="6109.10.00", origin="CN"):
    return DutyEntryLine(
        entry_line_id="EL-1",
        entry_id="E-1",
        importer_id="Importer-1",
        broker_id="Broker-1",
        import_date="2026-08-01",
        hts_code=hts,
        origin_country=origin,
        actual_total_cents=actual,
        source_hash=H("entry-hash"),
        source_locator="file://entries.csv#row=2",
        verified=verified,
    )


def assessment(
    *,
    verified=True,
    hts="6109.10.00",
    origin="CN",
    import_date="2026-08-01",
    reviewer="broker-reviewer-1",
):
    return DutyAssessment(
        assessment_id="A-1",
        entry_line_id="EL-1",
        import_date=import_date,
        hts_code=hts,
        origin_country=origin,
        base_duty_cents=16500,
        additional_duty_cents=5000,
        mpf_cents=346,
        hmf_cents=125,
        other_cents=0,
        source_hash=H("assessment-hash"),
        source_locator="file://assessments.csv#row=2",
        verified=verified,
        schedule_snapshot_date="2026-07-31",
        professional_reviewer_id=reviewer if verified else None,
    )


class DutyBranchTests(unittest.TestCase):
    def test_hts_normalization(self):
        self.assertEqual(normalize_hts("6109.10.00"), "61091000")

    def test_verified_reviewed_assessment_produces_validated_overpayment(self):
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(),),
            assessments=(assessment(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 21971)
        self.assertEqual(finding.potential_recovery_cents, 8029)
        self.assertEqual(
            finding.metadata["professional_reviewer_id"],
            "broker-reviewer-1",
        )

    def test_verified_assessment_requires_professional_reviewer(self):
        with self.assertRaises(ValueError):
            assessment(reviewer=None)

    def test_unverified_entry_or_assessment_stays_review(self):
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(verified=False),),
            assessments=(assessment(),),
        )
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_hts_mismatch_fails_closed(self):
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(hts="6109.10.00"),),
            assessments=(assessment(hts="9503.00.00"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "ASSESSMENT_IDENTITY_MISMATCH")

    def test_origin_mismatch_fails_closed(self):
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(origin="CN"),),
            assessments=(assessment(origin="VN"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertIn("origin_country", batch.exceptions[0].detail)

    def test_date_mismatch_fails_closed(self):
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(),),
            assessments=(assessment(import_date="2026-08-02"),),
        )
        self.assertEqual(batch.observations, ())
        self.assertIn("import_date", batch.exceptions[0].detail)

    def test_no_assessment_is_exception_not_guess(self):
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(),),
            assessments=(),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "NO_REVIEWED_ASSESSMENT")

    def test_conflicting_assessments_fail_closed(self):
        other = DutyAssessment(
            **{
                **assessment().__dict__,
                "assessment_id": "A-2",
                "base_duty_cents": 16000,
            }
        )
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(),),
            assessments=(assessment(), other),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "CONFLICTING_ASSESSMENTS")

    def test_no_overpayment_produces_no_finding(self):
        batch = audit_duty_entries(
            client_id="importer",
            entries=(entry(actual=21971),),
            assessments=(assessment(),),
        )
        self.assertEqual(batch.observations, ())


if __name__ == "__main__":
    unittest.main()
