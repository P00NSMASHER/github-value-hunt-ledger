from recoveryworks.test_support import source_hash as H
import unittest

from recoveryworks import FindingState, RecoveryEngine
from recoveryworks.branches.construction import (
    CausationReview,
    ConstructionEntitlement,
    ConstructionEvent,
    ConstructionSettlement,
    EventActivityMapping,
    ScheduleActivity,
    ScheduleRelationship,
    ScheduleVersion,
    audit_construction_recovery,
    calculate_cpm,
)


def schedule(version_id, data_date, *, b_duration, verified=True, extra_branch=False):
    activities = [
        ScheduleActivity("A", "Start work", 5),
        ScheduleActivity("B", "Mapped critical work", b_duration),
    ]
    relationships = [ScheduleRelationship("A", "B")]
    if extra_branch:
        activities.extend([
            ScheduleActivity("C", "Other path", 5),
            ScheduleActivity("D", "Other finish", 10),
        ])
        relationships.append(ScheduleRelationship("C", "D"))
    return ScheduleVersion(
        version_id=version_id,
        project_id="PRJ-1",
        data_date=data_date,
        activities=tuple(activities),
        relationships=tuple(relationships),
        source_hash=H(f"schedule-{version_id}"),
        source_locator=f"file://schedule.json#{version_id}",
        verified=verified,
        label=version_id,
    )


def entitlement(*, verified=True, amount=10_000_000, claimant="client-1"):
    return ConstructionEntitlement(
        entitlement_id="ENT-1",
        claimant_id=claimant,
        project_id="PRJ-1",
        counterparty_id="Owner-1",
        change_id="CO-7",
        event_id="EV-1",
        entitled_cents=amount,
        effective_date="2026-08-10",
        entitlement_basis="Reviewed contract clause 7.4 + priced change order",
        source_hash=H("entitlement-hash"),
        source_locator="file://entitlements.csv#row=2",
        verified=verified,
        entitlement_reviewer_id="contract-reviewer-1" if verified else None,
    )


def event(*, verified=True):
    return ConstructionEvent(
        event_id="EV-1",
        project_id="PRJ-1",
        event_date="2026-08-05",
        description="Owner-directed access restriction",
        source_hash=H("event-hash"),
        source_locator="file://events.csv#row=2",
        verified=verified,
    )


def mapping(*, verified=True, baseline_activity="B", update_activity="B"):
    return EventActivityMapping(
        mapping_id="MAP-1",
        event_id="EV-1",
        baseline_activity_id=baseline_activity,
        update_activity_id=update_activity,
        mapping_basis="RFI/daily report references mapped schedule activity",
        source_hash=H("mapping-hash"),
        source_locator="file://mappings.csv#row=2",
        verified=verified,
    )


def review(*, verified=True, accepted=True, days=3):
    return CausationReview(
        review_id="REV-1",
        entitlement_id="ENT-1",
        event_id="EV-1",
        baseline_version_id="BASE",
        update_version_id="UPD",
        accepted_causation=accepted,
        accepted_delay_days=days if accepted else 0,
        review_date="2026-09-15",
        source_hash=H("review-hash"),
        source_locator="file://causation.csv#row=2",
        verified=verified,
        qualified_reviewer_id="scheduler-1" if verified else None,
        qualification_basis="Forensic scheduler / P6 delay analyst" if verified else None,
    )


def settlement(*, verified=True, amount=2_000_000):
    return ConstructionSettlement(
        settlement_id="PAY-1",
        entitlement_id="ENT-1",
        amount_received_cents=amount,
        settlement_date="2026-09-20",
        source_hash=H("settlement-hash"),
        source_locator="file://settlements.csv#row=2",
        verified=verified,
    )


def batch(**overrides):
    params = {
        "client_id": "client-1",
        "entitlements": (entitlement(),),
        "events": (event(),),
        "mappings": (mapping(),),
        "schedules": (
            schedule("BASE", "2026-08-01", b_duration=5),
            schedule("UPD", "2026-09-01", b_duration=8),
        ),
        "causation_reviews": (review(),),
        "settlements": (settlement(),),
    }
    params.update(overrides)
    return audit_construction_recovery(**params)


