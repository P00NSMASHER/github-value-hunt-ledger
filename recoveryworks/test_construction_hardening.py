import unittest

from recoveryworks import RecoveryEngine
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
)


def schedule(version_id, data_date, *, a_duration=5, b_duration=5, c_duration=None, verified=True):
    activities = [
        ScheduleActivity("A", "Start", a_duration),
        ScheduleActivity("B", "Affected", b_duration),
    ]
    relationships = [ScheduleRelationship("A", "B")]
    if c_duration is not None:
        activities.append(ScheduleActivity("C", "Parallel", c_duration))
    return ScheduleVersion(
        version_id=version_id,
        project_id="P1",
        data_date=data_date,
        activities=tuple(activities),
        relationships=tuple(relationships),
        source_hash="container-hash",
        source_locator=f"file://schedules.json#{version_id}",
        verified=verified,
    )


def entitlement():
    return ConstructionEntitlement(
        entitlement_id="ENT-1",
        claimant_id="client",
        project_id="P1",
        counterparty_id="owner",
        change_id="CO-1",
        event_id="EV-1",
        entitled_cents=10000000,
        effective_date="2026-08-10",
        entitlement_basis="reviewed clause and priced change",
        source_hash="ent-hash",
        source_locator="file://entitlements.csv#2",
        verified=True,
        entitlement_reviewer_id="contract-reviewer",
    )


def event(event_date="2026-08-05"):
    return ConstructionEvent(
        event_id="EV-1",
        project_id="P1",
        event_date=event_date,
        description="owner-caused access restriction",
        source_hash="event-hash",
        source_locator="file://events.csv#2",
        verified=True,
    )


def mapping(activity="B"):
    return EventActivityMapping(
        mapping_id="MAP-1",
        event_id="EV-1",
        baseline_activity_id=activity,
        update_activity_id=activity,
        mapping_basis="RFI + daily report",
        source_hash="map-hash",
        source_locator="file://mappings.csv#2",
        verified=True,
    )


def review(days=3, *, baseline="BASE", update="UPD"):
    return CausationReview(
        review_id="REV-1",
        entitlement_id="ENT-1",
        event_id="EV-1",
        baseline_version_id=baseline,
        update_version_id=update,
        accepted_causation=True,
        accepted_delay_days=days,
        review_date="2026-09-15",
        source_hash="review-hash",
        source_locator="file://reviews.csv#2",
        verified=True,
        qualified_reviewer_id="scheduler-1",
    )


def settlement():
    return ConstructionSettlement(
        settlement_id="PAY-1",
        entitlement_id="ENT-1",
        amount_received_cents=2000000,
        settlement_date="2026-09-20",
        source_hash="settle-hash",
        source_locator="file://settlements.csv#2",
        verified=True,
    )


class ConstructionHardeningTests(unittest.TestCase):
    def test_schedule_version_hash_is_structural_and_version_specific(self):
        base = schedule("BASE", "2026-08-01", b_duration=5)
        changed = schedule("UPD", "2026-09-01", b_duration=8)
        same_shape_other_container = ScheduleVersion(
            version_id="BASE",
            project_id="P1",
            data_date="2026-08-01",
            activities=base.activities,
            relationships=base.relationships,
            source_hash="different-container",
            source_locator="file://other.json#0",
            verified=True,
        )
        self.assertNotEqual(base.version_hash, changed.version_hash)
        self.assertEqual(base.version_hash, same_shape_other_container.version_hash)
        self.assertEqual(base.evidence().metadata["version_hash"], base.version_hash)

    def test_event_before_baseline_window_fails_closed(self):
        batch = audit_construction_recovery(
            client_id="client",
            entitlements=(entitlement(),),
            events=(event("2026-07-20"),),
            mappings=(mapping(),),
            schedules=(
                schedule("BASE", "2026-08-01", b_duration=5),
                schedule("UPD", "2026-09-01", b_duration=8),
            ),
            causation_reviews=(review(3),),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "EVENT_OUTSIDE_SCHEDULE_WINDOW")

    def test_accepted_days_cannot_exceed_mapped_activity_delay(self):
        # Project grows by 5 days due to parallel C, while mapped B moves only 3.
        baseline = schedule("BASE", "2026-08-01", b_duration=5, c_duration=7)
        update = schedule("UPD", "2026-09-01", b_duration=8, c_duration=12)
        batch = audit_construction_recovery(
            client_id="client",
            entitlements=(entitlement(),),
            events=(event(),),
            mappings=(mapping("B"),),
            schedules=(baseline, update),
            causation_reviews=(review(4),),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "ACCEPTED_DELAY_EXCEEDS_CPM_IMPACT",
        )

    def test_noncritical_mapped_activity_cannot_support_project_delay(self):
        # B is delayed, but a much longer independent C path controls both schedules.
        baseline = schedule("BASE", "2026-08-01", b_duration=5, c_duration=20)
        update = schedule("UPD", "2026-09-01", b_duration=8, c_duration=25)
        batch = audit_construction_recovery(
            client_id="client",
            entitlements=(entitlement(),),
            events=(event(),),
            mappings=(mapping("B"),),
            schedules=(baseline, update),
            causation_reviews=(review(3),),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MAPPED_ACTIVITY_NOT_CRITICAL")

    def test_validated_finding_carries_version_hashes_and_supported_delay(self):
        base = schedule("BASE", "2026-08-01", b_duration=5)
        update = schedule("UPD", "2026-09-01", b_duration=8)
        batch = audit_construction_recovery(
            client_id="client",
            entitlements=(entitlement(),),
            events=(event(),),
            mappings=(mapping(),),
            schedules=(base, update),
            causation_reviews=(review(3),),
            settlements=(settlement(),),
        )
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.metadata["baseline_version_hash"], base.version_hash)
        self.assertEqual(finding.metadata["update_version_hash"], update.version_hash)
        self.assertEqual(finding.metadata["supported_causation_delay_days"], 3)


if __name__ == "__main__":
    unittest.main()
