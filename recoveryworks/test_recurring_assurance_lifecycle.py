from __future__ import annotations

from dataclasses import replace
import unittest

from recoveryworks.recurring_assurance_activation import (
    build_external_recurring_assurance_authorization,
    build_recurring_assurance_activation_readiness,
)
from recoveryworks.recurring_assurance_lifecycle import (
    RecurringAssuranceLifecycleState,
    build_recurring_assurance_service_activation,
    build_recurring_assurance_service_deactivation,
    build_recurring_assurance_service_lifecycle,
)
from recoveryworks.test_commercial_agreement_gate import fixture


def lifecycle_fixture(*, monthly_assurance_fee_cents: int = 300000):
    charter, snapshot, ack, agreement = fixture(
        monthly_assurance_fee_cents=monthly_assurance_fee_cents,
        monthly_assurance_separately_accepted=True,
    )
    auth = build_external_recurring_assurance_authorization(
        charter,
        ack,
        agreement,
        service_start_at="2026-10-01T00:00:00Z",
        service_end_at="2027-10-01T00:00:00Z",
        authorization_reference=f"buyer-auth-{monthly_assurance_fee_cents}",
        source_hash="8" * 64,
        source_locator=f"buyer://monthly-assurance/{monthly_assurance_fee_cents}",
        verified=True,
        externally_authorized=True,
    )
    ready = build_recurring_assurance_activation_readiness(
        charter, ack, agreement, auth
    )
    return charter, snapshot, ack, agreement, auth, ready


class RecurringAssuranceLifecycleTests(unittest.TestCase):
    def test_activation_creates_internal_active_state_without_external_actions(self):
        *_, ready = lifecycle_fixture()
        activation = build_recurring_assurance_service_activation(
            ready,
            activated_at="2026-10-01T00:00:00Z",
            operator_id="operator-001",
            activation_reference="assurance-activate-001",
            internal_operator_authorized=True,
        )
        lifecycle = build_recurring_assurance_service_lifecycle(ready, activation)

        self.assertIs(lifecycle.state, RecurringAssuranceLifecycleState.ACTIVE)
        self.assertFalse(lifecycle.automatic_invoice_schedule_enabled)
        self.assertFalse(lifecycle.provider_mutation_enabled)
        self.assertFalse(lifecycle.customer_scope_mutation_enabled)
        self.assertFalse(lifecycle.external_actions_performed)

    def test_deactivation_is_separate_proof_bound_receipt(self):
        *_, ready = lifecycle_fixture()
        activation = build_recurring_assurance_service_activation(
            ready,
            activated_at="2026-10-01T00:00:00Z",
            operator_id="operator-001",
            activation_reference="assurance-activate-001",
            internal_operator_authorized=True,
        )
        deactivation = build_recurring_assurance_service_deactivation(
            activation,
            deactivated_at="2026-11-15T12:00:00Z",
            operator_id="operator-002",
            deactivation_reference="assurance-stop-001",
            reason="buyer requested service stop",
            internal_operator_authorized=True,
        )
        lifecycle = build_recurring_assurance_service_lifecycle(
            ready, activation, deactivation
        )

        self.assertIs(
            lifecycle.state, RecurringAssuranceLifecycleState.DEACTIVATED
        )
        self.assertEqual(lifecycle.active_until, deactivation.deactivated_at)
        self.assertEqual(
            lifecycle.deactivation_receipt_proof_hash, deactivation.proof_hash
        )
        self.assertFalse(deactivation.automatic_refund_or_credit_enabled)
        self.assertFalse(deactivation.external_actions_performed)

    def test_activation_outside_authorized_window_fails_closed(self):
        *_, ready = lifecycle_fixture()
        with self.assertRaisesRegex(ValueError, "authorized service window"):
            build_recurring_assurance_service_activation(
                ready,
                activated_at="2026-09-30T23:59:59Z",
                operator_id="operator-001",
                activation_reference="too-early",
                internal_operator_authorized=True,
            )

    def test_cross_readiness_substitution_fails_closed(self):
        *_, ready_a = lifecycle_fixture(monthly_assurance_fee_cents=300000)
        *_, ready_b = lifecycle_fixture(monthly_assurance_fee_cents=250000)
        activation = build_recurring_assurance_service_activation(
            ready_a,
            activated_at="2026-10-01T00:00:00Z",
            operator_id="operator-001",
            activation_reference="assurance-activate-001",
            internal_operator_authorized=True,
        )
        with self.assertRaisesRegex(ValueError, "exact recurring readiness"):
            build_recurring_assurance_service_lifecycle(ready_b, activation)

    def test_automatic_billing_or_provider_mutation_cannot_be_enabled(self):
        *_, ready = lifecycle_fixture()
        activation = build_recurring_assurance_service_activation(
            ready,
            activated_at="2026-10-01T00:00:00Z",
            operator_id="operator-001",
            activation_reference="assurance-activate-001",
            internal_operator_authorized=True,
        )
        with self.assertRaisesRegex(ValueError, "cannot enable automatic billing"):
            replace(activation, automatic_invoice_schedule_enabled=True)
        with self.assertRaisesRegex(ValueError, "cannot enable automatic billing"):
            replace(activation, provider_mutation_enabled=True)

    def test_deactivation_cannot_predate_activation(self):
        *_, ready = lifecycle_fixture()
        activation = build_recurring_assurance_service_activation(
            ready,
            activated_at="2026-10-15T00:00:00Z",
            operator_id="operator-001",
            activation_reference="assurance-activate-001",
            internal_operator_authorized=True,
        )
        with self.assertRaisesRegex(ValueError, "cannot predate activation"):
            build_recurring_assurance_service_deactivation(
                activation,
                deactivated_at="2026-10-14T23:59:59Z",
                operator_id="operator-002",
                deactivation_reference="assurance-stop-001",
                reason="invalid chronology fixture",
                internal_operator_authorized=True,
            )


if __name__ == "__main__":
    unittest.main()
