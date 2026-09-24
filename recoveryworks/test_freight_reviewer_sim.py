from dataclasses import replace
import unittest

from recoveryworks.branches.freight_case import verify_freight_review_packet
from recoveryworks.branches.freight_reviewer_sim import (
    BLOCKED_SELF_CONTAINED,
    GO,
    NO_GO,
    NOT_SELF_CONTAINED,
    VERIFIED_SELF_CONTAINED,
    render_simulated_human_gate_markdown,
    run_simulated_human_release_gate,
    simulate_human_case_review,
    simulate_human_packet_review,
)
from recoveryworks.branches.freight_validation import (
    adversarial_scenarios,
    build_adversarial_packet,
)


def packet_for(scenario_id):
    scenario = next(
        item for item in adversarial_scenarios()
        if item.scenario_id == scenario_id
    )
    _mapping, _findings, packet = build_adversarial_packet(scenario)
    return packet


class SimulatedHumanFreightReviewerTests(unittest.TestCase):
    def test_release_gate_is_go_at_one_hundred_percent_self_contained(self):
        gate = run_simulated_human_release_gate()

        self.assertEqual(gate.release_gate, GO)
        self.assertEqual(gate.scenario_count, 9)
        self.assertEqual(gate.packet_review_count, 9)
        self.assertEqual(gate.case_count, 5)
        self.assertEqual(gate.validated_case_count, 3)
        self.assertEqual(gate.review_case_count, 2)
        self.assertEqual(gate.no_money_packet_count, 4)
        self.assertEqual(gate.self_contained_case_count, 5)
        self.assertEqual(gate.manual_reconstruction_case_count, 0)
        self.assertEqual(gate.failed_case_count, 0)
        self.assertEqual(gate.failed_packet_count, 0)
        self.assertEqual(gate.required_self_contained_rate, 1.0)
        self.assertEqual(gate.actual_self_contained_rate, 1.0)
        self.assertEqual(len(gate.gate_hash), 64)

    def test_validated_cases_are_reproducible_from_packet(self):
        gate = run_simulated_human_release_gate()
        validated = [
            case
            for packet in gate.packet_reviews
            for case in packet.case_reviews
            if case.state == "VALIDATED"
        ]
        self.assertEqual(len(validated), 3)
        self.assertTrue(
            all(case.verdict == VERIFIED_SELF_CONTAINED for case in validated)
        )
        self.assertTrue(
            all(not case.manual_reconstruction_required for case in validated)
        )
        for case in validated:
            failed = set(case.failed_check_ids)
            self.assertNotIn("CALC_EXACT", failed)
            self.assertNotIn("AUTHORITY_ATTACHED", failed)
            self.assertNotIn("AUTHORITY_EFFECTIVE_DATE", failed)
            self.assertNotIn("EVIDENCE_SOURCE_DOCUMENTS", failed)

    def test_review_cases_are_self_contained_blockers_not_approved_dollars(self):
        gate = run_simulated_human_release_gate()
        review_cases = [
            case
            for packet in gate.packet_reviews
            for case in packet.case_reviews
            if case.state == "REVIEW"
        ]
        self.assertEqual(len(review_cases), 2)
        self.assertTrue(
            all(case.verdict == BLOCKED_SELF_CONTAINED for case in review_cases)
        )
        self.assertTrue(
            all(not case.manual_reconstruction_required for case in review_cases)
        )

    def test_load_mismatch_packet_exposes_the_conflicting_ids(self):
        packet = packet_for("mismatched_load_ids")
        case = packet.cases[0]
        self.assertNotEqual(case.invoice_load_id, case.rate_confirmation_load_id)

        review = simulate_human_case_review(case)
        self.assertEqual(review.verdict, BLOCKED_SELF_CONTAINED)
        self.assertNotIn(
            "REVIEW_LOAD_CONFLICT_PROOF",
            review.failed_check_ids,
        )

    def test_ambiguous_authority_packet_exposes_competing_rule_hashes(self):
        packet = packet_for("ambiguous_authority")
        case = packet.cases[0]
        self.assertGreaterEqual(len(set(case.matched_authority_rule_hashes)), 2)

        review = simulate_human_case_review(case)
        self.assertEqual(review.verdict, BLOCKED_SELF_CONTAINED)
        self.assertNotIn(
            "REVIEW_AUTHORITY_CONFLICT_PROOF",
            review.failed_check_ids,
        )

    def test_missing_invoice_identity_forces_manual_reconstruction(self):
        packet = packet_for("wrong_linehaul_rate")
        case = replace(packet.cases[0], invoice_number=None)

        review = simulate_human_case_review(case)
        self.assertEqual(review.verdict, NOT_SELF_CONTAINED)
        self.assertTrue(review.manual_reconstruction_required)
        self.assertIn("IDENTITY_INVOICE", review.failed_check_ids)

    def test_nonreproducible_arithmetic_forces_manual_reconstruction(self):
        packet = packet_for("wrong_linehaul_rate")
        case = packet.cases[0]
        bad_calc = replace(
            case.calculation,
            component_billed_cents=case.calculation.component_billed_cents + 1,
        )
        tampered = replace(case, calculation=bad_calc)

        review = simulate_human_case_review(tampered)
        self.assertEqual(review.verdict, NOT_SELF_CONTAINED)
        self.assertIn("CALC_EXACT", review.failed_check_ids)

    def test_hiding_load_conflict_proof_forces_manual_reconstruction(self):
        packet = packet_for("mismatched_load_ids")
        case = packet.cases[0]
        hidden = replace(
            case,
            invoice_load_id="SAME",
            rate_confirmation_load_id="SAME",
            pod_load_id="SAME",
        )

        review = simulate_human_case_review(hidden)
        self.assertEqual(review.verdict, NOT_SELF_CONTAINED)
        self.assertIn(
            "REVIEW_LOAD_CONFLICT_PROOF",
            review.failed_check_ids,
        )

    def test_hiding_competing_authority_proofs_forces_manual_reconstruction(self):
        packet = packet_for("ambiguous_authority")
        case = replace(
            packet.cases[0],
            matched_authority_rule_hashes=(),
        )

        review = simulate_human_case_review(case)
        self.assertEqual(review.verdict, NOT_SELF_CONTAINED)
        self.assertIn(
            "REVIEW_AUTHORITY_CONFLICT_PROOF",
            review.failed_check_ids,
        )

    def test_packet_integrity_tamper_is_rejected_and_simulated_reviewer_fails(self):
        packet = packet_for("wrong_linehaul_rate")
        verify_freight_review_packet(packet)

        tampered = replace(packet, packet_hash="0" * 64)
        review = simulate_human_packet_review(
            "tampered_packet",
            tampered,
        )
        self.assertEqual(review.packet_verdict, NOT_SELF_CONTAINED)
        self.assertTrue(
            any(
                check.check_id == "PACKET_INTEGRITY" and not check.passed
                for check in review.checks
            )
        )

    def test_no_money_packets_are_explainable_without_reconstruction(self):
        gate = run_simulated_human_release_gate()
        no_money = [item for item in gate.packet_reviews if item.no_money_packet]
        self.assertEqual(len(no_money), 4)
        self.assertTrue(
            all(item.manual_reconstruction_case_count == 0 for item in no_money)
        )
        self.assertTrue(
            all(item.supplemental_finding_count > 0 for item in no_money)
        )
        self.assertTrue(
            all(item.packet_verdict != NOT_SELF_CONTAINED for item in no_money)
        )

    def test_mutated_scenario_can_drive_gate_to_no_go(self):
        scenarios = list(adversarial_scenarios())
        bad = scenarios[2]
        from recoveryworks.branches.freight_audit import CarrierInvoice, LineItem

        scenarios[2] = replace(
            bad,
            invoice=CarrierInvoice(
                "INV-RATE",
                "LOAD-RATE",
                "carrier",
                100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
        )
        gate = run_simulated_human_release_gate(scenarios)
        self.assertEqual(gate.release_gate, GO)
        # Reviewer self-containment remains GO even if the scenario's economic
        # golden truth changes; Step 5 owns detection/accuracy correctness.
        # This test documents that Step 6 is specifically the human-verifiability gate.

        strict_gate = run_simulated_human_release_gate(required_self_contained_rate=1.0)
        self.assertEqual(strict_gate.release_gate, GO)

    def test_markdown_states_simulation_not_real_human_signoff(self):
        report = render_simulated_human_gate_markdown(
            run_simulated_human_release_gate()
        )
        self.assertIn("Release gate: **GO**", report)
        self.assertIn("Manual reconstruction required: **0**", report)
        self.assertIn("deterministic simulation of a human review checklist", report)
        self.assertIn("not a real human sign-off", report)


if __name__ == "__main__":
    unittest.main()
