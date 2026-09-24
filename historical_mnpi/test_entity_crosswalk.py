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
    CaseEntityCrosswalk,
    CaseEntityCrosswalkRegistry,
    EntityKind,
    EntityResolutionRegistry,
    HistoricalIdentifier,
    HistoricalIdentifierType,
    IdentityAlias,
    IssuerIdentity,
    TraderIdentity,
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
    raw = b"historical public crosswalk evidence"
    source = SourceRecord(
        source_id="SEC:CROSSWALK:001",
        source_type=SourceType.SEC_COMPLAINT,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="Public source",
        title="Historical crosswalk evidence",
        url="https://www.sec.gov/example-crosswalk.pdf",
        publication_date="2015-08-11",
        sha256=H(raw),
        retrieved_at="2026-09-24T12:30:00Z",
        public_release_confirmed=True,
        case_id="CASE-CROSSWALK",
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
            acquired_at="2026-09-24T12:30:00Z",
            stored_at="2026-09-24T12:31:00Z",
        )
        manifest = freeze_raw_artifact_manifest(
            sources,
            (artifact,),
            created_at="2026-09-24T12:32:00Z",
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
        case_id="CASE-CROSSWALK",
        title="Historical crosswalk matter",
        event_type=CaseEventType.EARNINGS,
        information_origin="pre-release earnings information",
        proceeding_status=CaseProceedingStatus.SETTLED,
        parties=(
            CaseParty(
                party_id="party:trader",
                display_name="Historical Trader",
                roles=(CasePartyRole.TRADER, CasePartyRole.DEFENDANT),
            ),
            CaseParty(
                party_id="party:tipper",
                display_name="Historical Tipper",
                roles=(CasePartyRole.TIPPER,),
            ),
        ),
        issuers=(
            CaseIssuer(
                issuer_id="issuer:case-target",
                legal_name="Case Target Corp.",
                cik="1234567",
                ticker_at_case="CTGT",
            ),
        ),
        artifacts=(
            CaseArtifactLink(
                artifact_role=CaseArtifactRole.COMPLAINT,
                ref=ref,
            ),
        ),
        complaint_or_opened_date="2015-08-11",
    )
    cases = CaseRegistry()
    cases.register(
        case,
        source_registry=sources,
        artifact_manifest=manifest,
    )
    return sources, manifest, ref, cases, case


def durable_issuer(
    entity_id: str,
    name: str,
    ref: SourceArtifactRef,
    *,
    cik: str,
    ticker: str,
    valid_from: str | None = None,
    valid_to: str | None = None,
    aliases: tuple[str, ...] = (),
) -> IssuerIdentity:
    return IssuerIdentity(
        entity_id=entity_id,
        canonical_name=name,
        canonical_name_ref=ref,
        aliases=tuple(IdentityAlias(value, ref) for value in aliases),
        identifiers=(
            HistoricalIdentifier(
                HistoricalIdentifierType.CIK,
                cik,
                ref,
            ),
            HistoricalIdentifier(
                HistoricalIdentifierType.TICKER,
                ticker,
                ref,
                valid_from=valid_from,
                valid_to=valid_to,
            ),
        ),
    )


