from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from recoveryworks.container_build import build_container_build_manifest
from recoveryworks.models import canonical_hash
from recoveryworks.release_control import RecoveryWorksReleaseManifest
from recoveryworks.release_security import (
    ReleaseSecurityPolicy,
    build_container_attestation_input,
    build_release_sbom,
    build_release_security_gate,
    build_vulnerability_scan_receipt,
)


def release(build, image_digest: str):
    image = "registry.example/recoveryworks@sha256:" + image_digest
    identity = {
        "schema":1,"version":"1.0.0","source_commit":build.source_commit,
        "container_build_manifest_proof_hash":build.proof_hash,
        "container_image_ref":image,"container_image_digest":image_digest,
        "production_deployment_proof_hash":"d"*64,
        "created_at":"2026-09-24T13:00:00Z",
        "immutable":True,"published":False,"deployed":False,
    }
    return RecoveryWorksReleaseManifest(
        release_id="recoveryworks-release:"+canonical_hash(identity),
        version="1.0.0",source_commit=build.source_commit,
        container_build_manifest_proof_hash=build.proof_hash,
        container_image_ref=image,container_image_digest=image_digest,
        production_deployment_proof_hash="d"*64,
        created_at="2026-09-24T13:00:00Z",immutable=True,published=False,deployed=False)


class ReleaseSecurityTests(unittest.TestCase):
    def fixture(self):
        build=build_container_build_manifest(
            source_commit="a"*40,
            dockerfile_path="recoveryworks/deploy/Dockerfile.production",
            dependency_lock_path="recoveryworks/requirements.production.lock")
        rel=release(build,"c"*64)
        sbom=build_release_sbom(
            rel,build,repository_root=".",generated_at="2026-09-24T13:01:00Z")
        att=build_container_attestation_input(
            rel,build,sbom,generated_at="2026-09-24T13:02:00Z")
        return build,rel,sbom,att

    def scan(self, digest: str, *, critical=0, high=0, verified=True):
        return build_vulnerability_scan_receipt(
            container_image_digest=digest,
            scanner_id="scanner-test",scanner_version="1.0",
            vulnerability_database_id="db-2026-09-24",
            vulnerability_database_digest="e"*64,
            scanned_at="2026-09-24T13:03:00Z",
            severity_counts={"critical":critical,"high":high,"medium":2,"low":3},
            source_hash="f"*64,source_locator="scanner://receipt-1",
            verified=verified)

    def test_sbom_attestation_and_verified_scan_open_security_gate(self):
        build,rel,sbom,att=self.fixture()
        self.assertEqual(
            {c.name for c in sbom.components if c.component_type=="source-root"},
            {"recoveryworks","freight"})
        self.assertFalse(att.signing_performed)
        self.assertFalse(att.published)
        gate=build_release_security_gate(
            rel,sbom,att,self.scan(rel.container_image_digest),
            policy=ReleaseSecurityPolicy(max_critical=0,max_high=0),
            created_at="2026-09-24T13:04:00Z")
        self.assertEqual(gate.as_dict()["state"],"SECURITY_GATE_READY")
        self.assertFalse(gate.signing_performed)
        self.assertFalse(gate.attestation_published)
        self.assertFalse(gate.image_published)

    def test_critical_or_unverified_scan_fails_closed(self):
        _,rel,sbom,att=self.fixture()
        with self.assertRaisesRegex(ValueError,"critical vulnerability"):
            build_release_security_gate(
                rel,sbom,att,self.scan(rel.container_image_digest,critical=1),
                created_at="2026-09-24T13:04:00Z")
        with self.assertRaisesRegex(ValueError,"must be verified"):
            build_release_security_gate(
                rel,sbom,att,self.scan(rel.container_image_digest,verified=False),
                created_at="2026-09-24T13:04:00Z")

    def test_scan_for_wrong_image_cannot_open_gate(self):
        _,rel,sbom,att=self.fixture()
        with self.assertRaisesRegex(ValueError,"image digest mismatch"):
            build_release_security_gate(
                rel,sbom,att,self.scan("9"*64),
                created_at="2026-09-24T13:04:00Z")


if __name__=="__main__":
    unittest.main()
