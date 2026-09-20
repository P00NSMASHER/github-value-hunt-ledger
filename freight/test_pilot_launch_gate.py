from copy import deepcopy
from pathlib import Path

from freight.deployment_security_evidence import load_current
from freight.pilot_launch_gate import (
    DataPath,
    LaunchRequest,
    LaunchRoute,
    LaunchStatus,
    evaluate_launch,
)
from freight.readiness import PilotReadinessInput, assess_readiness
from freight.rights_evidence import load_json


ROOT=Path(__file__).resolve().parents[1]
REGISTRY=load_json(ROOT/"freight/COMPONENT_RIGHTS_REGISTRY.json")
RIGHTS=load_json(ROOT/"freight/RIGHTS_EVIDENCE_MANIFEST.json")
DEPLOYMENT=load_current(ROOT)


def readiness(**overrides):
    data=dict(
        authorization_documented=True,
        read_only_access=True,
        population_reproducible=True,
        incumbent_output_sealable=True,
        settlement_observable=True,
        material_authority_reconstructable=True,
        customer_identity_stable=True,
        carrier_identity_stable=True,
        retention_defined=True,
        deletion_defined=True,
        invoice_source_coverage=1.0,
        authority_source_coverage=1.0,
        shipment_evidence_coverage=1.0,
    )
    data.update(overrides)
    return assess_readiness(PilotReadinessInput(**data))


def decide(request, *, dep=None, ready=None):
    return evaluate_launch(
        readiness=ready or readiness(),
        component_registry=REGISTRY,
        rights_manifest=RIGHTS,
        deployment_evidence=dep or DEPLOYMENT,
        request=request,
    )


def test_buyer_readiness_does_not_override_current_deployment_security():
    d=decide(LaunchRequest(DataPath.CURRENT_DEPLOYMENT))
    assert d.status is LaunchStatus.BLOCKED
    assert d.route is LaunchRoute.DEPLOYED_PILOT_BLOCKED
    assert "deployment_team_mfa_not_enforced" in d.blockers
    assert "customer_data_plane_not_discovered" in d.blockers


def test_not_ready_buyer_routes_back_to_diagnostic_before_deployment_logic():
    d=decide(
        LaunchRequest(DataPath.CURRENT_DEPLOYMENT),
        ready=readiness(authorization_documented=False),
    )
    assert d.status is LaunchStatus.BLOCKED
    assert d.route is LaunchRoute.DATA_READINESS_DIAGNOSTIC
    assert "buyer_authorization_missing" in d.blockers


def test_current_deployment_still_blocks_multi_tenant_use_without_isolation_proof():
    dep=deepcopy(DEPLOYMENT)
    dep["access_control"]["team_mfa_enforced"]=True
    dep["deployment_inventory"]["status"]="FREIGHT_DATA_PLANE_DISCOVERED"
    d=decide(
        LaunchRequest(
            DataPath.CURRENT_DEPLOYMENT,
            requires_multi_tenant_data_plane=True,
        ),
        dep=dep,
    )
    assert d.status is LaunchStatus.BLOCKED
    assert "cross_tenant_isolation_not_proven" in d.blockers


def test_current_deployment_still_blocks_parser_use_without_sandbox_proof():
    dep=deepcopy(DEPLOYMENT)
    dep["access_control"]["team_mfa_enforced"]=True
    dep["deployment_inventory"]["status"]="FREIGHT_DATA_PLANE_DISCOVERED"
    d=decide(
        LaunchRequest(
            DataPath.CURRENT_DEPLOYMENT,
            requires_parser_runtime=True,
        ),
        dep=dep,
    )
    assert d.status is LaunchStatus.BLOCKED
    assert "parser_sandbox_not_proven" in d.blockers


def test_separate_environment_is_conditional_without_evidence():
    d=decide(LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT))
    assert d.status is LaunchStatus.CONDITIONAL
    assert d.route is LaunchRoute.SEPARATE_ENVIRONMENT_PENDING
    assert "separate_data_environment_controls_not_verified" in d.conditions
    assert "separate_data_environment_evidence_ref_missing" in d.conditions


def test_separate_controlled_environment_can_enable_manual_pilot_when_evidenced():
    d=decide(
        LaunchRequest(
            DataPath.SEPARATE_CONTROLLED_ENVIRONMENT,
            separate_environment_controls_verified=True,
            separate_environment_evidence_ref="diligence-room/manual-pilot-env-001",
        )
    )
    assert d.status is LaunchStatus.READY
    assert d.route is LaunchRoute.CONTROLLED_MANUAL_BLIND_PILOT


def test_deployed_pilot_can_be_ready_only_after_required_controls_are_proven():
    dep=deepcopy(DEPLOYMENT)
    dep["access_control"]["team_mfa_enforced"]=True
    dep["deployment_inventory"]["status"]="FREIGHT_DATA_PLANE_DISCOVERED"
    dep["cross_tenant_isolation"].update({
        "status":"PROVEN",
        "data_plane_id":"example-data-plane",
        "distinct_tenant_probe_count":2,
        "negative_cross_tenant_probe_passed":True,
    })
    dep["parser_sandbox"].update({
        "status":"PROVEN",
        "runtime_provider":"example-runtime",
        "cpu_limit_evidence_ref":"evidence/cpu",
        "memory_limit_evidence_ref":"evidence/memory",
        "time_limit_evidence_ref":"evidence/time",
        "network_isolation_evidence_ref":"evidence/network",
        "credential_isolation_evidence_ref":"evidence/credentials",
    })
    d=decide(
        LaunchRequest(
            DataPath.CURRENT_DEPLOYMENT,
            requires_multi_tenant_data_plane=True,
            requires_parser_runtime=True,
        ),
        dep=dep,
    )
    assert d.status is LaunchStatus.READY
    assert d.route is LaunchRoute.DEPLOYED_BLIND_PILOT