class CaseEntityCrosswalkTests(unittest.TestCase):
    def test_case_issuer_crosswalk_by_cik_registers(self):
        sources, manifest, ref, cases, case = fixture()
        entities = EntityResolutionRegistry()
        company = durable_issuer(
            "issuer-entity:target",
            "Durable Target Corp.",
            ref,
            cik="1234567",
            ticker="CTGT",
        )
        entities.register_issuer(
            company,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        result = entities.resolve_issuer_identifier(
            HistoricalIdentifierType.CIK,
            case.issuers[0].cik or "",
        )
        crosswalk = CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.ISSUER,
            local_id="issuer:case-target",
            durable_entity_id=company.entity_id,
            durable_entity_proof_hash=company.proof_hash,
            resolution=result,
        )
        registry = CaseEntityCrosswalkRegistry()
        registry.register(
            crosswalk,
            cases=cases,
            entities=entities,
        )

        self.assertEqual(
            registry.get(
                case.case_id,
                EntityKind.ISSUER,
                "issuer:case-target",
            ),
            crosswalk,
        )
        self.assertEqual(len(registry.registry_hash), 64)

    def test_case_trader_crosswalk_by_name_registers(self):
        sources, manifest, ref, cases, case = fixture()
        entities = EntityResolutionRegistry()
        trader = TraderIdentity(
            entity_id="trader-entity:historical",
            canonical_name="Historical Trader",
            canonical_name_ref=ref,
            aliases=(IdentityAlias("H. Trader", ref),),
        )
        entities.register_trader(
            trader,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        result = entities.resolve_trader_name("Historical Trader")
        crosswalk = CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.TRADER,
            local_id="party:trader",
            durable_entity_id=trader.entity_id,
            durable_entity_proof_hash=trader.proof_hash,
            resolution=result,
        )

        CaseEntityCrosswalkRegistry().register(
            crosswalk,
            cases=cases,
            entities=entities,
        )

    def test_ambiguous_resolution_cannot_be_crosswalked(self):
        sources, manifest, ref, _cases, case = fixture()
        entities = EntityResolutionRegistry()
        for entity_id, cik in (
            ("issuer-entity:first", "1111111"),
            ("issuer-entity:second", "2222222"),
        ):
            company = durable_issuer(
                entity_id,
                entity_id,
                ref,
                cik=cik,
                ticker="CTGT",
                valid_from="2010-01-01",
                valid_to="2020-01-01",
            )
            entities.register_issuer(
                company,
                source_registry=sources,
                artifact_manifest=manifest,
            )

        ambiguous = entities.resolve_issuer_identifier(
            HistoricalIdentifierType.TICKER,
            "CTGT",
            as_of_date="2015-08-10",
        )
        with self.assertRaisesRegex(ValueError, "uniquely resolved"):
            CaseEntityCrosswalk(
                case_id=case.case_id,
                case_proof_hash=case.proof_hash,
                entity_kind=EntityKind.ISSUER,
                local_id="issuer:case-target",
                durable_entity_id="issuer-entity:first",
                durable_entity_proof_hash=entities.issuer(
                    "issuer-entity:first"
                ).proof_hash,
                resolution=ambiguous,
            )

    def test_crosswalk_query_must_match_case_local_identity(self):
        sources, manifest, ref, cases, case = fixture()
        entities = EntityResolutionRegistry()
        company = durable_issuer(
            "issuer-entity:wrong-cik",
            "Wrong CIK Corp.",
            ref,
            cik="7654321",
            ticker="WRNG",
        )
        entities.register_issuer(
            company,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        result = entities.resolve_issuer_identifier(
            HistoricalIdentifierType.CIK,
            "7654321",
        )
        crosswalk = CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.ISSUER,
            local_id="issuer:case-target",
            durable_entity_id=company.entity_id,
            durable_entity_proof_hash=company.proof_hash,
            resolution=result,
        )

        with self.assertRaisesRegex(ValueError, "does not match case-local issuer"):
            CaseEntityCrosswalkRegistry().register(
                crosswalk,
                cases=cases,
                entities=entities,
            )

    def test_historical_ticker_crosswalk_requires_explicit_date(self):
        sources, manifest, ref, cases, case = fixture()
        entities = EntityResolutionRegistry()
        company = durable_issuer(
            "issuer-entity:target",
            "Case Target Corp.",
            ref,
            cik="1234567",
            ticker="CTGT",
            valid_from="2010-01-01",
        )
        entities.register_issuer(
            company,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        undated = entities.resolve_issuer_identifier(
            HistoricalIdentifierType.TICKER,
            "CTGT",
        )
        crosswalk = CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.ISSUER,
            local_id="issuer:case-target",
            durable_entity_id=company.entity_id,
            durable_entity_proof_hash=company.proof_hash,
            resolution=undated,
        )

        with self.assertRaisesRegex(ValueError, "requires as_of_date"):
            CaseEntityCrosswalkRegistry().register(
                crosswalk,
                cases=cases,
                entities=entities,
            )

    def test_non_trader_party_cannot_be_mapped_as_trader(self):
        sources, manifest, ref, cases, case = fixture()
        entities = EntityResolutionRegistry()
        trader = TraderIdentity(
            entity_id="trader-entity:tipper",
            canonical_name="Historical Tipper",
            canonical_name_ref=ref,
        )
        entities.register_trader(
            trader,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        result = entities.resolve_trader_name("Historical Tipper")
        crosswalk = CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.TRADER,
            local_id="party:tipper",
            durable_entity_id=trader.entity_id,
            durable_entity_proof_hash=trader.proof_hash,
            resolution=result,
        )

        with self.assertRaisesRegex(ValueError, "not a trader"):
            CaseEntityCrosswalkRegistry().register(
                crosswalk,
                cases=cases,
                entities=entities,
            )

    def test_case_local_mapping_is_append_only(self):
        sources, manifest, ref, cases, case = fixture()
        entities = EntityResolutionRegistry()
        first = durable_issuer(
            "issuer-entity:first",
            "First Durable Corp.",
            ref,
            cik="1234567",
            ticker="FIRST",
        )
        second = durable_issuer(
            "issuer-entity:second",
            "Case Target Corp.",
            ref,
            cik="9999999",
            ticker="SECOND",
        )
        for company in (first, second):
            entities.register_issuer(
                company,
                source_registry=sources,
                artifact_manifest=manifest,
            )

        first_result = entities.resolve_issuer_identifier(
            HistoricalIdentifierType.CIK,
            "1234567",
        )
        second_result = entities.resolve_issuer_name("Case Target Corp.")

        first_crosswalk = CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.ISSUER,
            local_id="issuer:case-target",
            durable_entity_id=first.entity_id,
            durable_entity_proof_hash=first.proof_hash,
            resolution=first_result,
        )
        second_crosswalk = CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.ISSUER,
            local_id="issuer:case-target",
            durable_entity_id=second.entity_id,
            durable_entity_proof_hash=second.proof_hash,
            resolution=second_result,
        )

        registry = CaseEntityCrosswalkRegistry()
        registry.register(
            first_crosswalk,
            cases=cases,
            entities=entities,
        )
        with self.assertRaisesRegex(ValueError, "already crosswalked"):
            registry.register(
                second_crosswalk,
                cases=cases,
                entities=entities,
            )


if __name__ == "__main__":
    unittest.main()
