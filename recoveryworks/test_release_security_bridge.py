from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
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
from recoveryworks.release_security_bridge import (
    ExternalProvenanceVerificationReceipt,
    ExternalSignatureVerificationReceipt,
    verify_external_release_security_evidence,
    write_cyclonedx_sbom,
)


def release(build, digest):
    image="registry.example/recoveryworks@sha256:"+digest
    ident={"schema":1,"version":"1.0.0","source_commit":build.source_commit,
           "container_build_manifest_proof_hash":build.proof_hash,
           "container_image_ref":image,"container_image_digest":digest,
           "production_deployment_proof_hash":"d"*64,
           "created_at":"2026-09-24T13:00:00Z","immutable":True,
           "published":False,"deployed":False}
    return RecoveryWorksReleaseManifest(
        release_id="recoveryworks-release:"+canonical_hash(ident),
        version="1.0.0",source_commit=build.source_commit,
        container_build_manifest_proof_hash=build.proof_hash,
        container_image_ref=image,container_image_digest=digest,
        production_deployment_proof_hash="d"*64,
        created_at="2026-09-24T13:00:00Z")


class ReleaseSecurityBridgeTests(unittest.TestCase):
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
        scan=build_vulnerability_scan_receipt(
            container_image_digest=rel.container_image_digest,
            scanner_id="scanner",scanner_version="1",
            vulnerability_database_id="db",vulnerability_database_digest="e"*64,
            scanned_at="2026-09-24T13:03:00Z",
            severity_counts={"critical":0,"high":0},
            source_hash="f"*64,source_locator="scanner://receipt",verified=True)
        gate=build_release_security_gate(
            rel,sbom,att,scan,policy=ReleaseSecurityPolicy(),
            created_at="2026-09-24T13:04:00Z")
        return build,rel,sbom,scan,gate

    def test_cyclonedx_export_and_external_receipts_bind_exact_release(self):
        with tempfile.TemporaryDirectory() as d:
            build,rel,sbom,scan,gate=self.fixture()
            path=Path(d)/"sbom.cdx.json"
            std=write_cyclonedx_sbom(rel,sbom,path=path)
            payload=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["bomFormat"],"CycloneDX")
            self.assertEqual(payload["specVersion"],"1.5")
            sig_ident={"schema":1,"release_id":rel.release_id,
                       "release_proof_hash":rel.proof_hash,
                       "container_image_digest":rel.container_image_digest,
                       "signer_identity":"key://release-signer",
                       "signature_algorithm":"ECDSA_P256_SHA256",
                       "signature_artifact_hash":"1"*64,
                       "verified_at":"2026-09-24T13:05:00Z",
                       "verifier_id":"signature-verifier",
                       "source_hash":"2"*64,"source_locator":"verifier://sig",
                       "verified":True}
            sig=ExternalSignatureVerificationReceipt(
                receipt_id="recoveryworks-signature-verification:"+canonical_hash(sig_ident),
                **{k:v for k,v in sig_ident.items() if k!="schema"})
            prov_ident={"schema":1,"release_id":rel.release_id,
                        "release_proof_hash":rel.proof_hash,
                        "container_image_digest":rel.container_image_digest,
                        "source_commit":rel.source_commit,
                        "container_build_manifest_proof_hash":
                            rel.container_build_manifest_proof_hash,
                        "sbom_proof_hash":sbom.proof_hash,
                        "predicate_type":"https://slsa.dev/provenance/v1",
                        "attestation_artifact_hash":"3"*64,
                        "verified_at":"2026-09-24T13:06:00Z",
                        "verifier_id":"provenance-verifier",
                        "source_hash":"4"*64,
                        "source_locator":"verifier://provenance","verified":True}
            prov=ExternalProvenanceVerificationReceipt(
                receipt_id="recoveryworks-provenance-verification:"
                +canonical_hash(prov_ident),
                **{k:v for k,v in prov_ident.items() if k!="schema"})
            verified=verify_external_release_security_evidence(
                rel,gate,std,scan,sig,prov)
            self.assertEqual(
                verified.as_dict()["state"],"EXTERNAL_SECURITY_EVIDENCE_VERIFIED")

    def test_wrong_image_signature_or_provenance_commit_fails_closed(self):
        build,rel,sbom,scan,gate=self.fixture()
        with tempfile.TemporaryDirectory() as d:
            std=write_cyclonedx_sbom(rel,sbom,path=Path(d)/"sbom.json")
            sig_ident={"schema":1,"release_id":rel.release_id,
                       "release_proof_hash":rel.proof_hash,
                       "container_image_digest":"9"*64,
                       "signer_identity":"key://release-signer",
                       "signature_algorithm":"ECDSA_P256_SHA256",
                       "signature_artifact_hash":"1"*64,
                       "verified_at":"2026-09-24T13:05:00Z",
                       "verifier_id":"signature-verifier",
                       "source_hash":"2"*64,"source_locator":"verifier://sig",
                       "verified":True}
            sig=ExternalSignatureVerificationReceipt(
                receipt_id="recoveryworks-signature-verification:"+canonical_hash(sig_ident),
                **{k:v for k,v in sig_ident.items() if k!="schema"})
            prov_ident={"schema":1,"release_id":rel.release_id,
                        "release_proof_hash":rel.proof_hash,
                        "container_image_digest":rel.container_image_digest,
                        "source_commit":"b"*40,
                        "container_build_manifest_proof_hash":
                            rel.container_build_manifest_proof_hash,
                        "sbom_proof_hash":sbom.proof_hash,
                        "predicate_type":"https://slsa.dev/provenance/v1",
                        "attestation_artifact_hash":"3"*64,
                        "verified_at":"2026-09-24T13:06:00Z",
                        "verifier_id":"provenance-verifier",
                        "source_hash":"4"*64,
                        "source_locator":"verifier://provenance","verified":True}
            prov=ExternalProvenanceVerificationReceipt(
                receipt_id="recoveryworks-provenance-verification:"
                +canonical_hash(prov_ident),
                **{k:v for k,v in prov_ident.items() if k!="schema"})
            with self.assertRaisesRegex(ValueError,"signature receipt image mismatch"):
                verify_external_release_security_evidence(
                    rel,gate,std,scan,sig,prov)


if __name__=="__main__":
    unittest.main()
