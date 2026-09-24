import hashlib
import tempfile
import unittest

from historical_mnpi.entity_resolution import (
    EntityKind,
    EntityResolutionRegistry,
    HistoricalIdentifier,
    HistoricalIdentifierType,
    IdentityAlias,
    IssuerIdentity,
    ResolutionState,
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


def fixture(*, discovery_only: bool = False):
    raw = b"historical public identity evidence"
    source = SourceRecord(
        source_id="SEC:IDENTITY:001",
        source_type=(
            SourceType.SECONDARY_INDEX
            if discovery_only
            else SourceType.SEC_COMPLAINT
        ),
        admissibility=(
            SourceAdmissibility.DISCOVERY_ONLY
            if discovery_only
            else SourceAdmissibility.PRIMARY_PUBLIC_RECORD
        ),
        publisher="Public source",
        title="Historical identity evidence",
        url="https://www.sec.gov/example-identity.pdf",
        publication_date="2015-08-11",
        sha256=H(raw),
        retrieved_at="2026-09-24T12:00:00Z",
        public_release_confirmed=True,
        case_id="CASE-IDENTITY",
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
            acquired_at="2026-09-24T12:00:00Z",
            stored_at="2026-09-24T12:01:00Z",
        )
        manifest = freeze_raw_artifact_manifest(
            sources,
            (artifact,),
            created_at="2026-09-24T12:02:00Z",
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
    return sources, manifest, ref


def issuer(
    entity_id: str,
    name: str,
    ref: SourceArtifactRef,
    *,
    ticker: str,
    cik: str,
    valid_from: str | None = None,
    valid_to: str | None = None,
    aliases: tuple[str, ...] = (),
) -> IssuerIdentity:
    return IssuerIdentity(
        entity_id=entity_id,
        canonical_name=name,
        canonical_name_ref=ref,
        aliases=tuple(IdentityAlias(value=item, ref=ref) for item in aliases),
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


class EntityResolutionTests(unittest.TestCase):
    def test_durable_issuer_and_trader_register_with_public_evidence(self):
        sources, manifest, ref = fixture()
        registry = EntityResolutionRegistry()

        company = issuer(
            "issuer-entity:alpha",
            "Alpha Holdings, Inc.",
            ref,
            ticker="alph",
            cik="0001234567",
            aliases=("Alpha Holdings",),
        )
        person = TraderIdentity(
            entity_id="trader-entity:one",
            canonical_name="Historical Trader",
            canonical_name_ref=ref,
            aliases=(IdentityAlias("H. Trader", ref),),
        )

        registry.register_issuer(
            company,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        registry.register_trader(
            person,
            source_registry=sources,
            artifact_manifest=manifest,
        )

        self.assertEqual(
            registry.resolve_issuer_identifier(
                HistoricalIdentifierType.CIK,
                "1234567",
            ).resolved_entity_id,
            company.entity_id,
        )
        self.assertEqual(
            registry.resolve_issuer_name(" alpha   holdings ").resolved_entity_id,
            company.entity_id,
        )
        self.assertEqual(
            registry.resolve_trader_name("h. TRADER").resolved_entity_id,
            person.entity_id,
        )
        self.assertEqual(len(registry.registry_hash), 64)

    def test_historical_ticker_reuse_resolves_only_with_date_context(self):
        sources, manifest, ref = fixture()
        registry = EntityResolutionRegistry()

        old = issuer(
            "issuer-entity:old",
            "Old Ticker Owner Inc.",
            ref,
            ticker="ABC",
            cik="100001",
            valid_from="2010-01-01",
            valid_to="2015-12-31",
        )
        new = issuer(
            "issuer-entity:new",
            "New Ticker Owner Inc.",
            ref,
            ticker="ABC",
            cik="200002",
            valid_from="2016-01-01",
            valid_to=None,
        )
        for item in (old, new):
            registry.register_issuer(
                item,
                source_registry=sources,
                artifact_manifest=manifest,
            )

        first = registry.resolve_issuer_identifier(
            HistoricalIdentifierType.TICKER,
            "abc",
            as_of_date="2014-06-01",
        )
        second = registry.resolve_issuer_identifier(
            HistoricalIdentifierType.TICKER,
            "ABC",
            as_of_date="2018-06-01",
        )
        undated = registry.resolve_issuer_identifier(
            HistoricalIdentifierType.TICKER,
            "ABC",
        )

        self.assertEqual(first.state, ResolutionState.RESOLVED)
        self.assertEqual(first.resolved_entity_id, old.entity_id)
        self.assertEqual(second.resolved_entity_id, new.entity_id)
        self.assertEqual(undated.state, ResolutionState.AMBIGUOUS)
        self.assertIsNone(undated.resolved_entity_id)
        self.assertEqual(
            undated.matched_entity_ids,
            tuple(sorted((old.entity_id, new.entity_id))),
        )

    def test_shared_alias_is_ambiguous_not_silently_selected(self):
        sources, manifest, ref = fixture()
        registry = EntityResolutionRegistry()
        for entity_id, name in (
            ("trader-entity:one", "Alex One"),
            ("trader-entity:two", "Alex Two"),
        ):
            registry.register_trader(
                TraderIdentity(
                    entity_id=entity_id,
                    canonical_name=name,
                    canonical_name_ref=ref,
                    aliases=(IdentityAlias("A. Smith", ref),),
                ),
                source_registry=sources,
                artifact_manifest=manifest,
            )

        result = registry.resolve_trader_name("A. Smith")
        self.assertEqual(result.entity_kind, EntityKind.TRADER)
        self.assertEqual(result.state, ResolutionState.AMBIGUOUS)
        self.assertEqual(
            result.matched_entity_ids,
            ("trader-entity:one", "trader-entity:two"),
        )
        self.assertIsNone(result.resolved_entity_id)

    def test_unmatched_query_is_explicitly_unresolved(self):
        sources, manifest, ref = fixture()
        registry = EntityResolutionRegistry()
        registry.register_issuer(
            issuer(
                "issuer-entity:alpha",
                "Alpha Inc.",
                ref,
                ticker="AAA",
                cik="12345",
            ),
            source_registry=sources,
            artifact_manifest=manifest,
        )

        result = registry.resolve_issuer_identifier(
            HistoricalIdentifierType.TICKER,
            "ZZZ",
            as_of_date="2015-08-10",
        )
        self.assertEqual(result.state, ResolutionState.UNRESOLVED)
        self.assertEqual(result.matched_entity_ids, ())
        self.assertEqual(result.evidence_hashes, ())

    def test_discovery_only_source_cannot_establish_durable_identity(self):
        sources, manifest, ref = fixture(discovery_only=True)
        registry = EntityResolutionRegistry()
        company = issuer(
            "issuer-entity:alpha",
            "Alpha Inc.",
            ref,
            ticker="AAA",
            cik="12345",
        )

        with self.assertRaisesRegex(ValueError, "discovery-only"):
            registry.register_issuer(
                company,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_conflicting_content_cannot_overwrite_existing_entity_id(self):
        sources, manifest, ref = fixture()
        registry = EntityResolutionRegistry()
        first = issuer(
            "issuer-entity:alpha",
            "Alpha Inc.",
            ref,
            ticker="AAA",
            cik="12345",
        )
        registry.register_issuer(
            first,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        altered = issuer(
            "issuer-entity:alpha",
            "Different Alpha Inc.",
            ref,
            ticker="AAA",
            cik="12345",
        )
        with self.assertRaisesRegex(ValueError, "different content"):
            registry.register_issuer(
                altered,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_identifier_validation_and_interval_validation_fail_closed(self):
        _sources, _manifest, ref = fixture()
        with self.assertRaisesRegex(ValueError, "CIK"):
            HistoricalIdentifier(
                HistoricalIdentifierType.CIK,
                "12A45",
                ref,
            )
        with self.assertRaisesRegex(ValueError, "valid_to"):
            HistoricalIdentifier(
                HistoricalIdentifierType.TICKER,
                "ABC",
                ref,
                valid_from="2018-01-01",
                valid_to="2017-12-31",
            )

    def test_entity_proof_is_order_independent_for_aliases_and_identifiers(self):
        _sources, _manifest, ref = fixture()
        aliases = (
            IdentityAlias("Alpha Holdings", ref),
            IdentityAlias("Alpha Corp", ref),
        )
        identifiers = (
            HistoricalIdentifier(HistoricalIdentifierType.CIK, "1234567", ref),
            HistoricalIdentifier(
                HistoricalIdentifierType.TICKER,
                "ALPH",
                ref,
                valid_from="2014-01-01",
            ),
        )
        left = IssuerIdentity(
            entity_id="issuer-entity:alpha",
            canonical_name="Alpha Holdings, Inc.",
            canonical_name_ref=ref,
            aliases=aliases,
            identifiers=identifiers,
        )
        right = IssuerIdentity(
            entity_id="issuer-entity:alpha",
            canonical_name="Alpha Holdings, Inc.",
            canonical_name_ref=ref,
            aliases=tuple(reversed(aliases)),
            identifiers=tuple(reversed(identifiers)),
        )
        self.assertEqual(left.proof_hash, right.proof_hash)


if __name__ == "__main__":
    unittest.main()
