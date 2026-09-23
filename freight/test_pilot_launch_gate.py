from copy import deepcopy
from hashlib import sha256
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
from freight.separate_environment_evidence import load_environment


ROOT=Path(__file__).resolve().parents[1]
REGISTRY=load_json(ROOT/"freight/COMPONENT_RIGHTS_REGISTRY.json")
RIGHTS=load_json(ROOT/"freight/RIGHTS_EVIDENCE_MANIFEST.json")
DEPLOYMENT=load_current(ROOT)
SEPARATE_TEMPLATE=load_environment(
    ROOT/"freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json"
)
AS_OF="2026-09-21"


def H(value:str)->str:
    return sha256(value.encode()).hexdigest()


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


def verified_separate_environment():
    e=deepcopy(SEPARATE_TEMPLATE)
    e["evidence_status"]="VERIFIED"
    e["environment_id"]="manual-pilot-env-001"
    e["environment_evidence_ref"]="diligence-room/manual-pilot-env-001"
    e["environment_evidence_sha256"]=H("environment-evidence")
    e["environment_configuration_sha256"]=H("configuration-snapshot")
    e["provider_or_host"]="controlled-host-001"
    e["verified_by_role"]="security-reviewer"
    e["verified_at"]="2026-09-20"
    e["valid_until"]="2026-10-20"
    for name,control in e["controls"].items():
        control["value"]=True
        control["evidence_ref"]="evidence/"+name
        control["evidence_sha256"]=H("control-"+name)
    return e


def verified_rights_manifest():
    manifest=deepcopy(RIGHTS)
    for entry in manifest["entries"]:
        repository=entry["repository"]
        entry["evidence_status"]="ATTACHED_VERIFIED"
        entry["evidence_location"]="diligence-room/"+repository
        entry["evidence_sha256"]=H("rights-"+repository)
        entry["scopes"]["commercial_use"]="CONFIRMED_ALLOWED"
    return manifest


def decide(request, *, dep=None, ready=None, separate=None, as_of=AS_OF, rights=None):
    return evaluate_launch(
        readiness=ready or readiness(),
        component_registry=REGISTRY,
        rights_manifest=verified_rights_manifest() if rights is None else rights,
        deployment_evidence=dep if dep is not None else DEPLOYMENT,
        request=request,
        separate_environment_evidence=separate,
        as_of_date=as_of,
    )


def test_buyer_readiness_does_not_override_current_deployment_security():
    d=decide(LaunchRequest(DataPath.CURRENT_DEPLOYMENT))
    assert d.status is LaunchStatus.BLOCKED
    assert d.route is LaunchRoute.DEPLOYED_PILOT_BLOCKED
    assert "deployment_team_mfa_not_enforced" in d.blockers
    assert "customer_data_plane_not_discovered" in d.blockers


def test_unattached_executed_rights_block_even_verified_separate_environment():
    d=decide(
        LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        separate=verified_separate_environment(),
        rights=RIGHTS,
    )
    assert d.status is LaunchStatus.BLOCKED
    assert d.route is LaunchRoute.SEPARATE_ENVIRONMENT_PENDING
    assert any("controlled pilot requires attached and verified" in x for x in d.blockers)


def test_stale_current_deployment_evidence_blocks_current_route():
    d=decide(
        LaunchRequest(DataPath.CURRENT_DEPLOYMENT),
        as_of="2026-09-28",
    )
    assert d.status is LaunchStatus.BLOCKED
    assert "deployment_evidence_expired" in d.blockers


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


def test_separate_environment_is_conditional_without_manifest():
    d=decide(LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT))
    assert d.status is LaunchStatus.CONDITIONAL
    assert d.route is LaunchRoute.SEPARATE_ENVIRONMENT_PENDING
    assert "separate_environment_evidence_manifest_missing" in d.conditions


def test_draft_separate_environment_stays_conditional():
    d=decide(
        LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        separate=SEPARATE_TEMPLATE,
    )
    assert d.status is LaunchStatus.CONDITIONAL
    assert "separate_environment_evidence_not_verified" in d.conditions


def test_verified_separate_environment_can_enable_manual_pilot():
    d=decide(
        LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        separate=verified_separate_environment(),
    )
    assert d.status is LaunchStatus.READY
    assert d.route is LaunchRoute.CONTROLLED_MANUAL_BLIND_PILOT


def test_expired_netlify_snapshot_does_not_block_independent_separate_environment():
    d=decide(
        LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        separate=verified_separate_environment(),
        as_of="2026-09-28",
    )
    assert d.status is LaunchStatus.READY
    assert "deployment_evidence_expired" not in d.blockers


def test_expired_separate_environment_becomes_conditional():
    e=verified_separate_environment()
    d=decide(
        LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        separate=e,
        as_of="2026-10-21",
    )
    assert d.status is LaunchStatus.CONDITIONAL
    assert "separate_environment_evidence_expired" in d.conditions


def test_malformed_separate_environment_blocks_instead_of_self_asserting():
    e=verified_separate_environment()
    e["controls"]="not-an-object"
    d=decide(
        LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        separate=e,
    )
    assert d.status is LaunchStatus.BLOCKED
    assert any(
        x.startswith("separate_environment_evidence_invalid:")
        for x in d.blockers
    )


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
