from recoveryworks.test_support import source_hash as H
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


def schedule(version_id, data_date, *, b_duration, c_duration=None):
    activities = [
        ScheduleActivity("A", "Start", 5),
        ScheduleActivity("B", "Affected", b_duration),
    ]
    relationships = [ScheduleRelationship("A", "B")]
    if c_duration is not None:
        activities.append(ScheduleActivity("C", "Parallel controlling work", c_duration))
    return ScheduleVersion(
        version_id=version_id,
        project_id="PRJ-1",
        data_date=data_date,
        activities=tuple(activities),
        relationships=tuple(relationships),
        source_hash=H(f"schedule-container-{version_id}"),
        source_locator=f"file://schedules.json#{version_id}",
        verified=True,
    )


def entitlement():
    return ConstructionEntitlement(
        entitlement_id="ENT-1",
        claimant_id="client-1",
        project_id="PRJ-1",
        counterparty_id="Owner-1",
        change_id="CO-7",
        event_id="EV-1",
        entitled_cents=10_000_000,
        effective_date="2026-08-10",
        entitlement_basis="Reviewed clause 7.4 and priced change",
        source_hash=H("entitlement-hash"),
        source_locator="file://entitlements.csv#row=2",
        verified=True,
        entitlement_reviewer_id="contract-reviewer-1",
    )


def event(event_date="2026-08-05"):
    return ConstructionEvent(
        event_id="EV-1",
        project_id="PRJ-1",
        event_date=event_date,
        description="Owner-directed access restriction",
        source_hash=H("event-hash"),
        source_locator="file://events.csv#row=2",
        verified=True,
    )


def mapping():
    return EventActivityMapping(
        mapping_id="MAP-1",
        event_id="EV-1",
        baseline_activity_id="B",
        update_activity_id="B",
        mapping_basis="RFI and daily report link the event to activity B",
        source_hash=H("mapping-hash"),
        source_locator="file://mappings.csv#row=2",
        verified=True,
    )


def review(days):
    return CausationReview(
        review_id="REV-1",
        entitlement_id="ENT-1",
        event_id="EV-1",
        baseline_version_id="BASE",
        update_version_id="UPD",
        accepted_causation=True,
        accepted_delay_days=days,
        review_date="2026-09-15",
        source_hash=H("review-hash"),
        source_locator="file://causation.csv#row=2",
        verified=True,
        qualified_reviewer_id="scheduler-1",
        qualification_basis="Independent CPM delay analyst review",
    )


def settlement():
    return ConstructionSettlement(
        settlement_id="PAY-1",
        entitlement_id="ENT-1",
        amount_received_cents=2_000_000,
        settlement_date="2026-09-20",
        source_hash=H("settlement-hash"),
        source_locator="file://settlements.csv#row=2",
        verified=True,
    )


def audit(base, update, *, event_date="2026-08-05", days=3):
    return audit_construction_recovery(
        client_id="client-1",
        entitlements=(entitlement(),),
        events=(event(event_date),),
        mappings=(mapping(),),
        schedules=(base, update),
        causation_reviews=(review(days),),
        settlements=(settlement(),),
    )


class ConstructionCausationBoundsTests(unittest.TestCase):
    def test_event_before_baseline_window_fails_closed(self):
        batch = audit(
            schedule("BASE", "2026-08-01", b_duration=5),
            schedule("UPD", "2026-09-01", b_duration=8),
            event_date="2026-07-20",
            days=3,
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "EVENT_OUTSIDE_SCHEDULE_WINDOW")

    def test_event_after_update_window_fails_closed(self):
        batch = audit(
            schedule("BASE", "2026-08-01", b_duration=5),
            schedule("UPD", "2026-09-01", b_duration=8),
            event_date="2026-09-05",
            days=3,
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "EVENT_OUTSIDE_SCHEDULE_WINDOW")

    def test_accepted_days_cannot_exceed_mapped_activity_delay(self):
        # Baseline project duration is controlled by A->B at 10 days.
        # Update project duration is controlled by independent C at 15 days.
        # B itself only moves 3 days, so a 4-day causal allocation is unsupported.
        batch = audit(
            schedule("BASE", "2026-08-01", b_duration=5, c_duration=7),
            schedule("UPD", "2026-09-01", b_duration=8, c_duration=15),
            days=4,
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(
            batch.exceptions[0].code,
            "ACCEPTED_DELAY_EXCEEDS_CPM_IMPACT",
        )

    def test_noncritical_mapping_cannot_borrow_unrelated_project_delay(self):
        # Independent C controls both schedules; mapped B is delayed but noncritical.
        batch = audit(
            schedule("BASE", "2026-08-01", b_duration=5, c_duration=20),
            schedule("UPD", "2026-09-01", b_duration=8, c_duration=25),
            days=3,
        )
        self.assertEqual(batch.observations, ())
        self.assertEqual(batch.exceptions[0].code, "MAPPED_ACTIVITY_NOT_CRITICAL")

    def test_valid_finding_records_supported_causation_bound(self):
        base = schedule("BASE", "2026-08-01", b_duration=5)
        update = schedule("UPD", "2026-09-01", b_duration=8)
        batch = audit(base, update, days=3)
        self.assertEqual(batch.exceptions, ())
        finding = RecoveryEngine().evaluate(batch.observations[0])
        self.assertEqual(finding.metadata["supported_causation_delay_days"], 3)
        self.assertEqual(finding.metadata["mapped_activity_finish_delay_days"], 3)
        self.assertTrue(finding.metadata["baseline_activity_critical"])
        self.assertTrue(finding.metadata["update_activity_critical"])
        self.assertEqual(
            finding.metadata["baseline_topology_hash"],
            base.topology_hash,
        )
        self.assertEqual(
            finding.metadata["update_topology_hash"],
            update.topology_hash,
        )


if __name__ == "__main__":
    unittest.main()
