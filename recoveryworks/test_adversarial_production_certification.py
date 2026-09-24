from __future__ import annotations

import unittest

from recoveryworks.commercial_operational_invariants import (
    CommercialOperationalInvariantState,
    verify_commercial_operational_invariants,
)
from recoveryworks.models import canonical_hash
from recoveryworks.recurring_assurance_lifecycle import (
    RecurringAssuranceLifecycleState,
    build_recurring_assurance_service_activation,
    build_recurring_assurance_service_deactivation,
    build_recurring_assurance_service_lifecycle,
)
from recoveryworks.test_commercial_operational_invariants import full_chain


PROOF_TAMPER_TARGETS = (
    ("kickoff_authorization", "charter_proof_hash"),
    ("kickoff_gate", "kickoff_authorization_proof_hash"),
    ("closeout", "charter_proof_hash"),
    ("closeout_acknowledgment", "closeout_proof_hash"),
    ("agreement", "charter_proof_hash"),
    ("fee_readiness", "agreement_receipt_proof_hash"),
    ("billing_draft", "fee_readiness_proof_hash"),
    ("invoice_handoff", "draft_proof_hash"),
    ("invoice_receipt", "handoff_proof_hash"),
    ("issued_invoice", "handoff_proof_hash"),
    ("payment_reconciliation", "issued_invoice_proof_hash"),
    ("recurring_authorization", "agreement_receipt_proof_hash"),
    ("recurring_readiness", "authorization_receipt_proof_hash"),
    ("recurring_activation", "readiness_proof_hash"),
    ("recurring_lifecycle", "activation_receipt_proof_hash"),
)

CROSS_TENANT_TARGETS = (
    "kickoff_authorization",
    "kickoff_gate",
    "closeout_acknowledgment",
    "agreement",
    "fee_readiness",
    "billing_draft",
    "invoice_handoff",
    "issued_invoice",
    "payment_reconciliation",
    "recurring_authorization",
    "recurring_readiness",
    "recurring_activation",
    "recurring_lifecycle",
)


