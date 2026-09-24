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
from historical_mnpi.event_model import (
    BoundaryPrecision,
    EventRegistry,
    InformationEvent,
    TemporalBoundary,
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
    complaint_raw = b"complaint establishes private information chronology"
    release_raw = b"public issuer earnings release"
    complaint = SourceRecord(
        source_id="SEC:EVENT:COMPLAINT",
        source_type=SourceType.SEC_COMPLAINT,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="SEC",
        title="Historical complaint",
        url="https://www.sec.gov/example-event.pdf",
        publication_date="2015-08-11",
        sha256=H(complaint_raw),
        retrieved_at="2026-09-24T11:00:00Z",
        public_release_confirmed=True,
        case_id="CASE-EVENT",
    )
    release = SourceRecord(
        source_id="ISSUER:EVENT:RELEASE",
        source_type=SourceType.PUBLIC_PRESS_RELEASE,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="Historical Issuer Inc.",
        title="Public earnings release",
        url="https://example.com/investors/release.html",
        publication_date="2015-08-10",
        sha256=H(release_raw),
        retrieved_at="2026-09-24T11:00:00Z",
        public_release_confirmed=True,
        case_id="CASE-EVENT",
    )
    sources = SourceRegistry()
    sources.register(complaint)
    sources.register(release)

    refs = {}
    artifacts = []
    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        for source, raw, role in (
            (complaint, complaint_raw, CaseArtifactRole.COMPLAINT),
            (release, release_raw, CaseArtifactRole.PUBLIC_RELEASE),
        ):
            artifact = store.retain(
                sources,
                source,
                raw,
                media_type="application/pdf" if role is CaseArtifactRole.COMPLAINT else "text/html",
                acquired_at="2026-09-24T11:00:00Z",
                stored_at="2026-09-24T11:01:00Z",
            )
            artifacts.append(artifact)
            refs[role] = SourceArtifactRef(
                source_id=source.source_id,
                source_proof_hash=source.proof_hash,
                artifact_id=artifact.artifact_id,
                artifact_sha256=artifact.sha256,
                artifact_record_proof_hash=artifact.proof_hash,
                locator_kind=SourceLocatorKind.PAGE if role is CaseArtifactRole.COMPLAINT else SourceLocatorKind.TEXT_RANGE,
                locator="page=3" if role is CaseArtifactRole.COMPLAINT else "chars=0-120",
            )
        manifest = freeze_raw_artifact_manifest(
            sources,
            tuple(artifacts),
            created_at="2026-09-24T11:02:00Z",
            created_by="test",
        )

    case = HistoricalCase(
        case_id="CASE-EVENT",
        title="Historical earnings matter",
        event_type=CaseEventType.EARNINGS,
        information_origin="pre-release earnings results",
        proceeding_status=CaseProceedingStatus.FINAL_CIVIL_JUDGMENT,
        parties=(
            CaseParty(
                party_id="party:event:trader",
                display_name="Historical Trader",
                roles=(CasePartyRole.TRADER, CasePartyRole.DEFENDANT),
            ),
        ),
        issuers=(
            CaseIssuer(
                issuer_id="issuer:event",
                legal_name="Historical Issuer Inc.",
                cik="1234567",
                ticker_at_case="HIST",
            ),
        ),
        artifacts=(
            CaseArtifactLink(
                artifact_role=CaseArtifactRole.COMPLAINT,
                ref=refs[CaseArtifactRole.COMPLAINT],
            ),
            CaseArtifactLink(
                artifact_role=CaseArtifactRole.PUBLIC_RELEASE,
                ref=refs[CaseArtifactRole.PUBLIC_RELEASE],
            ),
        ),
    )
    cases = CaseRegistry()
    cases.register(
        case,
        source_registry=sources,
        artifact_manifest=manifest,
    )
    return sources, manifest, cases, case, refs


class InformationEventTests(unittest.TestCase):
    def test_exact_public_boundary_and_private_start_register(self):
        sources, manifest, cases, case, refs = fixture()
        event = InformationEvent(
            event_id="event:earnings:001",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            event_type=CaseEventType.EARNINGS,
            issuer_ids=("issuer:event",),
            information_summary="Historical quarterly earnings results",
            private_information_start=TemporalBoundary(
                ref=refs[CaseArtifactRole.COMPLAINT],
                timestamp="2015-08-10T13:00:00-04:00",
                description="Complaint states results were known internally.",
            ),
            public_release=TemporalBoundary(
                ref=refs[CaseArtifactRole.PUBLIC_RELEASE],
                timestamp="2015-08-10T16:03:00-04:00",
                description="Issuer public release.",
            ),
        )
        EventRegistry().register(
            event,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(
            event.public_release.precision,
            BoundaryPrecision.EXACT_TIMESTAMP,
        )
        self.assertEqual(len(event.proof_hash), 64)

    def test_date_only_boundary_remains_date_only(self):
        _sources, _manifest, _cases, case, refs = fixture()
        boundary = TemporalBoundary(
            ref=refs[CaseArtifactRole.PUBLIC_RELEASE],
            date_value="2015-08-10",
        )
        self.assertEqual(boundary.precision, BoundaryPrecision.DATE_ONLY)
        self.assertIsNone(boundary.timestamp)

    def test_date_range_boundary_does_not_guess_exact_date(self):
        _sources, _manifest, _cases, case, refs = fixture()
        boundary = TemporalBoundary(
            ref=refs[CaseArtifactRole.COMPLAINT],
            date_range_start="2015-08-01",
            date_range_end="2015-08-05",
        )
        self.assertEqual(boundary.precision, BoundaryPrecision.DATE_RANGE)
        self.assertIsNone(boundary.date_value)

    def test_private_start_after_release_fails_when_exact(self):
        _sources, _manifest, _cases, case, refs = fixture()
        with self.assertRaisesRegex(ValueError, "cannot follow public release"):
            InformationEvent(
                event_id="event:bad:chronology",
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                event_type=CaseEventType.EARNINGS,
                issuer_ids=("issuer:event",),
                information_summary="Historical earnings",
                private_information_start=TemporalBoundary(
                    ref=refs[CaseArtifactRole.COMPLAINT],
                    timestamp="2015-08-10T17:00:00-04:00",
                ),
                public_release=TemporalBoundary(
                    ref=refs[CaseArtifactRole.PUBLIC_RELEASE],
                    timestamp="2015-08-10T16:03:00-04:00",
                ),
            )

    def test_unknown_issuer_fails_registration(self):
        sources, manifest, cases, case, refs = fixture()
        event = InformationEvent(
            event_id="event:bad:issuer",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            event_type=CaseEventType.EARNINGS,
            issuer_ids=("issuer:unknown",),
            information_summary="Historical earnings",
            public_release=TemporalBoundary(
                ref=refs[CaseArtifactRole.PUBLIC_RELEASE],
                date_value="2015-08-10",
            ),
        )
        with self.assertRaisesRegex(ValueError, "not part"):
            EventRegistry().register(
                event,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_complaint_cannot_masquerade_as_public_release(self):
        sources, manifest, cases, case, refs = fixture()
        event = InformationEvent(
            event_id="event:bad:release",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            event_type=CaseEventType.EARNINGS,
            issuer_ids=("issuer:event",),
            information_summary="Historical earnings",
            public_release=TemporalBoundary(
                ref=refs[CaseArtifactRole.COMPLAINT],
                date_value="2015-08-10",
            ),
        )
        with self.assertRaisesRegex(ValueError, "PUBLIC_RELEASE"):
            EventRegistry().register(
                event,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_conflicting_event_id_fails(self):
        sources, manifest, cases, case, refs = fixture()
        event = InformationEvent(
            event_id="event:earnings:002",
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            event_type=CaseEventType.EARNINGS,
            issuer_ids=("issuer:event",),
            information_summary="Historical earnings",
            public_release=TemporalBoundary(
                ref=refs[CaseArtifactRole.PUBLIC_RELEASE],
                date_value="2015-08-10",
            ),
        )
        registry = EventRegistry()
        registry.register(
            event,
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        altered = InformationEvent(
            event_id=event.event_id,
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            event_type=CaseEventType.EARNINGS,
            issuer_ids=("issuer:event",),
            information_summary="Different historical description",
            public_release=event.public_release,
        )
        with self.assertRaisesRegex(ValueError, "different content"):
            registry.register(
                altered,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )


if __name__ == "__main__":
    unittest.main()
