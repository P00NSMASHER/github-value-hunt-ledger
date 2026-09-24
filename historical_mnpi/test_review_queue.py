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
    ReviewDecision,
    build_review_item,
    decide_review_item,
    render_review_item_markdown,
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


def fixture():
    complaint_raw = b"2015-08-10 purchased 2500 shares at 30.375"
    release_raw = b"public acquisition announcement"
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
        for source, raw, role in (
            (complaint, complaint_raw, CaseArtifactRole.COMPLAINT),
            (release, release_raw, CaseArtifactRole.PUBLIC_RELEASE),
        ):
            artifact = store.retain(
                sources,
                source,
                raw,
                media_type="application/pdf" if role is CaseArtifactRole.COMPLAINT else "text/html",
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
                locator_kind=SourceLocatorKind.TEXT_RANGE,
                locator="chars=0-47" if role is CaseArtifactRole.COMPLAINT else "chars=0-31",
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
            CaseArtifactLink(CaseArtifactRole.COMPLAINT, refs[CaseArtifactRole.COMPLAINT]),
            CaseArtifactLink(CaseArtifactRole.PUBLIC_RELEASE, refs[CaseArtifactRole.PUBLIC_RELEASE]),
        ),
    )
    cases = CaseRegistry()
    cases.register(case, source_registry=sources, artifact_manifest=manifest)

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
    candidate = CandidateRecord(
        candidate_id="candidate:review:001",
        extractor_id="test-extractor",
        extractor_version="1",
        kind=CandidateKind.TRANSACTION,
        source_ref=refs[CaseArtifactRole.COMPLAINT],
        case_id=case.case_id,
        fields=(
            CandidateField("trade_date", "2015-08-10", "2015-08-10", CandidateFieldStatus.EXACT_TEXT_PARSE),
            CandidateField("quantity", "2500", "2500", CandidateFieldStatus.EXACT_TEXT_PARSE),
            CandidateField("execution_price", "30.375", "30.375", CandidateFieldStatus.EXACT_TEXT_PARSE),
        ),
        raw_excerpt="2015-08-10 purchased 2500 shares at 30.375",
    )
    return sources, manifest, cases, events, case, event, record, candidate


def build_clean():
    sources, manifest, cases, events, case, event, record, candidate = fixture()
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
    return sources, manifest, cases, events, case, event, record, candidate, item


class ReviewQueueTests(unittest.TestCase):
    def test_clean_item_contains_identity_excerpt_and_row_hash(self):
        *_, record, candidate, item = build_clean()
        self.assertEqual(item.normalized_row_hash, record.proof_hash)
        self.assertFalse(item.blockers)
        self.assertFalse(item.live_trading_allowed)
        report = render_review_item_markdown(item)
        self.assertIn(candidate.raw_excerpt, report)
        self.assertIn(record.proof_hash, report)
        self.assertIn("Live trading allowed: **no**", report)

    def test_explicit_historical_research_approval_is_hash_bound(self):
        *_, item = build_clean()
        decision = decide_review_item(
            item,
            decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T12:04:00Z",
            rationale="Historical public-record row verified.",
        )
        decision.verify_integrity()
        self.assertTrue(decision.research_corpus_eligible)
        self.assertFalse(decision.live_trading_allowed)

    def test_rejected_item_is_not_research_eligible(self):
        *_, item = build_clean()
        decision = decide_review_item(
            item,
            decision=ReviewDecision.REJECTED,
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T12:04:00Z",
            rationale="Source does not establish proposed value.",
        )
        self.assertFalse(decision.research_corpus_eligible)

    def test_conflict_creates_blocker_and_prevents_approval(self):
        sources, manifest, cases, events, case, event, record, candidate = fixture()
        conflict = CandidateRecord(
            candidate_id="candidate:review:002",
            extractor_id="second-parser",
            extractor_version="1",
            kind=CandidateKind.TRANSACTION,
            source_ref=candidate.source_ref,
            case_id=case.case_id,
            fields=(
                CandidateField("quantity", "2600", "2600", CandidateFieldStatus.EXACT_TEXT_PARSE),
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
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T12:04:00Z",
                rationale="Unresolved conflict.",
            )

    def test_pdf_text_warning_requires_corroboration(self):
        sources, manifest, cases, events, case, event, record, candidate = fixture()
        warned = CandidateRecord(
            candidate_id="candidate:review:pdf",
            extractor_id="pdf-text",
            extractor_version="1",
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
        self.assertTrue(any(x.startswith("RAW_VISUAL_VERIFICATION_REQUIRED") for x in item.blockers))

    def test_candidate_source_must_match_normalized_source(self):
        sources, manifest, cases, events, case, event, record, _candidate = fixture()
        wrong = CandidateRecord(
            candidate_id="candidate:wrong",
            extractor_id="test",
            extractor_version="1",
            kind=CandidateKind.TRANSACTION,
            source_ref=event.public_release.ref,
            case_id=case.case_id,
            fields=(
                CandidateField("trade_date", "2015-08-10", "2015-08-10", CandidateFieldStatus.EXACT_TEXT_PARSE),
            ),
            raw_excerpt="wrong source",
        )
        with self.assertRaisesRegex(ValueError, "not represented"):
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


if __name__ == "__main__":
    unittest.main()
