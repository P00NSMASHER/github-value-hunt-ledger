from __future__ import annotations

from types import SimpleNamespace
import tempfile
from pathlib import Path
import unittest

from recoveryworks.enterprise_controls import (
    ControlEvidenceReference,
    EnterpriseControlEntry,
    EnterpriseControlEvidenceMap,
    EnterpriseControlStatus,
)
from recoveryworks.enterprise_diligence_package import (
    build_enterprise_diligence_package,
    write_enterprise_diligence_package,
)
from recoveryworks.models import canonical_hash
from recoveryworks.private_io import private_permissions_verified


def control_map():
    evidence=ControlEvidenceReference(
        evidence_type="test-evidence",
        proof_hash="1"*64,
        description="Customer-safe proof description.",
        limitation="Does not constitute third-party certification.",
    )
    controls=(
        EnterpriseControlEntry(
            control_id="AC-01",domain="Access Control",title="Read-only access",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="Read-only provider access is proof-bound.",
            evidence=(evidence,),framework_references=("SOC2 CC6 (reference)",),
            questionnaire_topics=("least privilege",)),
        EnterpriseControlEntry(
            control_id="DP-01",domain="Data Protection",title="Private state",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="Private state is hash-bound.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("backup",)),
        EnterpriseControlEntry(
            control_id="SDLC-01",domain="Secure SDLC",title="Release gate",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="Releases require admission.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("change management",)),
        EnterpriseControlEntry(
            control_id="SC-01",domain="Supply Chain",title="SBOM",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="SBOM/provenance controls exist.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("SBOM",)),
        EnterpriseControlEntry(
            control_id="BCP-01",domain="Business Continuity",title="DR",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="DR is rehearsed.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("RPO",)),
        EnterpriseControlEntry(
            control_id="IR-01",domain="Incident Response",title="Incident lifecycle",
            status=EnterpriseControlStatus.CONTROL_IMPLEMENTED_NO_EVENT,
            description="Incident lifecycle is implemented.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("incident response",)),
        EnterpriseControlEntry(
            control_id="AU-01",domain="Auditability",title="Audit trail",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="Hash-chained history exists.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("audit logs",)),
        EnterpriseControlEntry(
            control_id="FIN-01",domain="Financial Integrity",title="Deterministic math",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="Money calculations are deterministic.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("financial controls",)),
        EnterpriseControlEntry(
            control_id="EXT-01",domain="External Actions",title="Separated mutation",
            status=EnterpriseControlStatus.INTERNAL_EVIDENCE,
            description="External mutations are separate.",
            evidence=(evidence,),framework_references=(),
            questionnaire_topics=("separation of duties",)),
    )
    identity={
        "schema":1,"release_id":"release-1","release_proof_hash":"2"*64,
        "generated_at":"2026-09-24T13:00:00Z",
        "control_hashes":[c.proof_hash for c in sorted(controls,key=lambda x:x.control_id)],
        "certification_claims":[],"framework_mappings_are_reference_only":True,
        "third_party_audit_completed":False,"buyer_diligence_ready":True,
    }
    return EnterpriseControlEvidenceMap(
        map_id="recoveryworks-enterprise-control-map:"+canonical_hash(identity),
        release_id="release-1",release_proof_hash="2"*64,
        generated_at="2026-09-24T13:00:00Z",controls=controls,
        certification_claims=(),framework_mappings_are_reference_only=True,
        third_party_audit_completed=False,buyer_diligence_ready=True)


class EnterpriseDiligencePackageTests(unittest.TestCase):
    def test_questionnaire_evidence_room_gap_register_and_redaction(self):
        package=build_enterprise_diligence_package(
            control_map(),generated_at="2026-09-24T14:00:00Z",
            gap_owners={"IR-01":"security-owner"},
            gap_due_at={"IR-01":"2026-10-15T12:00:00Z"})
        payload=package.as_dict()
        self.assertEqual(payload["state"],"CUSTOMER_SAFE_DILIGENCE_PACKAGE_READY")
        self.assertEqual(payload["certifications_claimed"],[])
        self.assertTrue(any(a["question_id"]=="Q-CERT" for a in payload["questionnaire_answers"]))
        self.assertEqual(len(payload["gaps"]),1)
        self.assertEqual(payload["gaps"][0]["owner_id"],"[REDACTED_OWNER]")
        for item in payload["evidence_room_items"]:
            self.assertNotIn("source_locator", item)
            self.assertNotIn("internal_path", item)
        for answer in payload["questionnaire_answers"]:
            self.assertNotIn("source_locator", answer)
            self.assertNotIn("internal_path", answer)
        self.assertNotIn("/home/", str(payload))

    def test_outputs_private_and_certification_claims_impossible(self):
        with tempfile.TemporaryDirectory() as d:
            package=build_enterprise_diligence_package(
                control_map(),generated_at="2026-09-24T14:00:00Z")
            json_path=Path(d)/"private"/"diligence.json"
            md_path=Path(d)/"private"/"diligence.md"
            write_enterprise_diligence_package(
                package,json_path=json_path,markdown_path=md_path)
            self.assertTrue(private_permissions_verified(json_path))
            self.assertTrue(private_permissions_verified(md_path))
            self.assertIn("No SOC 2",md_path.read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
