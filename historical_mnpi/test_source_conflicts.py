import hashlib
import tempfile
import unittest

from historical_mnpi.case_model import (
    CaseArtifactLink,
    CaseArtifactRole,
    CaseEventType,
    CaseIssuer,
    CaseParty,
    CasePartyRole,
    CaseProceedingStatus,
    CaseRegistry,
    HistoricalCase,
)
from historical_mnpi.raw_artifacts import (
    LocalContentAddressedArtifactStore,
    SourceArtifactRef,
    SourceLocatorKind,
    freeze_raw_artifact_manifest,
)
from historical_mnpi.source_conflicts import (
    ClaimAuthority,
    ConflictResolutionState,
    SourceConflictClaim,
    assess_conflicting_claims,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility,
    SourceRecord,
    SourceRegistry,
    SourceType,
)
from historical_mnpi.transaction_model import FactStatus


def H(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture():
    specs = (
        (
            "SEC:CONFLICT:COMPLAINT",
            SourceType.SEC_COMPLAINT,
            SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            CaseArtifactRole.COMPLAINT,
            b"complaint evidence",
        ),
        (
            "COURT:CONFLICT:JUDGMENT",
            SourceType.COURT_JUDGMENT,
            SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            CaseArtifactRole.JUDGMENT,
            b"judgment evidence",
        ),
        (
            "ACADEMIC:CONFLICT:001",
            SourceType.ACADEMIC_REPLICATION,
            SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
            CaseArtifactRole.ACADEMIC_RECONSTRUCTION,
            b"academic evidence",
        ),
        (
            "SECONDARY:CONFLICT:001",
            SourceType.SECONDARY_INDEX,
            SourceAdmissibility.DISCOVERY_ONLY,
            None,
            b"secondary evidence",
        ),
    )
    sources = SourceRegistry()
    records = []
    for source_id, source_type, admissibility, _role, raw in specs:
        source = SourceRecord(
            source_id=source_id,
            source_type=source_type,
            admissibility=admissibility,
            publisher="Public source",
            title=source_id,
            url="https://example.org/" + source_id.lower().replace(":", "-"),
            publication_date="2015-08-11",
            sha256=H(raw),
            retrieved_at="2026-09-24T13:00:00Z",
            public_release_confirmed=True,
            case_id="CASE-CONFLICT",
        )
        sources.register(source)
        records.append((source, _role, raw))

    refs = {}
    artifacts = []
    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        for source, role, raw in records:
            artifact = store.retain(
                sources,
                source,
                raw,
                media_type="application/pdf",
                acquired_at="2026-09-24T13:00:00Z",
                stored_at="2026-09-24T13:01:00Z",
            )
            artifacts.append(artifact)
            refs[source.source_id] = SourceArtifactRef(
                source_id=source.source_id,
                source_proof_hash=source.proof_hash,
                artifact_id=artifact.artifact_id,
                artifact_sha256=artifact.sha256,
                artifact_record_proof_hash=artifact.proof_hash,
                locator_kind=SourceLocatorKind.PAGE,
                locator="page=1",
            )

        manifest = freeze_raw_artifact_manifest(
            sources,
            tuple(artifacts),
            created_at="2026-09-24T13:02:00Z",
            created_by="test",
        )

    case = HistoricalCase(
        case_id="CASE-CONFLICT",
        title="Historical conflict matter",
        event_type=CaseEventType.EARNINGS,
        information_origin="pre-release earnings information",
        proceeding_status=CaseProceedingStatus.FINAL_CIVIL_JUDGMENT,
        parties=(
            CaseParty(
                party_id="party:trader",
                display_name="Historical Trader",
                roles=(CasePartyRole.TRADER, CasePartyRole.DEFENDANT),
            ),
        ),
        issuers=(
            CaseIssuer(
                issuer_id="issuer:target",
                legal_name="Target Corp.",
                cik="123456",
                ticker_at_case="TGT",
            ),
        ),
        artifacts=tuple(
            CaseArtifactLink(role, refs[source.source_id])
            for source, role, _raw in records
            if role is not None
        ),
    )
    cases = CaseRegistry()
    cases.register(
        case,
        source_registry=sources,
        artifact_manifest=manifest,
    )
    return sources, manifest, cases, refs


def claim(
    claim_id,
    *,
    source_id,
    refs,
    value,
    role,
    status,
    field_name="quantity",
):
    return SourceConflictClaim(
        claim_id=claim_id,
        case_id="CASE-CONFLICT",
        field_name=field_name,
        value=value,
        source_ref=refs[source_id],
        artifact_role=role,
        fact_status=status,
    )


class SourceConflictPolicyTests(unittest.TestCase):
    def test_judgment_fact_preferred_over_complaint_but_both_retained(self):
        sources, manifest, cases, refs = fixture()
        complaint = claim(
            "claim:complaint",
            source_id="SEC:CONFLICT:COMPLAINT",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.COMPLAINT,
            status=FactStatus.ALLEGED,
        )
        judgment = claim(
            "claim:judgment",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="2400",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.COURT_ESTABLISHED,
        )
        result = assess_conflicting_claims(
            (complaint, judgment),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(
            result.state,
            ConflictResolutionState.PREFERRED_VALUE_WITH_CONTRADICTIONS,
        )
        self.assertEqual(result.preferred_value, "2400")
        self.assertEqual(
            result.top_authority,
            ClaimAuthority.ESTABLISHED_OR_ADMITTED,
        )
        self.assertEqual(len(result.claims), 2)
        self.assertIn(complaint.proof_hash, result.contradictory_claim_hashes)

    def test_primary_allegation_preferred_over_academic_reconstruction(self):
        sources, manifest, cases, refs = fixture()
        complaint = claim(
            "claim:complaint",
            source_id="SEC:CONFLICT:COMPLAINT",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.COMPLAINT,
            status=FactStatus.ALLEGED,
        )
        academic = claim(
            "claim:academic",
            source_id="ACADEMIC:CONFLICT:001",
            refs=refs,
            value="2600",
            role=CaseArtifactRole.ACADEMIC_RECONSTRUCTION,
            status=FactStatus.ACADEMIC_RECONSTRUCTION,
        )
        result = assess_conflicting_claims(
            (academic, complaint),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(result.preferred_value, "2500")
        self.assertEqual(
            result.top_authority,
            ClaimAuthority.PRIMARY_ALLEGATION,
        )
        self.assertIn(academic.proof_hash, result.contradictory_claim_hashes)

    def test_discovery_only_claim_is_preserved_but_cannot_establish_value(self):
        sources, manifest, cases, refs = fixture()
        secondary = claim(
            "claim:secondary",
            source_id="SECONDARY:CONFLICT:001",
            refs=refs,
            value="9999",
            role=None,
            status=None,
        )
        result = assess_conflicting_claims(
            (secondary,),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(
            result.state,
            ConflictResolutionState.NO_CANONICAL_SUPPORT,
        )
        self.assertIsNone(result.preferred_value)
        self.assertEqual(len(result.claims), 1)
        self.assertEqual(
            result.claims[0].authority,
            ClaimAuthority.DISCOVERY_ONLY,
        )

    def test_conflicting_top_tier_judgments_fail_unresolved(self):
        sources, manifest, cases, refs = fixture()
        first = claim(
            "claim:judgment:one",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="2400",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.COURT_ESTABLISHED,
        )
        second = claim(
            "claim:judgment:two",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="2450",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.COURT_ESTABLISHED,
        )
        result = assess_conflicting_claims(
            (first, second),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(
            result.state,
            ConflictResolutionState.UNRESOLVED_TOP_TIER_CONFLICT,
        )
        self.assertIsNone(result.preferred_value)
        self.assertEqual(
            set(result.contradictory_claim_hashes),
            {first.proof_hash, second.proof_hash},
        )

    def test_agreeing_top_tier_claims_can_outweigh_lower_contradiction(self):
        sources, manifest, cases, refs = fixture()
        judgment_one = claim(
            "claim:judgment:one",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="2400",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.COURT_ESTABLISHED,
        )
        judgment_two = claim(
            "claim:judgment:two",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="2400",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.FOUND_LIABLE,
        )
        complaint = claim(
            "claim:complaint",
            source_id="SEC:CONFLICT:COMPLAINT",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.COMPLAINT,
            status=FactStatus.ALLEGED,
        )
        result = assess_conflicting_claims(
            (complaint, judgment_two, judgment_one),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(result.preferred_value, "2400")
        self.assertEqual(len(result.preferred_claim_hashes), 2)
        self.assertEqual(
            result.contradictory_claim_hashes,
            (complaint.proof_hash,),
        )

    def test_same_value_across_all_claims_is_no_conflict(self):
        sources, manifest, cases, refs = fixture()
        complaint = claim(
            "claim:complaint",
            source_id="SEC:CONFLICT:COMPLAINT",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.COMPLAINT,
            status=FactStatus.ALLEGED,
        )
        academic = claim(
            "claim:academic",
            source_id="ACADEMIC:CONFLICT:001",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.ACADEMIC_RECONSTRUCTION,
            status=FactStatus.ACADEMIC_RECONSTRUCTION,
        )
        result = assess_conflicting_claims(
            (academic, complaint),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(result.state, ConflictResolutionState.NO_CONFLICT)
        self.assertEqual(result.preferred_value, "2500")
        self.assertEqual(result.contradictory_claim_hashes, ())

    def test_settlement_without_admission_does_not_upgrade_trade_fact(self):
        sources, manifest, cases, refs = fixture()
        settlement = claim(
            "claim:settlement",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="2400",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.SETTLED_WITHOUT_ADMISSION,
        )
        complaint = claim(
            "claim:complaint",
            source_id="SEC:CONFLICT:COMPLAINT",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.COMPLAINT,
            status=FactStatus.ALLEGED,
        )
        result = assess_conflicting_claims(
            (settlement, complaint),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(result.preferred_value, "2500")
        self.assertEqual(
            result.top_authority,
            ClaimAuthority.PRIMARY_ALLEGATION,
        )

    def test_settlement_status_itself_is_official_status_evidence(self):
        sources, manifest, cases, refs = fixture()
        settlement = claim(
            "claim:settlement-status",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="SETTLED_WITHOUT_ADMISSION",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.SETTLED_WITHOUT_ADMISSION,
            field_name="fact_status",
        )
        academic = claim(
            "claim:academic-status",
            source_id="ACADEMIC:CONFLICT:001",
            refs=refs,
            value="ALLEGED",
            role=CaseArtifactRole.ACADEMIC_RECONSTRUCTION,
            status=FactStatus.ACADEMIC_RECONSTRUCTION,
            field_name="fact_status",
        )
        result = assess_conflicting_claims(
            (academic, settlement),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(
            result.top_authority,
            ClaimAuthority.OFFICIAL_NON_ADMISSION_STATUS,
        )
        self.assertEqual(result.preferred_value, "SETTLED_WITHOUT_ADMISSION")

    def test_assessment_hash_is_order_independent(self):
        sources, manifest, cases, refs = fixture()
        complaint = claim(
            "claim:complaint",
            source_id="SEC:CONFLICT:COMPLAINT",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.COMPLAINT,
            status=FactStatus.ALLEGED,
        )
        judgment = claim(
            "claim:judgment",
            source_id="COURT:CONFLICT:JUDGMENT",
            refs=refs,
            value="2400",
            role=CaseArtifactRole.JUDGMENT,
            status=FactStatus.COURT_ESTABLISHED,
        )
        left = assess_conflicting_claims(
            (complaint, judgment),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        right = assess_conflicting_claims(
            (judgment, complaint),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(left.proof_hash, right.proof_hash)

    def test_academic_source_cannot_masquerade_as_primary_claim(self):
        sources, manifest, cases, refs = fixture()
        bad = claim(
            "claim:bad-academic",
            source_id="ACADEMIC:CONFLICT:001",
            refs=refs,
            value="2500",
            role=CaseArtifactRole.ACADEMIC_RECONSTRUCTION,
            status=FactStatus.ALLEGED,
        )
        with self.assertRaisesRegex(ValueError, "academic reconstruction status"):
            assess_conflicting_claims(
                (bad,),
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )


if __name__ == "__main__":
    unittest.main()