class ConstructionBranchTests(unittest.TestCase):
    def test_cpm_calculates_project_duration_float_and_critical_path(self):
        result = calculate_cpm(schedule("BASE", "2026-08-01", b_duration=5))
        self.assertEqual(result.project_duration_days, 10)
        self.assertEqual(result.activities["A"].earliest_finish, 5)
        self.assertEqual(result.activities["B"].earliest_finish, 10)
        self.assertTrue(result.activities["A"].critical)
        self.assertTrue(result.activities["B"].critical)
        self.assertEqual(result.critical_activity_ids, ("A", "B"))

    def test_cpm_cycle_fails_closed(self):
        version = ScheduleVersion(
            version_id="CYCLE",
            project_id="PRJ-1",
            data_date="2026-08-01",
            activities=(
                ScheduleActivity("A", "A", 1),
                ScheduleActivity("B", "B", 1),
            ),
            relationships=(
                ScheduleRelationship("A", "B"),
                ScheduleRelationship("B", "A"),
            ),
            source_hash=H("h"),
            source_locator="file://cycle.json",
            verified=True,
        )
        with self.assertRaises(ValueError):
            calculate_cpm(version)

    def test_verified_entitlement_cpm_and_causation_produce_validated_underpayment(self):
        result = batch()
        self.assertEqual(result.exceptions, ())
        self.assertEqual(len(result.observations), 1)
        finding = RecoveryEngine().evaluate(result.observations[0])
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.expected_cents, 10_000_000)
        self.assertEqual(finding.actual_cents, 2_000_000)
        self.assertEqual(finding.potential_recovery_cents, 8_000_000)
        self.assertEqual(finding.metadata["cpm_project_delay_days"], 3)
        self.assertEqual(finding.metadata["mapped_activity_finish_delay_days"], 3)
        self.assertEqual(finding.metadata["accepted_delay_days"], 3)
        self.assertEqual(finding.metadata["qualified_reviewer_id"], "scheduler-1")
        self.assertEqual(len(finding.evidence), 6)

    def test_unverified_causation_review_keeps_candidate_in_review(self):
        result = batch(causation_reviews=(review(verified=False),))
        finding = RecoveryEngine().evaluate(result.observations[0])
        self.assertIs(finding.state, FindingState.REVIEW)

    def test_no_settlement_evidence_fails_closed(self):
        result = batch(settlements=())
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, "NO_SETTLEMENT_EVIDENCE")

    def test_accepted_delay_cannot_exceed_cpm_project_impact(self):
        result = batch(causation_reviews=(review(days=4),))
        self.assertEqual(result.observations, ())
        self.assertEqual(
            result.exceptions[0].code,
            "ACCEPTED_DELAY_EXCEEDS_CPM_IMPACT",
        )

    def test_mapped_activity_must_show_delay(self):
        baseline = schedule(
            "BASE",
            "2026-08-01",
            b_duration=5,
            extra_branch=True,
        )
        update = ScheduleVersion(
            version_id="UPD",
            project_id="PRJ-1",
            data_date="2026-09-01",
            activities=(
                ScheduleActivity("A", "Start work", 5),
                ScheduleActivity("B", "Mapped unchanged work", 5),
                ScheduleActivity("C", "Other path", 5),
                ScheduleActivity("D", "Other delayed finish", 13),
            ),
            relationships=(
                ScheduleRelationship("A", "B"),
                ScheduleRelationship("C", "D"),
            ),
            source_hash=H("schedule-UPD"),
            source_locator="file://schedule.json#UPD",
            verified=True,
        )
        result = batch(schedules=(baseline, update))
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, "MAPPED_ACTIVITY_NO_DELAY")

    def test_missing_mapped_activity_fails_closed(self):
        result = batch(mappings=(mapping(update_activity="NOPE"),))
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, "MAPPED_ACTIVITY_MISSING")

    def test_rejected_causation_creates_no_recovery(self):
        result = batch(causation_reviews=(review(accepted=False),))
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, "CAUSATION_NOT_ACCEPTED")

    def test_claimant_scope_mismatch_is_not_recovery(self):
        result = batch(entitlements=(entitlement(claimant="other-client"),))
        self.assertEqual(result.observations, ())
        self.assertEqual(result.exceptions[0].code, "CLAIMANT_SCOPE_MISMATCH")

    def test_verified_entitlement_requires_reviewer(self):
        with self.assertRaises(ValueError):
            ConstructionEntitlement(
                entitlement_id="ENT",
                claimant_id="client-1",
                project_id="PRJ-1",
                counterparty_id="Owner",
                change_id="CO",
                event_id="EV",
                entitled_cents=100,
                effective_date="2026-08-01",
                entitlement_basis="clause",
                source_hash=H("h"),
                source_locator="file://x",
                verified=True,
                entitlement_reviewer_id=None,
            )

    def test_verified_causation_requires_qualified_reviewer(self):
        with self.assertRaises(ValueError):
            CausationReview(
                review_id="R",
                entitlement_id="E",
                event_id="EV",
                baseline_version_id="B",
                update_version_id="U",
                accepted_causation=True,
                accepted_delay_days=1,
                review_date="2026-09-01",
                source_hash=H("h"),
                source_locator="file://r",
                verified=True,
                qualified_reviewer_id=None,
                qualification_basis="Forensic scheduler",
            )

    def test_verified_causation_requires_qualification_basis(self):
        with self.assertRaises(ValueError):
            CausationReview(
                review_id="R",
                entitlement_id="E",
                event_id="EV",
                baseline_version_id="B",
                update_version_id="U",
                accepted_causation=True,
                accepted_delay_days=1,
                review_date="2026-09-01",
                source_hash=H("h"),
                source_locator="file://r",
                verified=True,
                qualified_reviewer_id="scheduler-1",
                qualification_basis=None,
            )

    def test_schedule_topology_hash_and_cpm_manifest_are_reproducible(self):
        version = schedule("BASE", "2026-08-01", b_duration=5)
        same = schedule("BASE-COPY", "2026-08-01", b_duration=5)
        self.assertEqual(version.topology_hash, same.topology_hash)
        result = calculate_cpm(version)
        self.assertEqual(result.manifest["topology_hash"], version.topology_hash)
        self.assertEqual(result.manifest["engine_id"], "recoveryworks.fs_cpm")
        self.assertEqual(result.manifest["method"], "finish_to_start_integer_day_cpm")

    def test_multiple_event_activity_mappings_are_supported(self):
        baseline = ScheduleVersion(
            version_id="BASE",
            project_id="PRJ-1",
            data_date="2026-08-01",
            activities=(
                ScheduleActivity("A", "A", 2),
                ScheduleActivity("B", "B", 3),
                ScheduleActivity("C", "C", 1),
            ),
            relationships=(
                ScheduleRelationship("A", "B"),
                ScheduleRelationship("B", "C"),
            ),
            source_hash=H("base"),
            source_locator="file://base",
            verified=True,
        )
        update = ScheduleVersion(
            version_id="UPD",
            project_id="PRJ-1",
            data_date="2026-09-01",
            activities=(
                ScheduleActivity("A", "A", 2),
                ScheduleActivity("B", "B", 5),
                ScheduleActivity("C", "C", 2),
            ),
            relationships=(
                ScheduleRelationship("A", "B"),
                ScheduleRelationship("B", "C"),
            ),
            source_hash=H("upd"),
            source_locator="file://upd",
            verified=True,
        )
        mappings = (
            mapping(),
            EventActivityMapping(
                mapping_id="MAP-2",
                event_id="EV-1",
                baseline_activity_id="C",
                update_activity_id="C",
                mapping_basis="daily report and schedule narrative",
                source_hash=H("mapping-hash-2"),
                source_locator="file://mappings.csv#row=3",
                verified=True,
            ),
        )
        result = batch(
            schedules=(baseline, update),
            mappings=mappings,
            causation_reviews=(review(days=3),),
        )
        self.assertEqual(result.exceptions, ())
        finding = RecoveryEngine().evaluate(result.observations[0])
        self.assertEqual(finding.metadata["mapping_ids"], ["MAP-1", "MAP-2"])
        self.assertEqual(len(finding.metadata["mapped_activity_impacts"]), 2)
        self.assertEqual(len(finding.evidence), 7)


if __name__ == "__main__":
    unittest.main()
