from __future__ import annotations

from types import SimpleNamespace
import unittest

from recoveryworks.capacity_matrix import (
    CapacityDimension,
    build_conservative_operating_envelope,
    measured_capacity_cell,
)
from recoveryworks.commercial_pilot import build_commercial_pilot_package
from recoveryworks.enterprise_diligence_package import (
    DiligenceGap,
    DiligenceGapSeverity,
)
from recoveryworks.pilot_launch_brief import build_pilot_launch_brief
from recoveryworks.pilot_launch_gate import (
    PilotLaunchStatus,
    evaluate_pilot_launch_gate,
)
from recoveryworks.production_service_levels import (
    InternalCapacityDemand,
    InternalServiceLevelSnapshot,
    ServicePressureState,
)
from recoveryworks.models import canonical_hash


def commercial():
    return build_commercial_pilot_package({
        "schema":1,
        "offer_name":"Cloud Recovery & Savings Assurance Pilot",
        "buyer_profile":"Mid-market cloud buyer",
        "scope":{
            "provider":"aws","lookback_months":12,"max_billing_accounts":1,
            "recovery_modes":["CONTRACT_RATE_MISMATCH"],
            "include_prospective_savings":True,"include_diagnostics":True,
            "include_remediation_plan":True,"cloud_mutation_in_scope":False,
            "external_recovery_actions_in_scope":False,
        },
        "deliverables":["Assurance report"],
        "pricing":{
            "currency":"USD","diagnostic_fee_cents":500000,
            "recovered_cash_success_fee_bps":2000,
            "monthly_assurance_fee_cents":250000,
            "savings_implementation_fee_cents":None,
            "pricing_is_hypothesis":True,
        },
        "acceptance_criteria":[{
            "criterion_id":"A1",
            "description":"Validated recovery evidence is reproducible.",
            "required_evidence":"RecoveryOS proof packet",
        }],
        "exclusions":["Cloud mutation"],
        "assumptions":["Authorized inputs supplied separately."],
    })


def envelope():
    cells=(
        measured_capacity_cell(
            dimension=CapacityDimension.BILLING_ROWS,billing_rows=1000,
            provider_count=1,tenant_count=1,bundle_bytes=1000,evidence_bytes=1000,
            runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1000,
            evidence_proof_hashes=("1"*64,)),
        measured_capacity_cell(
            dimension=CapacityDimension.PROVIDERS,billing_rows=100,
            provider_count=3,tenant_count=1,bundle_bytes=1000,evidence_bytes=1000,
            runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1000,
            evidence_proof_hashes=("2"*64,)),
        measured_capacity_cell(
            dimension=CapacityDimension.TENANTS,billing_rows=100,
            provider_count=1,tenant_count=10,bundle_bytes=1000,evidence_bytes=1000,
            runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1000,
            evidence_proof_hashes=("3"*64,)),
        measured_capacity_cell(
            dimension=CapacityDimension.EVIDENCE_BYTES,billing_rows=100,
            provider_count=1,tenant_count=1,bundle_bytes=1000,evidence_bytes=100000,
            runtime_ms=1,peak_memory_bytes=1,rows_per_second_milli=1000,
            evidence_proof_hashes=("4"*64,)),
    )
    return build_conservative_operating_envelope(cells)


def slo(state=ServicePressureState.HEALTHY):
    alerts=()
    identity={
        "schema":1,"checked_at":"2026-09-24T13:00:00Z","state":state.value,
        "queue_depth":0,"oldest_job_age_seconds":0,"schedule_lateness_seconds":0,
        "missed_job_count":0,"capacity_utilization_bps":1000,
        "capacity_admitted":True,"alert_hashes":[],
        "admission_throttled":state is ServicePressureState.THROTTLED,
        "autonomous_external_actions_enabled":False,
    }
    return InternalServiceLevelSnapshot(
        snapshot_id="recoveryworks-service-level:"+canonical_hash(identity),
        checked_at=identity["checked_at"],state=state,queue_depth=0,
        oldest_job_age_seconds=0,schedule_lateness_seconds=0,
        missed_job_count=0,capacity_utilization_bps=1000,
        capacity_admitted=True,alerts=alerts,
        admission_throttled=state is ServicePressureState.THROTTLED,
        autonomous_external_actions_enabled=False,
    )


def rehearsal():
    return SimpleNamespace(
        proof_hash="5"*64,
        customer_contacted=False,
        real_customer_onboarded=False,
        external_actions_performed=False,
    )


def diligence(gaps=()):
    return SimpleNamespace(
        proof_hash="6"*64,
        gaps=tuple(gaps),
        certifications_claimed=(),
        externally_shared=False,
    )


class PilotLaunchGateTests(unittest.TestCase):
    def test_ready_gate_binds_authoritative_upstream_proofs(self):
        decision=evaluate_pilot_launch_gate(
            commercial_package=commercial(),
            operator_rehearsal=rehearsal(),
            diligence_package=diligence(),
            service_level=slo(),
            capacity_envelope=envelope(),
            demand=InternalCapacityDemand(100,1,1,1000),
            checked_at="2026-09-24T13:05:00Z")
        self.assertIs(decision.status,PilotLaunchStatus.READY)
        self.assertTrue(decision.buyer_handoff_allowed)
        self.assertFalse(decision.customer_data_authorized)
        self.assertFalse(decision.kickoff_authorized)
        brief=build_pilot_launch_brief(decision)
        self.assertEqual(brief.launch_decision_proof_hash,decision.proof_hash)
        self.assertFalse(brief.can_override_gate)

    def test_pressure_is_conditional_and_high_gap_blocks(self):
        conditional=evaluate_pilot_launch_gate(
            commercial_package=commercial(),operator_rehearsal=rehearsal(),
            diligence_package=diligence(),service_level=slo(ServicePressureState.PRESSURE),
            capacity_envelope=envelope(),demand=InternalCapacityDemand(100,1,1,1000),
            checked_at="2026-09-24T13:05:00Z")
        self.assertIs(conditional.status,PilotLaunchStatus.CONDITIONAL)
        gap=DiligenceGap(
            gap_id="GAP-IR",control_id="IR-01",
            severity=DiligenceGapSeverity.HIGH,
            description="Missing event evidence.",owner_id="owner",
            due_at="2026-10-01T00:00:00Z",remediation_plan="Collect evidence.")
        blocked=evaluate_pilot_launch_gate(
            commercial_package=commercial(),operator_rehearsal=rehearsal(),
            diligence_package=diligence((gap,)),service_level=slo(),
            capacity_envelope=envelope(),demand=InternalCapacityDemand(100,1,1,1000),
            checked_at="2026-09-24T13:05:00Z")
        self.assertIs(blocked.status,PilotLaunchStatus.BLOCKED)
        self.assertFalse(blocked.buyer_handoff_allowed)

    def test_over_capacity_blocks_before_handoff(self):
        decision=evaluate_pilot_launch_gate(
            commercial_package=commercial(),operator_rehearsal=rehearsal(),
            diligence_package=diligence(),service_level=slo(),
            capacity_envelope=envelope(),
            demand=InternalCapacityDemand(1001,1,1,1000),
            checked_at="2026-09-24T13:05:00Z")
        self.assertIs(decision.status,PilotLaunchStatus.BLOCKED)
        self.assertIn("requested_scope_exceeds_measured_capacity",decision.blockers)


if __name__=="__main__":
    unittest.main()
