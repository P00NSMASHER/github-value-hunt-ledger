import hashlib
import tempfile
import unittest

from historical_mnpi.case_model import (
    CaseArtifactLink, CaseArtifactRole, CaseEventType, CaseIssuer, CaseParty,
    CasePartyRole, CaseProceedingStatus, CaseRegistry, HistoricalCase,
)
from historical_mnpi.conflict_policy import (
    ConflictDisposition, FactClaim, FactDomain, SourcePriorityPolicy,
    resolve_fact_conflict,
)
from historical_mnpi.raw_artifacts import (
    LocalContentAddressedArtifactStore, SourceArtifactRef, SourceLocatorKind,
    freeze_raw_artifact_manifest,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility, SourceRecord, SourceRegistry, SourceType,
)


def H(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture():
    specs = (
        ("complaint", SourceType.SEC_COMPLAINT, CaseArtifactRole.COMPLAINT, b"complaint"),
        ("judgment", SourceType.COURT_JUDGMENT, CaseArtifactRole.JUDGMENT, b"judgment"),
        ("release", SourceType.PUBLIC_PRESS_RELEASE, CaseArtifactRole.PUBLIC_RELEASE, b"release"),
        ("academic", SourceType.ACADEMIC_REPLICATION, CaseArtifactRole.ACADEMIC_RECONSTRUCTION, b"academic"),
    )
    sources = SourceRegistry()
    records = []
    for name, stype, _role, raw in specs:
        admissibility = (
            SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
            if stype is SourceType.ACADEMIC_REPLICATION
            else SourceAdmissibility.PRIMARY_PUBLIC_RECORD
        )
        rec = SourceRecord(
            source_id=f"SRC:{name}",
            source_type=stype,
            admissibility=admissibility,
            publisher=name,
            title=name,
            url=f"https://example.org/{name}",
            publication_date="2015-01-01",
            sha256=H(raw),
            retrieved_at="2026-09-24T13:20:00Z",
            public_release_confirmed=True,
            case_id="CASE-CONFLICT",
        )
        sources.register(rec)
        records.append((rec, raw, _role))
    refs = {}
    artifacts = []
    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        for rec, raw, role in records:
            art = store.retain(
                sources, rec, raw,
                media_type="application/pdf" if role is not CaseArtifactRole.PUBLIC_RELEASE else "text/html",
                acquired_at="2026-09-24T13:20:00Z",
                stored_at="2026-09-24T13:21:00Z",
            )
            artifacts.append(art)
            refs[role] = SourceArtifactRef(
                source_id=rec.source_id,
                source_proof_hash=rec.proof_hash,
                artifact_id=art.artifact_id,
                artifact_sha256=art.sha256,
                artifact_record_proof_hash=art.proof_hash,
                locator_kind=SourceLocatorKind.PAGE,
                locator="page=1",
            )
        manifest = freeze_raw_artifact_manifest(
            sources, tuple(artifacts),
            created_at="2026-09-24T13:22:00Z",
            created_by="test",
        )
    case = HistoricalCase(
        case_id="CASE-CONFLICT",
        title="Conflict case",
        event_type=CaseEventType.EARNINGS,
        information_origin="historical information",
        proceeding_status=CaseProceedingStatus.FINAL_CIVIL_JUDGMENT,
        parties=(CaseParty("party:1", "Trader", (CasePartyRole.TRADER,)),),
        issuers=(CaseIssuer("issuer:1", "Issuer"),),
        artifacts=tuple(CaseArtifactLink(role, refs[role]) for _r, _b, role in records),
    )
    cases = CaseRegistry()
    cases.register(case, source_registry=sources, artifact_manifest=manifest)
    return sources, manifest, cases, case, refs


def claim(case, ref, claim_id, value, domain=FactDomain.TRANSACTION_DETAIL):
    return FactClaim(
        claim_id=claim_id,
        case_id=case.case_id,
        case_proof_hash=case.proof_hash,
        fact_key="trade:1.quantity",
        fact_domain=domain,
        value=value,
        source_ref=ref,
    )


class ConflictPolicyTests(unittest.TestCase):
    def test_judgment_controls_conflicting_complaint_transaction_fact(self):
        sources, manifest, cases, case, refs = fixture()
        result = resolve_fact_conflict((
            claim(case, refs[CaseArtifactRole.COMPLAINT], "claim:complaint", "2500"),
            claim(case, refs[CaseArtifactRole.JUDGMENT], "claim:judgment", "2600"),
        ), cases=cases, source_registry=sources, artifact_manifest=manifest)
        self.assertEqual(result.disposition, ConflictDisposition.SELECTED)
        self.assertEqual(result.selected_value, "2600")
        self.assertEqual(result.controlling_claim_ids, ("claim:judgment",))
        self.assertIn("claim:complaint", result.conflicting_claim_ids)
        result.verify_integrity()

    def test_equal_priority_judgments_with_different_values_remain_ambiguous(self):
        sources, manifest, cases, case, refs = fixture()
        a = claim(case, refs[CaseArtifactRole.JUDGMENT], "claim:j1", "2500")
        b = claim(case, refs[CaseArtifactRole.JUDGMENT], "claim:j2", "2600")
        result = resolve_fact_conflict(
            (a, b), cases=cases, source_registry=sources, artifact_manifest=manifest
        )
        self.assertEqual(result.disposition, ConflictDisposition.AMBIGUOUS)
        self.assertIsNone(result.selected_value)
        self.assertEqual(set(result.controlling_claim_ids), {"claim:j1", "claim:j2"})

    def test_public_release_controls_publication_boundary_over_complaint(self):
        sources, manifest, cases, case, refs = fixture()
        complaint = FactClaim(
            "claim:complaint:time", case.case_id, case.proof_hash,
            "event:1.public_release", FactDomain.PUBLICATION_BOUNDARY,
            "16:05", refs[CaseArtifactRole.COMPLAINT],
        )
        release = FactClaim(
            "claim:release:time", case.case_id, case.proof_hash,
            "event:1.public_release", FactDomain.PUBLICATION_BOUNDARY,
            "16:03", refs[CaseArtifactRole.PUBLIC_RELEASE],
        )
        result = resolve_fact_conflict(
            (complaint, release),
            cases=cases, source_registry=sources, artifact_manifest=manifest,
        )
        self.assertEqual(result.selected_value, "16:03")
        self.assertEqual(result.controlling_claim_ids, ("claim:release:time",))

    def test_primary_complaint_controls_academic_reconstruction_for_transaction_fact(self):
        sources, manifest, cases, case, refs = fixture()
        result = resolve_fact_conflict((
            claim(case, refs[CaseArtifactRole.ACADEMIC_RECONSTRUCTION], "claim:academic", "2500"),
            claim(case, refs[CaseArtifactRole.COMPLAINT], "claim:complaint", "2500"),
        ), cases=cases, source_registry=sources, artifact_manifest=manifest)
        self.assertEqual(result.selected_value, "2500")
        self.assertEqual(result.controlling_claim_ids, ("claim:complaint",))

    def test_multiple_top_sources_same_value_are_all_controlling(self):
        sources, manifest, cases, case, refs = fixture()
        a = claim(case, refs[CaseArtifactRole.JUDGMENT], "claim:j1", "2500")
        b = claim(case, refs[CaseArtifactRole.JUDGMENT], "claim:j2", "2500")
        result = resolve_fact_conflict(
            (b, a), cases=cases, source_registry=sources, artifact_manifest=manifest
        )
        self.assertEqual(result.disposition, ConflictDisposition.SELECTED)
        self.assertEqual(result.controlling_claim_ids, ("claim:j1", "claim:j2"))

    def test_resolution_is_bound_to_full_policy_proof(self):
        sources, manifest, cases, case, refs = fixture()
        policy = SourcePriorityPolicy()
        result = resolve_fact_conflict((
            claim(case, refs[CaseArtifactRole.COMPLAINT], "claim:c", "2500"),
            claim(case, refs[CaseArtifactRole.JUDGMENT], "claim:j", "2600"),
        ), cases=cases, source_registry=sources, artifact_manifest=manifest, policy=policy)
        self.assertEqual(result.policy_proof_hash, policy.proof_hash)
        self.assertEqual(len(result.policy_proof_hash), 64)

    def test_same_artifact_cannot_be_retyped_to_gain_priority(self):
        sources, manifest, cases, refs = fixture()
        base = cases.get("CASE-CONFLICT")
        complaint_ref = refs[CaseArtifactRole.COMPLAINT]
        retyped = HistoricalCase(
            **{
                **base.__dict__,
                "artifacts": base.artifacts + (
                    CaseArtifactLink(
                        CaseArtifactRole.EXHIBIT,
                        complaint_ref,
                    ),
                ),
            }
        )
        with self.assertRaisesRegex(ValueError, "incompatible"):
            CaseRegistry().register(
                retyped,
                source_registry=sources,
                artifact_manifest=manifest,
            )


    def test_policy_hash_is_deterministic(self):
        self.assertEqual(
            SourcePriorityPolicy().proof_hash,
            SourcePriorityPolicy().proof_hash,
        )

    def test_mismatched_artifact_manifest_and_source_registry_fail_closed(self):
        sources, manifest, cases, case, refs = fixture()
        mismatched = SourceRegistry()
        for item in sources.all():
            mismatched.register(item)
        mismatched.register(SourceRecord(
            source_id="SRC:extra",
            source_type=SourceType.SEC_COMPLAINT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            publisher="extra",
            title="extra",
            url="https://example.org/extra",
            publication_date="2015-01-02",
            sha256=H(b"extra"),
            retrieved_at="2026-09-24T13:23:00Z",
            public_release_confirmed=True,
            case_id="CASE-CONFLICT",
        ))
        with self.assertRaisesRegex(ValueError, "manifest/source registry mismatch"):
            resolve_fact_conflict((
                claim(
                    case,
                    refs[CaseArtifactRole.COMPLAINT],
                    "claim:mismatch",
                    "2500",
                ),
            ), cases=cases, source_registry=mismatched, artifact_manifest=manifest)

if __name__ == "__main__":
    unittest.main()
