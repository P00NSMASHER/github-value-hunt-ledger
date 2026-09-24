import unittest

from historical_mnpi.case_model import CaseArtifactRole
from historical_mnpi.extractors import (
    CandidateField,
    CandidateFieldStatus,
    CandidateKind,
    CandidateRecord,
)
from historical_mnpi.review_queue import (
    ReviewDecision,
    build_review_item,
    decide_review_item,
)
from historical_mnpi.source_conflicts import (
    ConflictResolutionState,
    SourceConflictClaim,
    SourceConflictRegistry,
)
from historical_mnpi.test_review_queue import (
    all_checks,
    clean_item,
    durable_identity_context,
    fixture,
)
from historical_mnpi.transaction_model import FactStatus


def source_claim(
    claim_id,
    *,
    record,
    ref,
    value,
    status,
):
    return SourceConflictClaim(
        claim_id=claim_id,
        case_id=record.case_id,
        field_name="quantity",
        value=value,
        source_ref=ref,
        artifact_role=CaseArtifactRole.COMPLAINT,
        fact_status=status,
    )


class ReviewSourceConflictIntegrationTests(unittest.TestCase):
    def test_priority_resolves_lower_tier_candidate_conflict_without_erasing_it(self):
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
        entities, crosswalks = durable_identity_context(
            sources,
            manifest,
            cases,
            case,
            refs,
        )
        conflict_candidate = CandidateRecord(
            candidate_id="candidate:review:lower-authority-conflict",
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
            raw_excerpt="lower-authority claim says 2600",
        )

        conflict_registry = SourceConflictRegistry()
        complaint_ref = refs[CaseArtifactRole.COMPLAINT]
        for item in (
            source_claim(
                "claim:review:alleged-2500",
                record=record,
                ref=complaint_ref,
                value="2500",
                status=FactStatus.ALLEGED,
            ),
            source_claim(
                "claim:review:primary-unspecified-2600",
                record=record,
                ref=complaint_ref,
                value="2600",
                status=None,
            ),
        ):
            conflict_registry.register(
                item,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

        review = build_review_item(
            record,
            event=event,
            candidates=(candidate, conflict_candidate),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T13:10:00Z",
            created_by="review-builder",
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=conflict_registry,
        )
        self.assertNotIn("CONFLICT:quantity", review.blockers)
        self.assertFalse(review.blockers)
        self.assertEqual(len(review.source_conflicts), 1)
        assessment = review.source_conflicts[0]
        self.assertEqual(
            assessment.state,
            ConflictResolutionState.PREFERRED_VALUE_WITH_CONTRADICTIONS,
        )
        self.assertEqual(assessment.preferred_value, "2500")
        self.assertEqual(len(assessment.contradictory_claim_hashes), 1)

        decision = decide_review_item(
            review,
            decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
            checks=all_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T13:11:00Z",
            rationale="Priority policy resolves lower-authority contradiction.",
            cases=cases,
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=conflict_registry,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertTrue(decision.research_corpus_eligible)
        self.assertIsNotNone(decision.source_conflict_hash)

    def test_same_tier_source_conflict_blocks_approval(self):
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
        entities, crosswalks = durable_identity_context(
            sources,
            manifest,
            cases,
            case,
            refs,
        )
        conflict_candidate = CandidateRecord(
            candidate_id="candidate:review:top-tier-conflict",
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
            raw_excerpt="same-authority claim says 2600",
        )
        conflict_registry = SourceConflictRegistry()
        complaint_ref = refs[CaseArtifactRole.COMPLAINT]
        for item in (
            source_claim(
                "claim:review:alleged-2500",
                record=record,
                ref=complaint_ref,
                value="2500",
                status=FactStatus.ALLEGED,
            ),
            source_claim(
                "claim:review:alleged-2600",
                record=record,
                ref=complaint_ref,
                value="2600",
                status=FactStatus.ALLEGED,
            ),
        ):
            conflict_registry.register(
                item,
                cases=cases,
                source_registry=sources,
                artifact_manifest=manifest,
            )

        review = build_review_item(
            record,
            event=event,
            candidates=(candidate, conflict_candidate),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T13:10:00Z",
            created_by="review-builder",
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=conflict_registry,
        )
        self.assertIn(
            "SOURCE_CONFLICT_UNRESOLVED:quantity",
            review.blockers,
        )
        with self.assertRaisesRegex(ValueError, "blocked item"):
            decide_review_item(
                review,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T13:11:00Z",
                rationale="Unresolved same-tier contradiction.",
                cases=cases,
                entities=entities,
                entity_crosswalks=crosswalks,
                source_conflicts=conflict_registry,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_normalized_value_must_match_priority_preferred_value(self):
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
        entities, crosswalks = durable_identity_context(
            sources,
            manifest,
            cases,
            case,
            refs,
        )
        conflict_registry = SourceConflictRegistry()
        conflict_registry.register(
            source_claim(
                "claim:review:preferred-2600",
                record=record,
                ref=refs[CaseArtifactRole.COMPLAINT],
                value="2600",
                status=FactStatus.ALLEGED,
            ),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )

        review = build_review_item(
            record,
            event=event,
            candidates=(candidate,),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T13:10:00Z",
            created_by="review-builder",
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=conflict_registry,
        )
        self.assertIn(
            "SOURCE_PRIORITY_MISMATCH:quantity",
            review.blockers,
        )

    def test_new_relevant_claim_after_review_creation_invalidates_snapshot(self):
        (
            sources,
            manifest,
            cases,
            _events,
            _case,
            _event,
            record,
            _candidate,
            refs,
            entities,
            crosswalks,
            conflict_registry,
            review,
        ) = clean_item()

        conflict_registry.register(
            source_claim(
                "claim:review:late-2500",
                record=record,
                ref=refs[CaseArtifactRole.COMPLAINT],
                value="2500",
                status=FactStatus.ALLEGED,
            ),
            cases=cases,
            source_registry=sources,
            artifact_manifest=manifest,
        )

        with self.assertRaisesRegex(ValueError, "snapshot is stale or changed"):
            decide_review_item(
                review,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T13:11:00Z",
                rationale="New evidence must invalidate stale review.",
                cases=cases,
                entities=entities,
                entity_crosswalks=crosswalks,
                source_conflicts=conflict_registry,
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_approval_requires_source_conflict_snapshot(self):
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
        entities, crosswalks = durable_identity_context(
            sources,
            manifest,
            cases,
            case,
            refs,
        )
        review = build_review_item(
            record,
            event=event,
            candidates=(candidate,),
            cases=cases,
            events=events,
            source_registry=sources,
            artifact_manifest=manifest,
            created_at="2026-09-24T13:10:00Z",
            created_by="review-builder",
            entities=entities,
            entity_crosswalks=crosswalks,
        )
        self.assertIsNone(review.source_conflict_registry_hash)
        with self.assertRaisesRegex(ValueError, "source-conflict snapshot"):
            decide_review_item(
                review,
                decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
                checks=all_checks(),
                reviewer_id="reviewer:1",
                reviewed_at="2026-09-24T13:11:00Z",
                rationale="Missing conflict snapshot must fail closed.",
                cases=cases,
                entities=entities,
                entity_crosswalks=crosswalks,
                source_conflicts=SourceConflictRegistry(),
                source_registry=sources,
                artifact_manifest=manifest,
            )

    def test_empty_current_registry_is_still_bound_into_approval(self):
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
            conflict_registry,
            review,
        ) = clean_item()
        decision = decide_review_item(
            review,
            decision=ReviewDecision.APPROVED_FOR_HISTORICAL_RESEARCH,
            checks=all_checks(),
            reviewer_id="reviewer:1",
            reviewed_at="2026-09-24T13:11:00Z",
            rationale="No registered relevant contradictions.",
            cases=cases,
            entities=entities,
            entity_crosswalks=crosswalks,
            source_conflicts=conflict_registry,
            source_registry=sources,
            artifact_manifest=manifest,
        )
        self.assertIsNotNone(review.source_conflict_registry_hash)
        self.assertEqual(review.source_conflicts, ())
        self.assertIsNotNone(decision.source_conflict_hash)
        decision.verify_integrity()


if __name__ == "__main__":
    unittest.main()
