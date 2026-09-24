from __future__ import annotations

from types import SimpleNamespace
import tempfile
from pathlib import Path
import unittest

from recoveryworks.enterprise_controls import build_enterprise_control_evidence_map
from recoveryworks.models import canonical_hash
from recoveryworks.release_control import RecoveryWorksReleaseManifest


def release():
    ident={
        "schema":1,"version":"1.0.0","source_commit":"a"*40,
        "container_build_manifest_proof_hash":"1"*64,
        "container_image_ref":"registry/x@sha256:"+"2"*64,
        "container_image_digest":"2"*64,
        "production_deployment_proof_hash":"3"*64,
        "created_at":"2026-09-24T10:00:00Z",
        "immutable":True,"published":False,"deployed":False}
    return RecoveryWorksReleaseManifest(
        release_id="recoveryworks-release:"+canonical_hash(ident),
        version="1.0.0",source_commit="a"*40,
        container_build_manifest_proof_hash="1"*64,
        container_image_ref=ident["container_image_ref"],
        container_image_digest="2"*64,
        production_deployment_proof_hash="3"*64,
        created_at=ident["created_at"])


class EnterpriseControlsTests(unittest.TestCase):
    def test_control_map_is_diligence_ready_without_certification_claims(self):
        rel=release()
        admission=SimpleNamespace(
            release_id=rel.release_id,release_proof_hash=rel.proof_hash,
            proof_hash="4"*64)
        security=SimpleNamespace(
            release_id=rel.release_id,proof_hash="5"*64)
        dr=SimpleNamespace(proof_hash="6"*64)
        backup=SimpleNamespace(proof_hash="7"*64)
        assurance=SimpleNamespace(
            release_id=rel.release_id,proof_hash="8"*64)
        commercial=SimpleNamespace(
            proof_hash="9"*64)
        dossier=SimpleNamespace(
            release_id=rel.release_id,
            commercial_pilot_package_proof_hash=commercial.proof_hash,
            production_admission_proof_hash=admission.proof_hash,
            security_evidence_proof_hash=security.proof_hash,
            dr_rehearsal_proof_hash=dr.proof_hash,
            proof_hash="a"*64)
        credential=SimpleNamespace(proof_hash="b"*64)
        control_map=build_enterprise_control_evidence_map(
            release=rel,admission=admission,security_evidence=security,
            dr_rehearsal=dr,backup=backup,continuous_assurance=assurance,
            launch_dossier=dossier,credential_scope=credential,
            commercial_pilot=commercial,incident_journal_head_hash=None,
            generated_at="2026-09-24T13:00:00Z")
        payload=control_map.as_dict()
        self.assertEqual(payload["state"],"BUYER_DILIGENCE_CONTROL_MAP_READY")
        self.assertEqual(payload["certification_claims"],[])
        self.assertTrue(payload["framework_mappings_are_reference_only"])
        self.assertFalse(payload["third_party_audit_completed"])
        ids={row["control_id"] for row in payload["controls"]}
        self.assertTrue({"AC-01","DP-01","SDLC-01","SC-01","BCP-01",
                         "IR-01","AU-01","FIN-01","EXT-01"}.issubset(ids))
        self.assertIn("No SOC 2",payload["disclaimer"])

    def test_certification_claims_fail_closed(self):
        from recoveryworks.enterprise_controls import EnterpriseControlEvidenceMap
        with self.assertRaisesRegex(ValueError,"cannot claim certifications"):
            EnterpriseControlEvidenceMap(
                map_id="bad",release_id="release",
                release_proof_hash="1"*64,
                generated_at="2026-09-24T13:00:00Z",
                controls=(),certification_claims=("SOC 2",),
                framework_mappings_are_reference_only=True,
                third_party_audit_completed=False,buyer_diligence_ready=True)


if __name__=="__main__":
    unittest.main()
