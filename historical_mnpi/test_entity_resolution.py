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
from historical_mnpi.entity_resolution import (
    CanonicalEntity,
    CaseEntityResolution,
    EntityKind,
    EntityRegistry,
    IdentifierBinding,
    IdentifierScheme,
    ResolutionStatus,
)
from historical_mnpi.raw_artifacts import (
    LocalContentAddressedArtifactStore,
    SourceArtifactRef,
    SourceLocatorKind,
    freeze_raw_artifact_manifest,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility,
    SourceRecord,
    SourceRegistry,
    SourceType,
)


def H(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fixture():
    raw = b"historical public identity evidence"
    source = SourceRecord(
        source_id="SEC:ENTITY:001",
        source_type=SourceType.SEC_COMPLAINT,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="SEC",
        title="Historical complaint",
        url="https://www.sec.gov/entity-example.pdf",
        publication_date="2015-01-01",
        sha256=H(raw),
        retrieved_at="2026-09-24T13:00:00Z",
        public_release_confirmed=True,
        case_id="CASE-ENTITY",
    )
    sources = SourceRegistry()
    sources.register(source)
    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        artifact = store.retain(
            sources,
            source,
            raw,
            media_type="application/pdf",
            acquired_at="2026-09-24T13:00:00Z",
            stored_at="2026-09-24T13:01:00Z",
        )
        manifest = freeze_raw_artifact_manifest(
            sources,
            (artifact,),
            created_at="2026-09-24T13:02:00Z",
            created_by="test",
        )
    ref = SourceArtifactRef(
        source_id=source.source_id,
        source_proof_hash=source.proof_hash,
        artifact_id=artifact.artifact_id,
        artifact_sha256=artifact.sha256,
        artifact_record_proof_hash=artifact.proof_hash,
        locator_kind=SourceLocatorKind.PAGE,
        locator="page=1",
    )
    case = HistoricalCase(
        case_id="CASE-ENTITY",
        title="Historical identity case",
        event_type=CaseEventType.EARNINGS,
        information_origin="historical earnings information",
        proceeding_status=CaseProceedingStatus.SETTLED,
        parties=(
            CaseParty(
                party_id="party:case:john",
                display_name="John Smith",
                roles=(CasePartyRole.TRADER,),
            ),
        ),
        issuers=(
            CaseIssuer(
                issuer_id="issuer:case:alpha",
                legal_name="Alpha Corp.",
                cik="123456",
                ticker_at_case="ALP",
            ),
        ),
        artifacts=(CaseArtifactLink(CaseArtifactRole.COMPLAINT, ref),),
    )
    cases = CaseRegistry()
    cases.register(case, source_registry=sources, artifact_manifest=manifest)
    return sources, manifest, cases, case, ref


class EntityResolutionTests(unittest.TestCase):
    def test_same_display_name_does_not_auto_merge_entities(self):
        registry = EntityRegistry()
        a = CanonicalEntity("person:john:1", EntityKind.PERSON, "John Smith")
        b = CanonicalEntity("person:john:2", EntityKind.PERSON, "John Smith")
        registry.register_entity(a)
        registry.register_entity(b)
        self.assertNotEqual(a.entity_id, b.entity_id)
        self.assertNotEqual(a.proof_hash, b.proof_hash)

    def test_case_party_can_be_resolved_to_canonical_person(self):
        sources, manifest, cases, case, ref = fixture()
        registry = EntityRegistry()
        person = registry.register_entity(
            CanonicalEntity(
                "person:john:canonical",
                EntityKind.PERSON,
                "John Smith",
                aliases=("J. Smith",),
            )
        )
        resolution = CaseEntityResolution(
            resolution_id="resolution:person:1",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            local_id="party:case:john",
            entity_kind=EntityKind.PERSON,
            status=ResolutionStatus.RESOLVED,
            canonical_entity_id=person.entity_id,
            evidence_refs=(ref,),
            rationale="Complaint names the defendant.",
        )
        registry.register_case_resolution(
            resolution,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(len(registry.registry_hash), 64)

    def test_ambiguous_resolution_preserves_multiple_candidates(self):
        sources, manifest, cases, case, ref = fixture()
        registry = EntityRegistry()
        for entity_id in ("person:john:1", "person:john:2"):
            registry.register_entity(
                CanonicalEntity(entity_id, EntityKind.PERSON, "John Smith")
            )
        resolution = CaseEntityResolution(
            resolution_id="resolution:ambiguous:1",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            local_id="party:case:john",
            entity_kind=EntityKind.PERSON,
            status=ResolutionStatus.AMBIGUOUS,
            candidate_entity_ids=("person:john:2", "person:john:1"),
            evidence_refs=(ref,),
        )
        registered = registry.register_case_resolution(
            resolution,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(
            registered.candidate_entity_ids,
            ("person:john:1", "person:john:2"),
        )

    def test_unresolved_resolution_selects_nothing(self):
        sources, manifest, cases, case, _ref = fixture()
        registry = EntityRegistry()
        resolution = CaseEntityResolution(
            resolution_id="resolution:unresolved:1",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            local_id="party:case:john",
            entity_kind=EntityKind.PERSON,
            status=ResolutionStatus.UNRESOLVED,
            evidence_refs=(),
        )
        registry.register_case_resolution(
            resolution,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )

    def test_ambiguous_resolution_blocks_older_resolved_identity(self):
        sources, manifest, cases, case, ref = fixture()
        registry = EntityRegistry()
        first = registry.register_entity(
            CanonicalEntity("person:john:1", EntityKind.PERSON, "John Smith")
        )
        registry.register_entity(
            CanonicalEntity("person:john:2", EntityKind.PERSON, "John Smith")
        )
        registry.register_case_resolution(
            CaseEntityResolution(
                resolution_id="resolution:resolved:first",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                local_id="party:case:john",
                entity_kind=EntityKind.PERSON,
                status=ResolutionStatus.RESOLVED,
                canonical_entity_id=first.entity_id,
                evidence_refs=(ref,),
            ),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        registry.register_case_resolution(
            CaseEntityResolution(
                resolution_id="resolution:later:ambiguous",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                local_id="party:case:john",
                entity_kind=EntityKind.PERSON,
                status=ResolutionStatus.AMBIGUOUS,
                candidate_entity_ids=("person:john:1", "person:john:2"),
                evidence_refs=(ref,),
            ),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            registry.resolved_entity_for(
                case.case_id,
                "party:case:john",
                EntityKind.PERSON,
            )

    def test_organization_resolution_requires_real_case_party(self):
        sources, manifest, cases, case, ref = fixture()
        registry = EntityRegistry()
        organization = registry.register_entity(
            CanonicalEntity(
                "organization:firm:1",
                EntityKind.ORGANIZATION,
                "Historical Firm",
            )
        )
        resolution = CaseEntityResolution(
            resolution_id="resolution:organization:bad-local",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            local_id="organization:not-in-case",
            entity_kind=EntityKind.ORGANIZATION,
            status=ResolutionStatus.RESOLVED,
            canonical_entity_id=organization.entity_id,
            evidence_refs=(ref,),
        )
        with self.assertRaisesRegex(ValueError, "not a case party"):
            registry.register_case_resolution(
                resolution,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_non_overlapping_ticker_reuse_is_allowed(self):
        sources, manifest, _cases, _case, ref = fixture()
        registry = EntityRegistry()
        first = registry.register_entity(
            CanonicalEntity("issuer:alpha", EntityKind.ISSUER, "Alpha Corp.")
        )
        second = registry.register_entity(
            CanonicalEntity("issuer:beta", EntityKind.ISSUER, "Beta Corp.")
        )
        registry.register_binding(
            IdentifierBinding(
                "binding:ticker:alpha",
                first.entity_id,
                IdentifierScheme.TICKER,
                "xyz",
                ref,
                valid_from="2000-01-01",
                valid_to="2005-12-31",
            ),
            source_registry=sources,
            artifact_manifest=manifest,
        )
        registry.register_binding(
            IdentifierBinding(
                "binding:ticker:beta",
                second.entity_id,
                IdentifierScheme.TICKER,
                "XYZ",
                ref,
                valid_from="2006-01-01",
            ),
            source_registry=sources,
            artifact_manifest=manifest,
        )
        status, ids = registry.resolve_identifier(
            IdentifierScheme.TICKER,
            "xyz",
            as_of_date="2004-01-01",
        )
        self.assertEqual(status, ResolutionStatus.RESOLVED)
        self.assertEqual(ids, ("issuer:alpha",))
        status2, ids2 = registry.resolve_identifier(
            IdentifierScheme.TICKER,
            "XYZ",
            as_of_date="2010-01-01",
        )
        self.assertEqual(status2, ResolutionStatus.RESOLVED)
        self.assertEqual(ids2, ("issuer:beta",))

    def test_overlapping_ticker_binding_to_different_issuer_fails_closed(self):
        sources, manifest, _cases, _case, ref = fixture()
        registry = EntityRegistry()
        registry.register_entity(
            CanonicalEntity("issuer:alpha", EntityKind.ISSUER, "Alpha Corp.")
        )
        registry.register_entity(
            CanonicalEntity("issuer:beta", EntityKind.ISSUER, "Beta Corp.")
        )
        registry.register_binding(
            IdentifierBinding(
                "binding:ticker:1",
                "issuer:alpha",
                IdentifierScheme.TICKER,
                "XYZ",
                ref,
                valid_from="2000-01-01",
                valid_to="2010-12-31",
            ),
            source_registry=sources,
            artifact_manifest=manifest,
        )
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            registry.register_binding(
                IdentifierBinding(
                    "binding:ticker:2",
                    "issuer:beta",
                    IdentifierScheme.TICKER,
                    "XYZ",
                    ref,
                    valid_from="2005-01-01",
                    valid_to="2015-12-31",
                ),
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_cik_cannot_bind_two_confirmed_issuers(self):
        sources, manifest, _cases, _case, ref = fixture()
        registry = EntityRegistry()
        for entity_id in ("issuer:alpha", "issuer:beta"):
            registry.register_entity(
                CanonicalEntity(entity_id, EntityKind.ISSUER, entity_id)
            )
        registry.register_binding(
            IdentifierBinding(
                "binding:cik:1",
                "issuer:alpha",
                IdentifierScheme.CIK,
                "0000123456",
                ref,
            ),
            source_registry=sources,
            artifact_manifest=manifest,
        )
        with self.assertRaisesRegex(ValueError, "different entity"):
            registry.register_binding(
                IdentifierBinding(
                    "binding:cik:2",
                    "issuer:beta",
                    IdentifierScheme.CIK,
                    "123456",
                    ref,
                ),
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_mismatched_artifact_manifest_and_source_registry_fail_closed(self):
        sources, manifest, cases, case, ref = fixture()
        mismatched = SourceRegistry()
        for item in sources.all():
            mismatched.register(item)
        mismatched.register(SourceRecord(
            source_id="SEC:ENTITY:EXTRA",
            source_type=SourceType.SEC_COMPLAINT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            publisher="SEC",
            title="Extra source",
            url="https://www.sec.gov/entity-extra.pdf",
            publication_date="2015-01-02",
            sha256=H(b"extra-source"),
            retrieved_at="2026-09-24T13:03:00Z",
            public_release_confirmed=True,
            case_id="CASE-ENTITY",
        ))

        registry = EntityRegistry()
        entity = registry.register_entity(
            CanonicalEntity("issuer:canonical:mismatch", EntityKind.ISSUER, "Alpha Corp.")
        )
        binding = IdentifierBinding(
            "binding:mismatch",
            entity.entity_id,
            IdentifierScheme.CIK,
            "123456",
            ref,
        )
        with self.assertRaisesRegex(ValueError, "manifest/source registry mismatch"):
            registry.register_binding(
                binding,
                source_registry=mismatched,
                artifact_manifest=manifest,
            )

if __name__ == "__main__":
    unittest.main()
