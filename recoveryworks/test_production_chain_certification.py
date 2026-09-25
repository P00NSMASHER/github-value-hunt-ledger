from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from recoveryworks.models import canonical_hash
from recoveryworks.production_admission import build_production_admission_gate
from recoveryworks.production_adversarial_certification import current_repository_revision
from recoveryworks.production_chain_certification import (
    ProductionChainAdversarialVector,
    ProductionChainState,
    run_production_chain_adversarial_certification,
    verify_production_chain,
)
from recoveryworks.release_deployment_handoff import (
    DeploymentEnvironmentSnapshot,
    ExternalDeploymentReceipt,
    prepare_release_deployment_handoff,
    validate_external_deployment,
)
from recoveryworks.test_production_admission import ProductionAdmissionTests


def H(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def full_production_chain(root: Path) -> dict:
    admission_fixture = ProductionAdmissionTests()
    release, promotion, security, dr, build = admission_fixture.fixture(root)
    admission = build_production_admission_gate(
        release,
        promotion,
        security,
        dr,
        build,
        admission_fixture.package_integrity,
        admitted_at="2026-09-24T13:11:00Z",
    )
    handoff = prepare_release_deployment_handoff(
        release,
        promotion,
        admission,
        deployer_id="external-deployer",
        issued_at="2026-09-24T13:12:00Z",
        expires_at="2026-09-24T13:30:00Z",
    )
    receipt_identity = {
        "schema": 1,
        "handoff_id": handoff.handoff_id,
        "handoff_proof_hash": handoff.proof_hash,
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "environment": "PRODUCTION",
        "deployer_id": "external-deployer",
        "deployed_at": "2026-09-24T13:20:00Z",
        "container_image_ref": release.container_image_ref,
        "container_image_digest": release.container_image_digest,
        "source_commit": release.source_commit,
        "production_deployment_proof_hash":
            release.production_deployment_proof_hash,
        "external_deployment_id": "deploy-chain-1",
        "source_hash": H("deploy-chain-receipt"),
        "source_locator": "deployer://deploy-chain-1",
        "verified": True,
    }
    receipt = ExternalDeploymentReceipt(
        receipt_id="recoveryworks-deployment-receipt:"
        + canonical_hash(receipt_identity),
        **{k: v for k, v in receipt_identity.items() if k != "schema"},
    )
    snapshot_identity = {
        "schema": 1,
        "environment": "PRODUCTION",
        "observed_at": "2026-09-24T13:22:00Z",
        "release_id": release.release_id,
        "release_proof_hash": release.proof_hash,
        "container_image_ref": release.container_image_ref,
        "container_image_digest": release.container_image_digest,
        "source_commit": release.source_commit,
        "production_deployment_proof_hash":
            release.production_deployment_proof_hash,
        "health_receipt_hash": H("post-health"),
        "readiness_receipt_hash": H("post-readiness"),
        "health_passed": True,
        "readiness_passed": True,
        "source_hash": H("environment-chain"),
        "source_locator": "environment://prod-chain",
        "verified": True,
    }
    snapshot = DeploymentEnvironmentSnapshot(
        snapshot_id="recoveryworks-environment-snapshot:"
        + canonical_hash(snapshot_identity),
        **{k: v for k, v in snapshot_identity.items() if k != "schema"},
    )
    post = validate_external_deployment(
        handoff,
        admission,
        receipt,
        snapshot,
    )
    return {
        "release": release,
        "promotion_gate": promotion,
        "package_integrity": admission_fixture.package_integrity,
        "admission": admission,
        "handoff": handoff,
        "post_deployment": post,
        "checked_at": "2026-09-24T13:23:00Z",
    }


class ProductionChainCertificationTests(unittest.TestCase):
    def test_step48_post_deployment_identity_is_exact(self):
        with tempfile.TemporaryDirectory() as d:
            chain = full_production_chain(Path(d))
            report = verify_production_chain(**chain)
            self.assertIs(report.state, ProductionChainState.PASS)
            self.assertEqual(report.failed_codes, ())
            self.assertFalse(report.external_actions_performed)
            self.assertFalse(report.automatic_repair_performed)

    def test_step49_hostile_matrix_blocks_every_vector(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            def factory():
                return full_production_chain(root)

            result = run_production_chain_adversarial_certification(
                factory,
                source_revision=current_repository_revision(),
                seed=49001,
                iterations_per_vector=3,
            )
            self.assertEqual(result.false_negative_count, 0)
            self.assertEqual(
                len(result.cases),
                len(ProductionChainAdversarialVector) * 3,
            )
            self.assertEqual(
                {case.vector for case in result.cases},
                set(ProductionChainAdversarialVector),
            )
            self.assertTrue(all(case.passed for case in result.cases))
            self.assertFalse(result.external_actions_performed)
            self.assertFalse(result.automatic_repair_performed)


if __name__ == "__main__":
    unittest.main()
