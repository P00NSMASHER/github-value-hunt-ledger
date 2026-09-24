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
    IssuerIdentity,
    TraderIdentity,
)
from historical_mnpi.event_model import EventRegistry, InformationEvent, TemporalBoundary
from historical_mnpi.extractors import (
    CandidateField,
    CandidateFieldStatus,
    CandidateKind,
    CandidateRecord,
)
from historical_mnpi.raw_artifacts import (
    LocalContentAddressedArtifactStore,
    SourceArtifactRef,
    SourceLocatorKind,
    freeze_raw_artifact_manifest,
)
from historical_mnpi.review_queue import (
    HistoricalReviewQueue,
    ReviewChecks,
    ReviewDecision,
    build_review_item,
    decide_review_item,
    render_review_item_markdown,
)
from historical_mnpi.source_conflicts import (
    SourceConflictClaim,
    SourceConflictRegistry,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility,
    SourceRecord,
    SourceRegistry,
    SourceType,
)
from historical_mnpi.transaction_model import (
    FactStatus,
    HistoricalTransaction,
    InstrumentType,
    TradeSide,
)


def H(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def subref(base: SourceArtifactRef, locator: str, excerpt: str) -> SourceArtifactRef:
    return SourceArtifactRef(
        source_id=base.source_id,
        source_proof_hash=base.source_proof_hash,
        artifact_id=base.artifact_id,
        artifact_sha256=base.artifact_sha256,
        artifact_record_proof_hash=base.artifact_record_proof_hash,
        locator_kind=SourceLocatorKind.TABLE,
        locator=locator,
        excerpt_sha256=H(excerpt.encode("utf-8")),
    )


def fixture():
    complaint_raw = b"historical public complaint"
    release_raw = b"historical public acquisition announcement"

    complaint = SourceRecord(
        source_id="SEC:REVIEW:001",
        source_type=SourceType.SEC_COMPLAINT,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="SEC",
        title="Historical complaint",
        url="https://www.sec.gov/review-example.pdf",
        publication_date="2015-08-11",
        sha256=H(complaint_raw),
        retrieved_at="2026-09-24T12:00:00Z",
        public_release_confirmed=True,
        case_id="CASE-REVIEW",
    )
    release = SourceRecord(
        source_id="ISSUER:REVIEW:001",
        source_type=SourceType.PUBLIC_PRESS_RELEASE,
        admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
        publisher="Target Corp.",
        title="Public announcement",
        url="https://example.com/review-release.html",
        publication_date="2015-08-10",
        sha256=H(release_raw),
        retrieved_at="2026-09-24T12:00:00Z",
        public_release_confirmed=True,
        case_id="CASE-REVIEW",
    )
    sources = SourceRegistry()
    sources.register(complaint)
    sources.register(release)

    refs = {}
    artifacts = []
    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        for source, raw, role, media_type in (
            (
                complaint,
                complaint_raw,
                CaseArtifactRole.COMPLAINT,
                "application/pdf",
            ),
            (
                release,
                release_raw,
                CaseArtifactRole.PUBLIC_RELEASE,
                "text/html",
            ),
        ):
            artifact = store.retain(
                sources,
                source,
                raw,
                media_type=media_type,
                acquired_at="2026-09-24T12:00:00Z",
                stored_at="2026-09-24T12:01:00Z",
            )
            artifacts.append(artifact)
            refs[role] = SourceArtifactRef(
                source_id=source.source_id,
                source_proof_hash=source.proof_hash,
                artifact_id=artifact.artifact_id,
                artifact_sha256=artifact.sha256,
                artifact_record_proof_hash=artifact.proof_hash,
                locator_kind=SourceLocatorKind.OTHER,
                locator="document-root",
            )

        manifest = freeze_raw_artifact_manifest(
            sources,
            tuple(artifacts),
            created_at="2026-09-24T12:02:00Z",
            created_by="test",
        )

    case = HistoricalCase(
        case_id="CASE-REVIEW",
        title="Historical review matter",
        event_type=CaseEventType.MERGER_ACQUISITION,
        information_origin="confidential acquisition information",
        proceeding_status=CaseProceedingStatus.SETTLED,
        parties=(
            CaseParty(
                party_id="party:review:trader",
                display_name="Historical Trader",
                roles=(CasePartyRole.TRADER, CasePartyRole.DEFENDANT),
            ),
        ),
        issuers=(
            CaseIssuer(
                issuer_id="issuer:review:target",
                legal_name="Target Corp.",
                cik="123456",
                ticker_at_case="TGT",
            ),
        ),
        artifacts=(
            CaseArtifactLink(
                CaseArtifactRole.COMPLAINT,
                refs[CaseArtifactRole.COMPLAINT],
            ),
            CaseArtifactLink(
                CaseArtifactRole.PUBLIC_RELEASE,
                refs[CaseArtifactRole.PUBLIC_RELEASE],
            ),
        ),
    )
    cases = CaseRegistry()
    cases.register(
        case,
        source_registry=sources,
        artifact_manifest=manifest,
    )

    event = InformationEvent(
        event_id="event:review:001",
        case_id=case.case_id,
        case_proof_hash=case.proof_hash,
        event_type=CaseEventType.MERGER_ACQUISITION,
        issuer_ids=("issuer:review:target",),
        information_summary="Historical acquisition announcement",
        public_release=TemporalBoundary(
            ref=refs[CaseArtifactRole.PUBLIC_RELEASE],
            timestamp="2015-08-10T16:00:00-04:00",
        ),
        private_information_start=TemporalBoundary(
            ref=refs[CaseArtifactRole.COMPLAINT],
            date_value="2015-08-01",
        ),
    )
    events = EventRegistry()
    events.register(
        event,
        cases=cases,
        source_registry=sources,
        artifact_manifest=manifest,
    )

    record = HistoricalTransaction(
        trade_id="trade:review:001",
        case_id=case.case_id,
        case_proof_hash=case.proof_hash,
        trader_party_id="party:review:trader",
        issuer_id="issuer:review:target",
        source_ref=refs[CaseArtifactRole.COMPLAINT],
        fact_status=FactStatus.ALLEGED,
        status_ref=refs[CaseArtifactRole.COMPLAINT],
        instrument_type=InstrumentType.STOCK,
        side=TradeSide.BUY,
        trade_date="2015-08-10",
        quantity="2500",
        execution_price="30.375",
    )

    excerpt = "2015-08-10 | 2,500 shares | $30.375"
    candidate_ref = subref(
        refs[CaseArtifactRole.COMPLAINT],
        "page=4;table=1;row=2",
        excerpt,
    )
    candidate = CandidateRecord(
        candidate_id="candidate:review:001",
        extractor_id="test-extractor",
        extractor_version="2",
        kind=CandidateKind.TRANSACTION,
        source_ref=candidate_ref,
        case_id=case.case_id,
        fields=(
            CandidateField(
                "trade_date",
                "2015-08-10",
                "2015-08-10",
                CandidateFieldStatus.EXACT_TEXT_PARSE,
            ),
            CandidateField(
                "quantity",
                "2,500",
                "2500",
                CandidateFieldStatus.EXACT_TEXT_PARSE,
            ),
            CandidateField(
                "execution_price",
                "30.375",
                "30.375",
                CandidateFieldStatus.EXACT_TEXT_PARSE,
            ),
            CandidateField(
                "instrument_type",
                "STOCK",
                "STOCK",
                CandidateFieldStatus.EXACT_TEXT_PARSE,
            ),
            CandidateField(
                "side",
                "BUY",
                "BUY",
                CandidateFieldStatus.EXACT_TEXT_PARSE,
            ),
        ),
        raw_excerpt=excerpt,
    )

    return (
        sources,
        manifest,
        cases,
        events,
        case,
        event,
        record,
        candidate,
        refs,
    )


def durable_identity_context(sources, manifest, cases, case, refs):
    ref = refs[CaseArtifactRole.COMPLAINT]
    entities = EntityResolutionRegistry()
    issuer = IssuerIdentity(
        entity_id="issuer-entity:review-target",
        canonical_name="Target Corp.",
        canonical_name_ref=ref,
        identifiers=(
            HistoricalIdentifier(
                HistoricalIdentifierType.CIK,
                "123456",
                ref,
            ),
            HistoricalIdentifier(
                HistoricalIdentifierType.TICKER,
                "TGT",
                ref,
                valid_from="2010-01-01",
            ),
        ),
    )
    trader = TraderIdentity(
        entity_id="trader-entity:review-trader",
        canonical_name="Historical Trader",
        canonical_name_ref=ref,
    )
    entities.register_issuer(
        issuer,
        source_registry=sources,
        artifact_manifest=manifest,
    )
    entities.register_trader(
        trader,
        source_registry=sources,
        artifact_manifest=manifest,
    )

    crosswalks = CaseEntityCrosswalkRegistry()
    issuer_result = entities.resolve_issuer_identifier(
        HistoricalIdentifierType.CIK,
        "123456",
    )
    trader_result = entities.resolve_trader_name("Historical Trader")
    crosswalks.register(
        CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.ISSUER,
            local_id="issuer:review:target",
            durable_entity_id=issuer.entity_id,
            durable_entity_proof_hash=issuer.proof_hash,
            resolution=issuer_result,
        ),
        cases=cases,
        entities=entities,
    )
    crosswalks.register(
        CaseEntityCrosswalk(
            case_id=case.case_id,
            case_proof_hash=case.proof_hash,
            entity_kind=EntityKind.TRADER,
            local_id="party:review:trader",
            durable_entity_id=trader.entity_id,
            durable_entity_proof_hash=trader.proof_hash,
            resolution=trader_result,
        ),
        cases=cases,
        entities=entities,
    )
    return entities, crosswalks


