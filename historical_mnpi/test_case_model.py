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
    verify_case_provenance,
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


def H(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_fixture(*, discovery_only=False, academic=False):
    raw = b"historical case public record bytes"
    if discovery_only:
        source_type = SourceType.SECONDARY_INDEX
        admissibility = SourceAdmissibility.DISCOVERY_ONLY
    elif academic:
        source_type = SourceType.ACADEMIC_REPLICATION
        admissibility = SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION
    else:
        source_type = SourceType.SEC_COMPLAINT
        admissibility = SourceAdmissibility.PRIMARY_PUBLIC_RECORD

    source = SourceRecord(
        source_id="CASE:SOURCE:001",
        source_type=source_type,
        admissibility=admissibility,
        publisher="Public source",
        title="Historical source",
        url="https://example.org/source.pdf",
        publication_date="2015-08-11",
        sha256=H(raw),
        retrieved_at="2026-09-24T10:00:00Z",
        public_release_confirmed=True,
        case_id="CASE-001",
    )
    registry = SourceRegistry()
    registry.register(source)

    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        record = store.retain(
            registry,
            source,
            raw,
            media_type="application/pdf",
            acquired_at="2026-09-24T10:00:00Z",
            stored_at="2026-09-24T10:01:00Z",
        )
        manifest = freeze_raw_artifact_manifest(
            registry,
            (record,),
            created_at="2026-09-24T10:02:00Z",
            created_by="test",
        )

    ref = SourceArtifactRef(
        source_id=source.source_id,
        source_proof_hash=source.proof_hash,
        artifact_id=record.artifact_id,
        artifact_sha256=record.sha256,
        artifact_record_proof_hash=record.proof_hash,
        locator_kind=SourceLocatorKind.PAGE,
        locator="page=1",
    )
    return source, registry, manifest, ref


def build_case(ref, *, academic=False):
    return HistoricalCase(
        case_id="CASE-001",
        title="Historical insider-trading matter",
        event_type=CaseEventType.EARNINGS,
        information_origin="pre-release earnings information",
        proceeding_status=CaseProceedingStatus.FINAL_CIVIL_JUDGMENT,
        parties=(
            CaseParty(
                party_id="party:trader:1",
                display_name="Historical Trader",
                roles=(CasePartyRole.DEFENDANT, CasePartyRole.TRADER),
            ),
        ),
        issuers=(
            CaseIssuer(
                issuer_id="issuer:1",
                legal_name="Historical Issuer Inc.",
                cik="1234567",
                ticker_at_case="HIST",
            ),
        ),
        artifacts=(
            CaseArtifactLink(
                artifact_role=(
                    CaseArtifactRole.ACADEMIC_RECONSTRUCTION
                    if academic
                    else CaseArtifactRole.COMPLAINT
                ),
                ref=ref,
            ),
        ),
        complaint_or_opened_date="2015-08-11",
        judgment_or_resolution_date="2017-02-10",
    )


class HistoricalCaseTests(unittest.TestCase):
    def test_primary_case_registers_with_bound_artifact(self):
        _source, registry, manifest, ref = build_fixture()
        case = build_case(ref)
        cases = CaseRegistry()
        cases.register(
            case,
            source_registry=registry,
            artifact_manifest=manifest,
        )
        self.assertEqual(cases.get(case.case_id), case)
        self.assertEqual(len(case.proof_hash), 64)
        self.assertEqual(len(cases.registry_hash), 64)

    def test_discovery_only_source_cannot_establish_case(self):
        _source, registry, manifest, ref = build_fixture(discovery_only=True)
        case = build_case(ref)
        with self.assertRaisesRegex(ValueError, "discovery-only"):
            verify_case_provenance(
                case,
                source_registry=registry,
                artifact_manifest=manifest,
            )

    def test_academic_source_must_remain_academic_reconstruction(self):
        _source, registry, manifest, ref = build_fixture(academic=True)
        primary_role_case = build_case(ref, academic=False)
        with self.assertRaisesRegex(ValueError, "masquerade"):
            verify_case_provenance(
                primary_role_case,
                source_registry=registry,
                artifact_manifest=manifest,
            )

        academic_case = build_case(ref, academic=True)
        verify_case_provenance(
            academic_case,
            source_registry=registry,
            artifact_manifest=manifest,
        )

    def test_case_proof_is_order_independent_for_parties_and_issuers(self):
        _source, registry, manifest, ref = build_fixture()
        base = build_case(ref)
        second_party = CaseParty(
            party_id="party:tipper:2",
            display_name="Historical Tipper",
            roles=(CasePartyRole.TIPPER,),
        )
        second_issuer = CaseIssuer(
            issuer_id="issuer:2",
            legal_name="Second Issuer Inc.",
            cik="7654321",
            ticker_at_case="HST2",
        )

        left = HistoricalCase(
            **{
                **base.__dict__,
                "parties": (base.parties[0], second_party),
                "issuers": (base.issuers[0], second_issuer),
            }
        )
        right = HistoricalCase(
            **{
                **base.__dict__,
                "parties": (second_party, base.parties[0]),
                "issuers": (second_issuer, base.issuers[0]),
            }
        )
        self.assertEqual(left.proof_hash, right.proof_hash)
        verify_case_provenance(
            left,
            source_registry=registry,
            artifact_manifest=manifest,
        )

    def test_duplicate_party_and_issuer_ids_fail(self):
        _source, _registry, _manifest, ref = build_fixture()
        party = CaseParty(
            party_id="party:one",
            display_name="One",
            roles=(CasePartyRole.TRADER,),
        )
        issuer = CaseIssuer(
            issuer_id="issuer:one",
            legal_name="Issuer One",
        )
        with self.assertRaisesRegex(ValueError, "duplicate party_id"):
            HistoricalCase(
                case_id="CASE-DUP",
                title="Duplicate party",
                event_type=CaseEventType.OTHER,
                information_origin="historical source",
                proceeding_status=CaseProceedingStatus.UNKNOWN,
                parties=(party, party),
                issuers=(issuer,),
                artifacts=(
                    CaseArtifactLink(
                        artifact_role=CaseArtifactRole.COMPLAINT,
                        ref=ref,
                    ),
                ),
            )

    def test_conflicting_case_id_is_rejected(self):
        _source, registry, manifest, ref = build_fixture()
        first = build_case(ref)
        cases = CaseRegistry()
        cases.register(
            first,
            source_registry=registry,
            artifact_manifest=manifest,
        )
        altered = HistoricalCase(
            **{
                **first.__dict__,
                "title": "Different title",
            }
        )
        with self.assertRaisesRegex(ValueError, "different content"):
            cases.register(
                altered,
                source_registry=registry,
                artifact_manifest=manifest,
            )


if __name__ == "__main__":
    unittest.main()
