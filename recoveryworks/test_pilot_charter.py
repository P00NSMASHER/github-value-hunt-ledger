from __future__ import annotations

import unittest

from recoveryworks.pilot_activation_packet import build_recoveryworks_activation_packet
from recoveryworks.pilot_charter import (
    PilotCharterState,
    build_recoveryworks_pilot_charter,
    pilot_charter_request_from_dict,
)
from recoveryworks.pilot_launch_brief import build_pilot_launch_brief
from recoveryworks.pilot_launch_gate import evaluate_pilot_launch_gate
from recoveryworks.production_service_levels import InternalCapacityDemand
from recoveryworks.test_pilot_launch_gate import (
    commercial,diligence,envelope,rehearsal,slo,
)


def packet():
    decision=evaluate_pilot_launch_gate(
        commercial_package=commercial(),operator_rehearsal=rehearsal(),
        diligence_package=diligence(),service_level=slo(),
        capacity_envelope=envelope(),demand=InternalCapacityDemand(100,1,1,1000),
        checked_at="2026-09-24T13:05:00Z")
    return build_recoveryworks_activation_packet(
        decision,build_pilot_launch_brief(decision),commercial())


def request_dict():
    return {
        "engagement_id":"eng-001","buyer_id":"buyer-001","business_unit":"FinOps",
        "population_rule":"AWS payer account sim-acct for August 2026",
        "source_date_start":"2026-08-01","source_date_end":"2026-08-31",
        "billing_account_scope":["sim-acct"],"provider_scope":["aws"],
        "diagnostic_fee_cents":500000,
        "recovered_cash_success_fee_bps":2000,
        "monthly_assurance_fee_cents":250000,
        "buyer_truth_owner_role":"FinOps owner",
        "buyer_action_approver_role":"Controller",
        "recoveryworks_engagement_owner_role":"RecoveryWorks operator",
        "buyer_acknowledges_scope":True,
        "buyer_acknowledges_read_only_intake":True,
        "buyer_acknowledges_report_surfaces_separate":True,
        "buyer_acknowledges_no_guaranteed_recovery":True,
        "buyer_acknowledges_success_fee_only_on_verified_recovered_cash":True,
        "recoveryworks_acknowledges_no_external_action_without_separate_approval":True,
    }


class PilotCharterTests(unittest.TestCase):
    def test_prelaunch_acceptance_freezes_scope_but_authorizes_nothing(self):
        charter=build_recoveryworks_pilot_charter(
            packet(),pilot_charter_request_from_dict(request_dict()))
        self.assertIs(charter.state,PilotCharterState.PRELAUNCH_ACCEPTED)
        self.assertFalse(charter.customer_data_authorized)
        self.assertFalse(charter.kickoff_authorized)
        self.assertFalse(charter.external_action_authorized)
        self.assertFalse(charter.contract_created)

    def test_false_ack_stays_pending(self):
        data=request_dict()
        data["buyer_acknowledges_no_guaranteed_recovery"]=False
        charter=build_recoveryworks_pilot_charter(
            packet(),pilot_charter_request_from_dict(data))
        self.assertIs(charter.state,PilotCharterState.PENDING_ACKNOWLEDGMENT)

    def test_string_false_cannot_become_truthy_authorization(self):
        data=request_dict()
        data["buyer_acknowledges_scope"]="false"
        with self.assertRaisesRegex(ValueError,"must be literal boolean"):
            pilot_charter_request_from_dict(data)

    def test_fee_drift_from_activation_packet_fails_closed(self):
        data=request_dict()
        data["diagnostic_fee_cents"]=1
        with self.assertRaisesRegex(ValueError,"diagnostic fee differs"):
            build_recoveryworks_pilot_charter(
                packet(),pilot_charter_request_from_dict(data))


if __name__=="__main__":
    unittest.main()
