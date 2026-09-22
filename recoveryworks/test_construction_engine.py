import unittest

from recoveryworks import EvidenceRef, FindingState, RecoveryEngine, RuleRef
from recoveryworks.engines.construction import (
    ConstructionEntitlement,
    ScheduleImpact,
    detect_construction_recovery,
)


def rule():
    return RuleRef(
        rule_id="contract-clause-7.4",
        source_hash="contracthash",
        effective_from="2026-01-01",
        effective_to=None,
        verified_controlling=True,
        source_locator="source://contract#7.4",
    )


def evidence():
    return EvidenceRef(
        evidence_id="co-7",
        source_hash="cohash",
        locator="source://change-order#7",
        kind="change_order",
        verified=True,
    )


def entitlement():
    return ConstructionEntitlement(
        event_id="co-7", event_date="2026-06-01",
        entitled_cents=500000, paid_cents=200000, currency="USD",
        rule=rule(), evidence=(evidence(),), entitlement_type="delay",
    )


def impact(*, verified=True):
    return ScheduleImpact(
        analysis_id="cpm-1", method="AACE-window-analysis", impact_days=12,
        analysis_hash="analysishash", locator="source://cpm#1",
        baseline_hash="baselinehash", comparison_hash="updatehash",
        verified=verified,
    )


class ConstructionRecoveryTests(unittest.TestCase):
    def test_delay_recovery_requires_schedule_impact_when_configured(self):
        observation = detect_construction_recovery(
            client_id="sub", counterparty_id="gc", entitlement=entitlement(),
            require_schedule_impact=True,
        )
        finding = RecoveryEngine().evaluate(observation)
        self.assertIs(finding.state, FindingState.REVIEW)
        self.assertEqual(finding.potential_recovery_cents, 300000)

    def test_verified_schedule_impact_allows_validated_delay_candidate(self):
        observation = detect_construction_recovery(
            client_id="sub", counterparty_id="gc", entitlement=entitlement(),
            schedule_impact=impact(), require_schedule_impact=True,
        )
        finding = RecoveryEngine().evaluate(observation)
        self.assertIs(finding.state, FindingState.VALIDATED)
        self.assertEqual(finding.metadata["schedule_analysis_id"], "cpm-1")

    def test_unverified_schedule_analysis_keeps_review(self):
        observation = detect_construction_recovery(
            client_id="sub", counterparty_id="gc", entitlement=entitlement(),
            schedule_impact=impact(verified=False), require_schedule_impact=True,
        )
        self.assertIs(RecoveryEngine().evaluate(observation).state, FindingState.REVIEW)

    def test_change_entitlement_can_validate_without_schedule_analysis(self):
        observation = detect_construction_recovery(
            client_id="sub", counterparty_id="gc", entitlement=entitlement(),
            require_schedule_impact=False,
        )
        self.assertIs(RecoveryEngine().evaluate(observation).state, FindingState.VALIDATED)


if __name__ == "__main__":
    unittest.main()