class AdversarialProductionCertificationTests(unittest.TestCase):
    def assert_blocked(self, chain, *, code: str | None = None):
        result = verify_commercial_operational_invariants(**chain)
        self.assertIs(result.state, CommercialOperationalInvariantState.BLOCKED)
        self.assertTrue(result.failed_codes)
        self.assertFalse(result.external_actions_performed)
        self.assertFalse(result.automatic_repair_performed)
        if code is not None:
            self.assertIn(code, result.failed_codes)
        with self.assertRaisesRegex(
            ValueError, "commercial operational invariants blocked"
        ):
            result.require_pass()
        return result

    def test_bounded_deterministic_proof_tamper_fuzz_fails_closed(self):
        # Reproducible property-style fuzzing: every bound proof surface is
        # mutated with multiple deterministic hashes. No test randomness means
        # a certification failure can be replayed exactly.
        for case_number in range(45):
            key, field = PROOF_TAMPER_TARGETS[
                case_number % len(PROOF_TAMPER_TARGETS)
            ]
            chain = full_chain()
            forged_hash = canonical_hash(
                {
                    "certification": "RECOVERYWORKS_41A",
                    "attack": "PROOF_TAMPER",
                    "case": case_number,
                    "target": f"{key}.{field}",
                }
            )
            object.__setattr__(chain[key], field, forged_hash)
            with self.subTest(case=case_number, target=f"{key}.{field}"):
                self.assert_blocked(chain)

    def test_cross_tenant_substitution_property_fails_closed(self):
        for case_number, key in enumerate(CROSS_TENANT_TARGETS):
            chain = full_chain()
            object.__setattr__(
                chain[key], "buyer_id", f"substituted-buyer-{case_number:02d}"
            )
            with self.subTest(target=key):
                self.assert_blocked(chain)

    def test_non_cash_amount_surfaces_never_become_success_fee_basis(self):
        for amount in (10001, 50000, 250000, 999999, 25000000):
            chain = full_chain()
            object.__setattr__(
                chain["fee_readiness"], "recovered_cash_cents", amount
            )
            with self.subTest(forged_recovered_cash_cents=amount):
                self.assert_blocked(
                    chain, code="RECOVERED_CASH_AMOUNT_SURFACE"
                )

    def test_stale_authorization_fuzz_is_rejected_at_use_time(self):
        stale_cases = (
            (
                "kickoff_authorization",
                "expires_at",
                "2026-09-24T15:59:59Z",
            ),
            (
                "recurring_authorization",
                "service_end_at",
                "2026-10-01T00:00:00Z",
            ),
        )
        for key, field, value in stale_cases:
            chain = full_chain()
            object.__setattr__(chain[key], field, value)
            with self.subTest(target=f"{key}.{field}"):
                self.assert_blocked(
                    chain, code="LIFECYCLE_CHRONOLOGY_AND_FRESHNESS"
                )

    def test_duplicate_settlement_replay_is_rejected(self):
        chain = full_chain()
        receipt = chain["settlement_receipts"][0]
        chain["settlement_receipts"] = (receipt, receipt)
        self.assert_blocked(
            chain, code="INDEPENDENT_SETTLEMENT_RECONCILIATION"
        )

    def test_replayed_deactivation_receipt_cannot_cross_activation_boundary(self):
        chain = full_chain()
        activation_a = chain["recurring_activation"]
        deactivation_a = build_recurring_assurance_service_deactivation(
            activation_a,
            deactivated_at="2026-11-15T12:00:00Z",
            operator_id="operator-stop-a",
            deactivation_reference="stop-a",
            reason="certification fixture",
            internal_operator_authorized=True,
        )
        lifecycle_a = build_recurring_assurance_service_lifecycle(
            chain["recurring_readiness"], activation_a, deactivation_a
        )
        activation_b = build_recurring_assurance_service_activation(
            chain["recurring_readiness"],
            activated_at=activation_a.activated_at,
            operator_id="operator-replay-b",
            activation_reference="activation-b",
            internal_operator_authorized=True,
        )
        chain["recurring_activation"] = activation_b
        chain["recurring_deactivation"] = deactivation_a
        chain["recurring_lifecycle"] = lifecycle_a
        chain["checked_at"] = "2026-11-15T12:01:00Z"
        self.assert_blocked(
            chain, code="RECURRING_LIFECYCLE_STATE_INTEGRITY"
        )

    def test_lifecycle_state_skipping_fails_closed(self):
        mutations = (
            ("state", RecurringAssuranceLifecycleState.DEACTIVATED),
            ("active_until", "2026-10-15T00:00:00Z"),
            ("deactivation_receipt_proof_hash", "a" * 64),
        )
        for field, value in mutations:
            chain = full_chain()
            object.__setattr__(chain["recurring_lifecycle"], field, value)
            with self.subTest(field=field):
                self.assert_blocked(
                    chain, code="RECURRING_LIFECYCLE_STATE_INTEGRITY"
                )

    def test_exact_deactivated_lifecycle_remains_valid(self):
        chain = full_chain()
        deactivation = build_recurring_assurance_service_deactivation(
            chain["recurring_activation"],
            deactivated_at="2026-11-15T12:00:00Z",
            operator_id="operator-stop-valid",
            deactivation_reference="stop-valid",
            reason="buyer requested service stop",
            internal_operator_authorized=True,
        )
        chain["recurring_deactivation"] = deactivation
        chain["recurring_lifecycle"] = build_recurring_assurance_service_lifecycle(
            chain["recurring_readiness"],
            chain["recurring_activation"],
            deactivation,
        )
        chain["checked_at"] = "2026-11-15T12:01:00Z"

        result = verify_commercial_operational_invariants(**chain)
        self.assertIs(result.state, CommercialOperationalInvariantState.PASS)
        self.assertEqual(result.failed_codes, ())
        self.assertIn(
            ("recurring_deactivation", deactivation.proof_hash),
            result.artifact_proof_hashes,
        )
        self.assertFalse(result.external_actions_performed)
        self.assertFalse(result.automatic_repair_performed)


if __name__ == "__main__":
    unittest.main()
