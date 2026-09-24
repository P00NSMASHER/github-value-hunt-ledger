from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from recoveryworks.container_build import build_container_build_manifest
from recoveryworks.production_deployment import (
    build_production_deployment_contract,
    check_production_health,
    check_production_readiness,
)
from recoveryworks.release_control import (
    ReleaseEnvironment,
    approve_release,
    build_environment_promotion_gate,
    build_release_manifest,
    build_rollback_manifest,
    write_release_control_artifacts,
)
from recoveryworks.private_io import private_permissions_verified
from recoveryworks.test_production_deployment import (
    ProductionDeploymentPackagingTests,
)


class ReleaseControlTests(unittest.TestCase):
    def deployment(self, root: Path, image_ref: str):
        helper = ProductionDeploymentPackagingTests()
        spec = helper.setup(root)
        spec["service"]["image_ref"] = image_ref
        return build_production_deployment_contract(spec, base_dir=root)

    def build_manifest(self, commit: str):
        return build_container_build_manifest(
            source_commit=commit,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock",
        )

    def test_production_gate_requires_two_distinct_approvals_and_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            image = "registry.example/recoveryworks@sha256:" + "c" * 64
            deployment = self.deployment(root, image)
            build = self.build_manifest("a" * 40)
            current = build_release_manifest(
                version="1.0.0",
                build_manifest=build,
                deployment=deployment,
                container_image_ref=image,
                created_at="2026-09-24T13:00:00Z",
            )

            previous_image = (
                "registry.example/recoveryworks@sha256:" + "d" * 64
            )
            previous_deployment = self.deployment(
                root / "previous",
                previous_image,
            )
            previous = build_release_manifest(
                version="0.9.0",
                build_manifest=self.build_manifest("b" * 40),
                deployment=previous_deployment,
                container_image_ref=previous_image,
                created_at="2026-09-23T13:00:00Z",
            )
            rollback = build_rollback_manifest(
                current,
                previous,
                reason="Return to last verified production release.",
                created_at="2026-09-24T13:05:00Z",
            )
            approvals = (
                approve_release(
                    current,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approver_id="release-manager",
                    role="RELEASE_MANAGER",
                    approved_at="2026-09-24T13:06:00Z",
                ),
                approve_release(
                    current,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approver_id="operations-owner",
                    role="OPERATIONS_OWNER",
                    approved_at="2026-09-24T13:07:00Z",
                ),
            )
            gate = build_environment_promotion_gate(
                current,
                environment=ReleaseEnvironment.PRODUCTION,
                approvals=approvals,
                health_check=check_production_health(deployment),
                readiness_check=check_production_readiness(deployment),
                rollback_manifest=rollback,
                gate_created_at="2026-09-24T13:08:00Z",
            )
            self.assertTrue(gate.promotion_ready)
            self.assertFalse(gate.promotion_execution_enabled)
            self.assertFalse(gate.deployment_performed)
            self.assertEqual(
                gate.as_dict()["state"],
                "READY_FOR_SEPARATE_PROMOTION_ACTION",
            )
            paths = write_release_control_artifacts(
                release=current,
                approvals=approvals,
                rollback=rollback,
                gate=gate,
                directory=root / "private" / "release",
            )
            self.assertTrue(all(private_permissions_verified(path) for path in paths))

    def test_production_gate_fails_without_second_approver_or_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            image = "registry.example/recoveryworks@sha256:" + "e" * 64
            deployment = self.deployment(root, image)
            release = build_release_manifest(
                version="1.0.0",
                build_manifest=self.build_manifest("a" * 40),
                deployment=deployment,
                container_image_ref=image,
                created_at="2026-09-24T13:00:00Z",
            )
            one = (
                approve_release(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approver_id="only-one",
                    role="RELEASE_MANAGER",
                    approved_at="2026-09-24T13:01:00Z",
                ),
            )
            with self.assertRaisesRegex(ValueError, "2 distinct"):
                build_environment_promotion_gate(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approvals=one,
                    health_check=check_production_health(deployment),
                    readiness_check=check_production_readiness(deployment),
                    rollback_manifest=None,
                    gate_created_at="2026-09-24T13:02:00Z",
                )

    def test_release_image_must_match_deployment_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            deployment = self.deployment(
                root,
                "registry.example/recoveryworks@sha256:" + "f" * 64,
            )
            with self.assertRaisesRegex(ValueError, "exactly match"):
                build_release_manifest(
                    version="1.0.0",
                    build_manifest=self.build_manifest("a" * 40),
                    deployment=deployment,
                    container_image_ref=(
                        "registry.example/recoveryworks@sha256:" + "1" * 64
                    ),
                    created_at="2026-09-24T13:00:00Z",
                )


if __name__ == "__main__":
    unittest.main()
