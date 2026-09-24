from __future__ import annotations

import unittest

from recoveryworks.pilot_activation_packet import (
    build_recoveryworks_activation_packet,
)
from recoveryworks.pilot_launch_brief import build_pilot_launch_brief
from recoveryworks.pilot_launch_gate import evaluate_pilot_launch_gate
from recoveryworks.production_service_levels import InternalCapacityDemand
from recoveryworks.test_pilot_launch_gate import (
    commercial,diligence,envelope,rehearsal,slo,
)


class PilotActivationPacketTests(unittest.TestCase):
    def decision(self):
        return evaluate_pilot_launch_gate(
            commercial_package=commercial(),
            operator_rehearsal=rehearsal(),
            diligence_package=diligence(),
            service_level=slo(),
            capacity_envelope=envelope(),
            demand=InternalCapacityDemand(100,1,1,1000),
            checked_at="2026-09-24T13:05:00Z")

    def test_packet_binds_authoritative_gate_and_has_no_authorization(self):
        decision=self.decision()
        brief=build_pilot_launch_brief(decision)
        packet=build_recoveryworks_activation_packet(
            decision,brief,commercial())
        self.assertEqual(packet.launch_decision_proof_hash,decision.proof_hash)
        self.assertEqual(packet.launch_brief_proof_hash,brief.proof_hash)
        self.assertFalse(packet.customer_data_authorized)
        self.assertFalse(packet.kickoff_authorized)
        self.assertFalse(packet.external_action_authorized)
        self.assertFalse(packet.contract_created)
        self.assertEqual(
            packet.as_dict()["state"],"BUYER_SAFE_ACTIVATION_PACKET_READY")

    def test_tampered_brief_binding_fails(self):
        decision=self.decision()
        brief=build_pilot_launch_brief(decision)
        object.__setattr__(brief,"launch_decision_proof_hash","9"*64)
        with self.assertRaisesRegex(ValueError,"does not bind authoritative decision"):
            build_recoveryworks_activation_packet(decision,brief,commercial())


if __name__=="__main__":
    unittest.main()
