from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.branches.cloud_remediation import (
    approve_cloud_remediation_plan,
    build_cloud_remediation_plan,
    prepare_cloud_remediation_envelopes,
)
from recoveryworks.branches.cloud_savings import build_cloud_savings_report
from recoveryworks.branches.cloud_savings_evidence import (
    CloudSavingsBaseline,
    CloudSavingsImplementationEvidence,
    CloudSavingsNormalizationReview,
    CloudSavingsPostObservation,
    SavingsEvidenceState,
    SavingsNormalizationMode,
    measure_realized_cloud_savings,
)
from recoveryworks.integrations.cletrics import load_cletrics_bundle
from recoveryworks.test_cletrics_final_cycle import make_bundle


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class RealizedCloudSavingsTests(unittest.TestCase):
    def artifacts(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        bundle = load_cletrics_bundle(make_bundle(root / "bundle.zip"))
        signal = next(
            item for item in bundle.signals if item.signal_id == "S-1"
        )
        plan = build_cloud_remediation_plan(bundle.signals)
        action = next(item for item in plan.actions if item.signal_id == signal.signal_id)
        approval = approve_cloud_remediation_plan(
            plan,
            reviewer_id="reviewer-1",
            customer_authorization_id="customer-auth-1",
            approved_action_ids=(action.action_id,),
        )
        envelope = prepare_cloud_remediation_envelopes(plan, approval)[0]
        return temp, signal, plan, action, approval, envelope

    def test_activity_normalized_verified_realized_savings(self):
        temp, signal, plan, action, approval, envelope = self.artifacts()
        with temp:
            baseline = CloudSavingsBaseline(
                signal_id=signal.signal_id,
                signal_proof_hash=signal.proof_hash,
                period_start="2026-07-01",
                period_end="2026-07-31",
                cost_cents=100_000,
                activity_units="1000",
                source_hash=H("baseline"),
                source_locator="cur://baseline",
                verified=True,
            )
            implementation = CloudSavingsImplementationEvidence(
                action_id=action.action_id,
                envelope_proof_hash=envelope.proof_hash,
                implemented_at="2026-08-15T12:00:00Z",
                source_hash=H("implementation"),
                source_locator="cloudtrail://change-1",
                verified=True,
            )
            post = CloudSavingsPostObservation(
                signal_id=signal.signal_id,
                period_start="2026-09-01",
                period_end="2026-10-01",
                cost_cents=80_000,
                activity_units="1200",
                source_hash=H("post"),
                source_locator="cur://post",
                verified=True,
            )
            normalization = CloudSavingsNormalizationReview(
                mode=SavingsNormalizationMode.ACTIVITY_RATIO,
                reviewer_id="finops-reviewer",
                scope_unchanged=False,
                source_hash=H("normalization"),
                source_locator="review://normalization-1",
                verified=True,
            )
            measurement = measure_realized_cloud_savings(
                signal=signal,
                action=action,
                plan=plan,
                approval=approval,
                envelope=envelope,
                baseline=baseline,
                implementation=implementation,
                post=post,
                normalization=normalization,
            )
            self.assertIs(measurement.state, SavingsEvidenceState.VERIFIED)
            self.assertEqual(measurement.normalized_baseline_cost_cents, 120_000)
            self.assertEqual(measurement.realized_savings_cents, 40_000)
            report = build_cloud_savings_report(
                (signal,), realized_measurements=(measurement,)
            )
            self.assertEqual(report.realized_savings_cents, 40_000)
            self.assertEqual(report.realized_measurement_count, 1)

    def test_unverified_post_observation_stays_review_and_not_realized(self):
        temp, signal, plan, action, approval, envelope = self.artifacts()
        with temp:
            baseline = CloudSavingsBaseline(
                signal_id=signal.signal_id,
                signal_proof_hash=signal.proof_hash,
                period_start="2026-07-01",
                period_end="2026-07-31",
                cost_cents=100_000,
                activity_units=None,
                source_hash=H("baseline2"),
                source_locator="cur://baseline2",
                verified=True,
            )
            implementation = CloudSavingsImplementationEvidence(
                action_id=action.action_id,
                envelope_proof_hash=envelope.proof_hash,
                implemented_at="2026-08-15T12:00:00Z",
                source_hash=H("implementation2"),
                source_locator="cloudtrail://change-2",
                verified=True,
            )
            post = CloudSavingsPostObservation(
                signal_id=signal.signal_id,
                period_start="2026-09-01",
                period_end="2026-10-01",
                cost_cents=70_000,
                activity_units=None,
                source_hash=H("post2"),
                source_locator="cur://post2",
                verified=False,
            )
            normalization = CloudSavingsNormalizationReview(
                mode=SavingsNormalizationMode.FIXED_SCOPE,
                reviewer_id="finops-reviewer",
                scope_unchanged=True,
                source_hash=H("normalization2"),
                source_locator="review://normalization-2",
                verified=True,
            )
            measurement = measure_realized_cloud_savings(
                signal=signal,
                action=action,
                plan=plan,
                approval=approval,
                envelope=envelope,
                baseline=baseline,
                implementation=implementation,
                post=post,
                normalization=normalization,
            )
            self.assertIs(measurement.state, SavingsEvidenceState.REVIEW)
            self.assertEqual(measurement.realized_savings_cents, 30_000)
            report = build_cloud_savings_report(
                (signal,), realized_measurements=(measurement,)
            )
            self.assertEqual(report.realized_savings_cents, 0)
            self.assertEqual(report.realized_measurement_count, 0)

    def test_post_period_before_implementation_fails_closed(self):
        temp, signal, plan, action, approval, envelope = self.artifacts()
        with temp:
            baseline = CloudSavingsBaseline(
                signal_id=signal.signal_id,
                signal_proof_hash=signal.proof_hash,
                period_start="2026-06-01",
                period_end="2026-06-30",
                cost_cents=100_000,
                activity_units=None,
                source_hash=H("baseline3"),
                source_locator="cur://baseline3",
                verified=True,
            )
            implementation = CloudSavingsImplementationEvidence(
                action_id=action.action_id,
                envelope_proof_hash=envelope.proof_hash,
                implemented_at="2026-08-15T12:00:00Z",
                source_hash=H("implementation3"),
                source_locator="cloudtrail://change-3",
                verified=True,
            )
            post = CloudSavingsPostObservation(
                signal_id=signal.signal_id,
                period_start="2026-08-01",
                period_end="2026-08-30",
                cost_cents=70_000,
                activity_units=None,
                source_hash=H("post3"),
                source_locator="cur://post3",
                verified=True,
            )
            normalization = CloudSavingsNormalizationReview(
                mode=SavingsNormalizationMode.FIXED_SCOPE,
                reviewer_id="reviewer",
                scope_unchanged=True,
                source_hash=H("norm3"),
                source_locator="review://norm3",
                verified=True,
            )
            with self.assertRaisesRegex(ValueError, "post observation must start after"):
                measure_realized_cloud_savings(
                    signal=signal,
                    action=action,
                    plan=plan,
                    approval=approval,
                    envelope=envelope,
                    baseline=baseline,
                    implementation=implementation,
                    post=post,
                    normalization=normalization,
                )


if __name__ == "__main__":
    unittest.main()