def clean_item():
    sources, manifest, cases, events, case, event, record, candidate, refs = fixture()
    entities, crosswalks = durable_identity_context(
        sources,
        manifest,
        cases,
        case,
        refs,
    )
    source_conflicts = SourceConflictRegistry()
    item = build_review_item(
        record,
        event=event,
        candidates=(candidate,),
        cases=cases,
        events=events,
        source_registry=sources,
        artifact_manifest=manifest,
        created_at="2026-09-24T12:03:00Z",
        created_by="review-builder",
        entities=entities,
        entity_crosswalks=crosswalks,
        source_conflicts=source_conflicts,
    )
    return (
        sources,
        manifest,
        cases,
        events,
        case,
        event,
        record,
        candidate,
        refs,
        entities,
        crosswalks,
        source_conflicts,
        item,
    )


def all_checks() -> ReviewChecks:
    return ReviewChecks(
        source_evidence_checked=True,
        identity_checked=True,
        temporal_precision_checked=True,
        legal_status_checked=True,
        conflicts_resolved=True,
    )


class ReviewQueueTests(unittest.TestCase):
    def test_clean_item_accepts_candidate_sublocator_and_binds_row_hash(self):
        *_, record, candidate, _refs, _entities, _crosswalks, _source_conflicts, item = clean_item()
        self.assertNotEqual(
            candidate.source_ref.proof_hash,
            record.source_ref.proof_hash,
        )
        self.assertEqual(item.normalized_row_hash, record.proof_hash)
        self.assertFalse(item.blockers)
        self.assertFalse(item.live_trading_allowed)
        self.assertEqual(item.temporal.trade_date, "2015-08-10")
        report = render_review_item_markdown(item)
        self.assertIn(candidate.raw_excerpt, report)
        self.assertIn(record.proof_hash, report)
        self.assertIn("Trade date: **2015-08-10**", report)
        self.assertIn("Fact status: **ALLEGED**", report)
        self.assertIn("Live trading allowed: **no**", report)

    def test_approval_requires_explicit_human_checks(self):
        *_, item = clean_item()
        incomplete = ReviewChecks(
            source_evidence_checked=True,
            identity_checked=True,
            temporal_precision_checked=True,
            legal_status_checked=False,
            conflicts_resolved=True,
        )
        with self.assertRaisesRegex(ValueError, "all reviewer checks"):
            decide_review_item(
                item,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=incomplete,
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T12:04:00Z",
                rationale="Incomplete review.",
            )

    def test_explicit_historical_research_approval_is_hash_bound(self):
        (
            sources,
            manifest,
            cases,
            _events,
            _case,
            _event,
            record,
            _candidate,
            _refs,
            entities,
            crosswalks,
            source_conflicts,
            item,
        ) = clean_item()
        decision = decide_review_item(
            item,
            decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
            checks=all_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T12:04:00Z",
            rationale="Historical public-record row verified.",
            cases=cases,
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=source_conflicts,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        decision.verify_integrity()
        self.assertTrue(decision.research_corpus_eligible)
        self.assertFalse(decision.live_trading_allowed)
        self.assertEqual(decision.normalized_row_hash, record.proof_hash)

    def test_review_decision_cannot_predate_item(self):
        *_, item = clean_item()
        with self.assertRaisesRegex(ValueError, "predate"):
            decide_review_item(
                item,
                decision=ReviewDecision.REJECTED,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T12:02:00Z",
                rationale="Rejected.",
            )

    def test_conflict_creates_blocker_and_prevents_approval(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            record,
            candidate,
            _refs,
        ) = fixture()
        conflict = CandidateRecord(
            candidate_id="candidate:review:002",
            extractor_id="second-parser",
            extractor_version="2",
            kind=CandidateKind.TRANSACTION,
            source_ref=candidate.source_ref,
            case_id=case.case_id,
            fields=(
                CandidateField(
                    "quantity",
                    "2600",
                    "2600",
                    CandidateFieldStatus.EXACT_TEXT_PARSE,
                ),
            ),
            raw_excerpt="second parse says 2600",
        )
        item = build_review_item(
            record,
            event=event,
            candidates=(candidate, conflict),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T12:03:00Z",
            created_by="review-builder",
        )
        self.assertIn("CONFLICT:quantity", item.blockers)
        with self.assertRaisesRegex(ValueError, "blocked item"):
            decide_review_item(
                item,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T12:04:00Z",
                rationale="Unresolved conflict.",
            )

    def test_unparsed_field_is_blocker(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            record,
            candidate,
            _refs,
        ) = fixture()
        unparsed = CandidateRecord(
            candidate_id="candidate:review:unparsed",
            extractor_id="parser",
            extractor_version="2",
            kind=CandidateKind.TRANSACTION,
            source_ref=candidate.source_ref,
            case_id=case.case_id,
            fields=(
                CandidateField(
                    "quantity",
                    "",
                    None,
                    CandidateFieldStatus.UNPARSED,
                ),
            ),
            raw_excerpt="quantity not parseable",
        )
        item = build_review_item(
            record,
            event=event,
            candidates=(candidate, unparsed),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T12:03:00Z",
            created_by="review-builder",
        )
        self.assertTrue(any(
            blocker.startswith("UNPARSED_FIELD:")
            for blocker in item.blockers
        ))

    def test_pdf_text_warning_requires_corroboration(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            record,
            candidate,
            _refs,
        ) = fixture()
        warned = CandidateRecord(
            candidate_id="candidate:review:pdf",
            extractor_id="pdf-text",
            extractor_version="2",
            kind=CandidateKind.TRANSACTION,
            source_ref=candidate.source_ref,
            case_id=case.case_id,
            fields=candidate.fields,
            raw_excerpt=candidate.raw_excerpt,
            warnings=("PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION",),
        )
        item = build_review_item(
            record,
            event=event,
            candidates=(warned,),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T12:03:00Z",
            created_by="review-builder",
        )
        self.assertTrue(any(
            blocker.startswith("RAW_VISUAL_VERIFICATION_REQUIRED")
            for blocker in item.blockers
        ))

    def test_candidate_artifact_must_be_linked_to_case(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            record,
            _candidate,
            refs,
        ) = fixture()
        wrong_ref = subref(
            refs[CaseArtifactRole.PUBLIC_RELEASE],
            "paragraph=1",
            "wrong source",
        )
        wrong = CandidateRecord(
            candidate_id="candidate:wrong",
            extractor_id="test",
            extractor_version="2",
            kind=CandidateKind.TRANSACTION,
            source_ref=wrong_ref,
            case_id=case.case_id,
            fields=(
                CandidateField(
                    "trade_date",
                    "2015-08-10",
                    "2015-08-10",
                    CandidateFieldStatus.EXACT_TEXT_PARSE,
                ),
            ),
            raw_excerpt="wrong source",
        )
        with self.assertRaisesRegex(
            ValueError,
            "transaction source artifact is not represented",
        ):
            build_review_item(
                record,
                event=event,
                candidates=(wrong,),
                cases=cases,
                events=events,
                source_registry=sources,
                artifact_manifest=manifest,
                created_at="2026-09-24T12:03:00Z",
                created_by="review-builder",
            )

    def test_status_source_artifact_must_be_represented(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            record,
            candidate,
            refs,
        ) = fixture()

        # The candidate uses the complaint artifact, which represents both source
        # and status for the ALLEGED fixture, so the clean item succeeds.
        clean = build_review_item(
            record,
            event=event,
            candidates=(candidate,),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T12:03:00Z",
            created_by="review-builder",
        )
        self.assertFalse(clean.blockers)

    def test_proposed_value_without_candidate_support_is_blocked(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            record,
            candidate,
            _refs,
        ) = fixture()
        unsupported = HistoricalTransaction(
            trade_id="trade:review:unsupported",
            case_id=record.case_id,
            case_proof_hash=record.case_proof_hash,
            trader_party_id=record.trader_party_id,
            issuer_id=record.issuer_id,
            source_ref=record.source_ref,
            fact_status=record.fact_status,
            status_ref=record.status_ref,
            instrument_type=record.instrument_type,
            side=record.side,
            trade_date=record.trade_date,
            quantity="9999",
            execution_price=record.execution_price,
        )
        item = build_review_item(
            unsupported,
            event=event,
            candidates=(candidate,),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T12:03:00Z",
            created_by="review-builder",
        )
        self.assertIn(
            "PROPOSED_VALUE_UNSUPPORTED:quantity",
            item.blockers,
        )
        with self.assertRaisesRegex(ValueError, "blocked item"):
            decide_review_item(
                item,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T12:04:00Z",
                rationale="Unsupported normalized value.",
            )

    def test_mmddyyyy_candidate_date_can_support_iso_normalized_date(self):
        (
            sources,
            manifest,
            cases,
            events,
            case,
            event,
            record,
            candidate,
            _refs,
        ) = fixture()
        converted = CandidateRecord(
            candidate_id="candidate:review:date-normalized",
            extractor_id="test-extractor",
            extractor_version="2",
            kind=CandidateKind.TRANSACTION,
            source_ref=candidate.source_ref,
            case_id=case.case_id,
            fields=tuple(
                CandidateField(
                    field.name,
                    "08/10/2015",
                    "08/10/2015",
                    field.status,
                )
                if field.name == "trade_date"
                else field
                for field in candidate.fields
            ),
            raw_excerpt="08/10/2015 | 2,500 shares | $30.375",
        )
        item = build_review_item(
            record,
            event=event,
            candidates=(converted,),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T12:03:00Z",
            created_by="review-builder",
        )
        self.assertNotIn(
            "PROPOSED_VALUE_UNSUPPORTED:trade_date",
            item.blockers,
        )

    def test_append_only_queue_prevents_second_decision(self):
        (
            sources,
            manifest,
            cases,
            _events,
            _case,
            _event,
            _record,
            _candidate,
            _refs,
            entities,
            crosswalks,
            source_conflicts,
            item,
        ) = clean_item()
        queue = HistoricalReviewQueue()
        queue.enqueue(item)
        before = queue.queue_hash
        first = queue.decide(
            item.review_id,
            decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
            checks=all_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T12:04:00Z",
            rationale="Verified.",
            cases=cases,
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=source_conflicts,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertNotEqual(queue.queue_hash, before)
        self.assertEqual(
            queue.approved_normalized_row_hashes(),
            (item.normalized_row_hash,),
        )
        with self.assertRaisesRegex(ValueError, "already has"):
            queue.decide(
                item.review_id,
                decision=ReviewDecision.REJECTED,
                checks=all_checks(),
                reviewer_id="reviewer:2",
                reviewed_at="2026-09-24T12:05:00Z",
                rationale="Second decision must not overwrite.",
            )
        self.assertEqual(
            queue.approved_normalized_row_hashes(),
            (first.normalized_row_hash,),
        )


    def test_approval_requires_durable_identity_snapshot(self):
        (
            sources,
            manifest,
            cases,
            events,
            _case,
            event,
            record,
            candidate,
            _refs,
        ) = fixture()
        item = build_review_item(
            record,
            event=event,
            candidates=(candidate,),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T12:03:00Z",
            created_by="review-builder",
        )
        self.assertIsNone(item.durable_identity)
        with self.assertRaisesRegex(ValueError, "durable identity crosswalks"):
            decide_review_item(
                item,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T12:04:00Z",
                rationale="Identity context missing.",
            )

    def test_approval_rejects_crosswalk_that_became_ambiguous(self):
        (
            sources,
            manifest,
            cases,
            _events,
            _case,
            _event,
            _record,
            _candidate,
            refs,
            entities,
            crosswalks,
            _source_conflicts,
            item,
        ) = clean_item()
        ref = refs[CaseArtifactRole.COMPLAINT]
        duplicate = IssuerIdentity(
            entity_id="issuer-entity:duplicate-target",
            canonical_name="Duplicate Historical Target",
            canonical_name_ref=ref,
            identifiers=(
                HistoricalIdentifier(
                    HistoricalIdentifierType.CIK,
                    "123456",
                    ref,
                ),
            ),
        )
        entities.register_issuer(
            duplicate,
            source_registry=sources,
            artifact_manifest=manifest,
        )

        with self.assertRaisesRegex(
            ValueError,
            "resolution proof does not recompute|no longer unique",
        ):
            decide_review_item(
                item,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T12:04:00Z",
                rationale="Stale identity must fail closed.",
                cases=cases,
                entities=entities,
                entity_crosswalks=crosswalks,
            )

    def test_approved_decision_binds_durable_identity_hash(self):
        (
            sources,
            manifest,
            cases,
            _events,
            _case,
            _event,
            _record,
            _candidate,
            _refs,
            entities,
            crosswalks,
            source_conflicts,
            item,
        ) = clean_item()
        decision = decide_review_item(
            item,
            decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
            checks=all_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T12:04:00Z",
            rationale="Durable identities verified.",
            cases=cases,
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=source_conflicts,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertEqual(
            decision.durable_identity_hash,
            item.durable_identity.proof_hash,
        )
        decision.verify_integrity()

    def test_rejected_item_is_not_research_eligible(self):
        *_, item = clean_item()
        decision = decide_review_item(
            item,
            decision=ReviewDecision.REJECTED,
            checks=ReviewChecks(
                source_evidence_checked=True,
                identity_checked=False,
                temporal_precision_checked=False,
                legal_status_checked=False,
                conflicts_resolved=False,
            ),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T12:04:00Z",
            rationale="Source does not establish proposed value.",
        )
        self.assertFalse(decision.research_corpus_eligible)


if __name__ == "__main__":
    unittest.main()
