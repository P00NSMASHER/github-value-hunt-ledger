from __future__ import annotations

import unittest

from recoveryworks.commercial_operational_invariants import (
    CommercialOperationalInvariantState,
    verify_commercial_operational_invariants,
)
from recoveryworks.container_build import build_container_build_manifest
from recoveryworks.production_adversarial_certification import (
    AdversarialCertificationState,
    AdversarialVector,
    current_repository_revision,
    run_commercial_adversarial_certification,
)
from recoveryworks.recurring_assurance_lifecycle import (
    build_recurring_assurance_service_activation,
    build_recurring_assurance_service_deactivation,
    build_recurring_assurance_service_lifecycle,
)
from recoveryworks.test_commercial_operational_invariants import full_chain


SOURCE_REVISION = current_repository_revision()
OTHER_SOURCE_REVISION = "6" * 40


def build_manifest(source_revision: str = SOURCE_REVISION):
    return build_container_build_manifest(
        source_commit=source_revision,
        dockerfile_path="recoveryworks/deploy/Dockerfile.production",
        dependency_lock_path="recoveryworks/requirements.production.lock",
    )


class ProductionAdversarialCertificationTests(unittest.TestCase):
    def test_seeded_property_matrix_covers_all_attack_vectors(self):
        result = run_commercial_adversarial_certification(
            full_chain,
            build_manifest=build_manifest(),
            seed=41001,
            iterations_per_vector=6,
        )
        self.assertIs(result.state, AdversarialCertificationState.PASS)
        self.assertEqual(result.total_cases, len(AdversarialVector) * 6)
        self.assertEqual(result.false_negative_count, 0)
        self.assertEqual(
            set(result.vector_counts),
            {vector.value for vector in AdversarialVector},
        )
        self.assertTrue(all(count == 6 for count in result.vector_counts.values()))
        self.assertFalse(result.external_actions_performed)
        self.assertFalse(result.automatic_repair_performed)

    def test_same_seed_produces_same_certification_proof(self):
        first = run_commercial_adversarial_certification(
            full_chain,
            build_manifest=build_manifest(),
            seed=9917,
            iterations_per_vector=2,
        )
        second = run_commercial_adversarial_certification(
            full_chain,
            build_manifest=build_manifest(),
            seed=9917,
            iterations_per_vector=2,
        )
        self.assertEqual(first.proof_hash, second.proof_hash)
        self.assertEqual(
            [case.mutation for case in first.cases],
            [case.mutation for case in second.cases],
        )

    def test_source_revision_is_current_head_and_proof_bound(self):
        result = run_commercial_adversarial_certification(
            full_chain,
            build_manifest=build_manifest(),
            seed=9917,
            iterations_per_vector=1,
        )
        self.assertEqual(result.source_revision, current_repository_revision())
        self.assertEqual(result.source_revision, SOURCE_REVISION)

    def test_unverified_build_manifest_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "build_manifest"):
            run_commercial_adversarial_certification(
                full_chain,
                build_manifest="not-a-build-manifest",
                seed=1,
                iterations_per_vector=1,
            )

    def test_noncurrent_source_revision_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError, "does not match current repository revision"
        ):
            run_commercial_adversarial_certification(
                full_chain,
                build_manifest=build_manifest(OTHER_SOURCE_REVISION),
                seed=1,
                iterations_per_vector=1,
            )

    def test_stale_build_manifest_inputs_are_rejected(self):
        manifest = build_manifest()
        object.__setattr__(
            manifest,
            "dockerfile_sha256",
            "f" * 64,
        )
        with self.assertRaisesRegex(
            ValueError, "does not match current production build inputs"
        ):
            run_commercial_adversarial_certification(
                full_chain,
                build_manifest=manifest,
                seed=1,
                iterations_per_vector=1,
            )

    def test_noncanonical_build_manifest_path_is_rejected(self):
        manifest = build_manifest()
        object.__setattr__(
            manifest,
            "dockerfile_path",
            "recoveryworks/deploy/alternate.Dockerfile",
        )
        with self.assertRaisesRegex(
            ValueError, "does not match current production build inputs"
        ):
            run_commercial_adversarial_certification(
                full_chain,
                build_manifest=manifest,
                seed=1,
                iterations_per_vector=1,
            )

    def test_broken_baseline_is_not_certified(self):
        def broken_factory():
            chain = full_chain()
            object.__setattr__(
                chain["issued_invoice"],
                "buyer_id",
                "wrong-baseline-buyer",
            )
            return chain

        with self.assertRaisesRegex(ValueError, "baseline chain must pass"):
            run_commercial_adversarial_certification(
                broken_factory,
                build_manifest=build_manifest(),
                seed=5,
                iterations_per_vector=1,
            )

    def test_exact_deactivated_lifecycle_is_verified_end_to_end(self):
        chain = full_chain()
        deactivation = build_recurring_assurance_service_deactivation(
            chain["recurring_activation"],
            deactivated_at="2026-11-15T12:00:00Z",
            operator_id="operator-stop-valid",
            deactivation_reference="stop-valid",
            reason="buyer requested service stop",
            internal_operator_authorized=True,
        )
        chain["recurring_deactivation"] = deactivation
        chain["recurring_lifecycle"] = build_recurring_assurance_service_lifecycle(
            chain["recurring_readiness"],
            chain["recurring_activation"],
            deactivation,
        )
        chain["checked_at"] = "2026-11-15T12:01:00Z"

        report = verify_commercial_operational_invariants(**chain)
        self.assertIs(report.state, CommercialOperationalInvariantState.PASS)
        self.assertEqual(report.failed_codes, ())
        self.assertIn(
            ("recurring_deactivation", deactivation.proof_hash),
            report.artifact_proof_hashes,
        )
        self.assertFalse(report.external_actions_performed)
        self.assertFalse(report.automatic_repair_performed)

    def test_replayed_deactivation_receipt_is_blocked(self):
        chain = full_chain()
        activation_a = chain["recurring_activation"]
        deactivation_a = build_recurring_assurance_service_deactivation(
            activation_a,
            deactivated_at="2026-11-15T12:00:00Z",
            operator_id="operator-stop-a",
            deactivation_reference="stop-a",
            reason="certification replay fixture",
            internal_operator_authorized=True,
        )
        lifecycle_a = build_recurring_assurance_service_lifecycle(
            chain["recurring_readiness"], activation_a, deactivation_a
        )
        activation_b = build_recurring_assurance_service_activation(
            chain["recurring_readiness"],
            activated_at=activation_a.activated_at,
            operator_id="operator-replay-b",
            activation_reference="activation-b",
            internal_operator_authorized=True,
        )
        chain["recurring_activation"] = activation_b
        chain["recurring_deactivation"] = deactivation_a
        chain["recurring_lifecycle"] = lifecycle_a
        chain["checked_at"] = "2026-11-15T12:01:00Z"

        report = verify_commercial_operational_invariants(**chain)
        self.assertIs(report.state, CommercialOperationalInvariantState.BLOCKED)
        self.assertIn(
            "RECURRING_LIFECYCLE_STATE_INTEGRITY", report.failed_codes
        )
        self.assertFalse(report.external_actions_performed)
        self.assertFalse(report.automatic_repair_performed)


if __name__ == "__main__":
    unittest.main()
