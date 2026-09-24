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
from recoveryworks.production_adversarial_certification import (
    current_repository_revision,
    run_commercial_adversarial_certification,
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
from recoveryworks.test_commercial_operational_invariants import full_chain


def production_certification(build):
    return run_commercial_adversarial_certification(
        full_chain,
        build_manifest=build,
        seed=42001,
        iterations_per_vector=2,
    )


def production_spec(root: Path, image_ref: str) -> dict:
    config = root / "config"
    inputs = root / "inputs"
    state = root / "private" / "state"
    reports = root / "private" / "reports"
    for path in (config, inputs, state, reports):
        path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        state.chmod(0o700)
        reports.chmod(0o700)
    (inputs / "focus.csv").write_text(
        "ProviderName,BillingAccountId,ServiceName,ChargePeriodStart,"
        "BilledCost,BillingCurrency,ResourceId\n"
        "Amazon Web Services,acct-1,EC2,2026-08-31T00:00:00Z,"
        "40.00,USD,i-1\n",
        encoding="utf-8",
    )
    (inputs / "meter.csv").write_text(
        "Meter_Record_ID,Usage_Units,ResourceId,ServiceName,UsageDate\n"
        "M-1,10,i-1,EC2,2026-08-31\n",
        encoding="utf-8",
    )
    (inputs / "rates.csv").write_text(
        "Counterparty,Service_ID,Effective_From,Effective_To,Fixed_Fee,"
        "Included_Units,Unit_Rate\n"
        "Amazon Web Services,EC2,2026-01-01,,10.00,0,2.00\n",
        encoding="utf-8",
    )
    pilot = {
        "schema": 1,
        "deployment_id": "release-pilot",
        "client_id": "client-release",
        "currency": "USD",
        "provider": "aws",
        "security": {
            "cloud_access_mode": "READ_ONLY",
            "recoveryos_provider_write_credentials": False,
            "remediation_execution_enabled": False,
            "external_actions_enabled": False,
            "private_state_required": True,
        },
        "period": {
            "start": "2026-08-01",
            "end": "2026-08-31",
            "exported_at": "2026-09-01T12:00:00Z",
        },
        "cletrics": {
            "focus_csv": str(inputs / "focus.csv"),
            "meter_csv": str(inputs / "meter.csv"),
            "release": "release-test",
            "commit": "a" * 40,
        },
        "recoveryos": {
            "rates_csv": str(inputs / "rates.csv"),
            "bundle_path": str(state / "bundle.zip"),
            "ledger_path": str(state / "ledger.json"),
            "receipt_registry_path": str(state / "receipts.json"),
            "report_path": str(reports / "assurance.json"),
        },
    }
    import json
    (config / "pilot.json").write_text(json.dumps(pilot), encoding="utf-8")
    return {
        "schema": 1,
        "pilot_spec": str(config / "pilot.json"),
        "service": {
            "image_ref": image_ref,
            "user": "65532:65532",
            "command": [
                "python","-m","recoveryworks.pilot_runner",
                "--spec","/config/pilot.json",
                "--base-dir","/workspace",
            ],
            "read_only_root_filesystem": True,
            "privileged": False,
            "host_network": False,
            "network_disabled": True,
            "no_new_privileges": True,
            "cap_drop_all": True,
            "provider_write_credentials": False,
            "remediation_execution_enabled": False,
            "external_actions_enabled": False,
        },
        "volumes": {
            "config": {
                "host_path": str(config),
                "container_path": "/config",
                "read_only": True,
                "private_required": False,
            },
            "inputs": {
                "host_path": str(inputs),
                "container_path": "/inputs",
                "read_only": True,
                "private_required": False,
            },
            "state": {
                "host_path": str(state),
                "container_path": "/state",
                "read_only": False,
                "private_required": True,
            },
            "reports": {
                "host_path": str(reports),
                "container_path": "/reports",
                "read_only": False,
                "private_required": True,
            },
        },
    }


class ReleaseControlTests(unittest.TestCase):
    def deployment(self, root: Path, image_ref: str):
        return build_production_deployment_contract(
            production_spec(root, image_ref), base_dir=root
        )

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
            build = self.build_manifest(current_repository_revision())
            certification = production_certification(build)
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
                adversarial_certification=certification,
            )
            self.assertTrue(gate.promotion_ready)
            self.assertFalse(gate.promotion_execution_enabled)
            self.assertFalse(gate.deployment_performed)
            self.assertEqual(
                gate.adversarial_certification_proof_hash,
                certification.proof_hash,
            )
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

    def test_production_gate_fails_without_adversarial_certification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            image = "registry.example/recoveryworks@sha256:" + "7" * 64
            deployment = self.deployment(root, image)
            build = self.build_manifest(current_repository_revision())
            release = build_release_manifest(
                version="1.0.0",
                build_manifest=build,
                deployment=deployment,
                container_image_ref=image,
                created_at="2026-09-24T13:00:00Z",
            )
            previous_image = (
                "registry.example/recoveryworks@sha256:" + "8" * 64
            )
            previous = build_release_manifest(
                version="0.9.0",
                build_manifest=self.build_manifest("b" * 40),
                deployment=self.deployment(root / "previous", previous_image),
                container_image_ref=previous_image,
                created_at="2026-09-23T13:00:00Z",
            )
            rollback = build_rollback_manifest(
                release,
                previous,
                reason="Known-good rollback target.",
                created_at="2026-09-24T13:05:00Z",
            )
            approvals = (
                approve_release(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approver_id="release-manager",
                    role="RELEASE_MANAGER",
                    approved_at="2026-09-24T13:06:00Z",
                ),
                approve_release(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approver_id="operations-owner",
                    role="OPERATIONS_OWNER",
                    approved_at="2026-09-24T13:07:00Z",
                ),
            )
            with self.assertRaisesRegex(
                ValueError, "requires adversarial certification"
            ):
                build_environment_promotion_gate(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approvals=approvals,
                    health_check=check_production_health(deployment),
                    readiness_check=check_production_readiness(deployment),
                    rollback_manifest=rollback,
                    gate_created_at="2026-09-24T13:08:00Z",
                )

    def test_production_gate_rejects_certification_from_other_build(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            image = "registry.example/recoveryworks@sha256:" + "9" * 64
            deployment = self.deployment(root, image)
            current_build = self.build_manifest(current_repository_revision())
            release = build_release_manifest(
                version="1.0.0",
                build_manifest=current_build,
                deployment=deployment,
                container_image_ref=image,
                created_at="2026-09-24T13:00:00Z",
            )
            certification = run_commercial_adversarial_certification(
                full_chain,
                build_manifest=current_build,
                seed=42002,
                iterations_per_vector=1,
            )
            object.__setattr__(
                certification,
                "container_build_manifest_proof_hash",
                "f" * 64,
            )
            previous_image = (
                "registry.example/recoveryworks@sha256:" + "a" * 64
            )
            previous = build_release_manifest(
                version="0.9.0",
                build_manifest=self.build_manifest("b" * 40),
                deployment=self.deployment(root / "previous", previous_image),
                container_image_ref=previous_image,
                created_at="2026-09-23T13:00:00Z",
            )
            rollback = build_rollback_manifest(
                release,
                previous,
                reason="Known-good rollback target.",
                created_at="2026-09-24T13:05:00Z",
            )
            approvals = (
                approve_release(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approver_id="release-manager",
                    role="RELEASE_MANAGER",
                    approved_at="2026-09-24T13:06:00Z",
                ),
                approve_release(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approver_id="operations-owner",
                    role="OPERATIONS_OWNER",
                    approved_at="2026-09-24T13:07:00Z",
                ),
            )
            with self.assertRaisesRegex(
                ValueError, "build manifest does not bind release"
            ):
                build_environment_promotion_gate(
                    release,
                    environment=ReleaseEnvironment.PRODUCTION,
                    approvals=approvals,
                    health_check=check_production_health(deployment),
                    readiness_check=check_production_readiness(deployment),
                    rollback_manifest=rollback,
                    gate_created_at="2026-09-24T13:08:00Z",
                    adversarial_certification=certification,
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
