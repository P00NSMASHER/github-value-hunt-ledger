from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from recoveryworks.container_build import build_container_build_manifest
from recoveryworks.final_production_certification import (
    build_final_production_certification_dossier,
    write_final_production_certification_dossier,
)
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.production_adversarial_certification import current_repository_revision
from recoveryworks.production_chain_certification import (
    run_production_chain_adversarial_certification,
    verify_production_chain,
)
from recoveryworks.test_production_chain_certification import full_production_chain
from recoveryworks.test_release_control import production_certification


class FinalProductionCertificationTests(unittest.TestCase):
    def test_step50_final_dossier_binds_complete_hardening_chain(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            def factory():
                return full_production_chain(root)

            chain = factory()
            build = build_container_build_manifest(
                source_commit=current_repository_revision(),
                dockerfile_path="recoveryworks/deploy/Dockerfile.production",
                dependency_lock_path="recoveryworks/requirements.production.lock",
            )
            commercial = production_certification(build)
            chain_report = verify_production_chain(**chain)
            hostile = run_production_chain_adversarial_certification(
                factory,
                source_revision=current_repository_revision(),
                seed=50001,
                iterations_per_vector=2,
            )
            dossier = build_final_production_certification_dossier(
                build_manifest=build,
                commercial_certification=commercial,
                release=chain["release"],
                package_integrity=chain["package_integrity"],
                promotion_gate=chain["promotion_gate"],
                admission=chain["admission"],
                handoff=chain["handoff"],
                post_deployment=chain["post_deployment"],
                chain_report=chain_report,
                chain_adversarial_certification=hostile,
                certified_at="2026-09-25T09:20:00Z",
            )
            self.assertEqual(
                dossier.as_dict()["state"],
                "PRODUCTION_HARDENING_CERTIFIED",
            )
            self.assertEqual(
                dossier.source_revision,
                current_repository_revision(),
            )
            self.assertEqual(
                dossier.production_chain_adversarial_certification_proof_hash,
                hostile.proof_hash,
            )
            self.assertFalse(dossier.deployment_performed_by_recoveryworks)
            self.assertFalse(dossier.external_actions_performed)
            self.assertFalse(dossier.automatic_repair_performed)
            path = root / "private" / "final-production-certification.json"
            write_final_production_certification_dossier(dossier, path)
            self.assertTrue(private_permissions_verified(path))
            self.assertIn(dossier.proof_hash, path.read_text(encoding="utf-8"))

    def test_step50_rejects_tampered_hostile_certification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)

            def factory():
                return full_production_chain(root)

            chain = factory()
            build = build_container_build_manifest(
                source_commit=current_repository_revision(),
                dockerfile_path="recoveryworks/deploy/Dockerfile.production",
                dependency_lock_path="recoveryworks/requirements.production.lock",
            )
            commercial = production_certification(build)
            chain_report = verify_production_chain(**chain)
            hostile = run_production_chain_adversarial_certification(
                factory,
                source_revision=current_repository_revision(),
                seed=50002,
                iterations_per_vector=1,
            )
            object.__setattr__(
                hostile,
                "source_revision",
                "f" * 40,
            )
            with self.assertRaisesRegex(
                ValueError, "source revision|did not pass"
            ):
                build_final_production_certification_dossier(
                    build_manifest=build,
                    commercial_certification=commercial,
                    release=chain["release"],
                    package_integrity=chain["package_integrity"],
                    promotion_gate=chain["promotion_gate"],
                    admission=chain["admission"],
                    handoff=chain["handoff"],
                    post_deployment=chain["post_deployment"],
                    chain_report=chain_report,
                    chain_adversarial_certification=hostile,
                    certified_at="2026-09-25T09:20:00Z",
                )


if __name__ == "__main__":
    unittest.main()
