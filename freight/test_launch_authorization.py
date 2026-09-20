from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from freight.deployment_security_evidence import load_current
from freight.launch_authorization import (
    authorization_is_valid,
    build_launch_authorization,
    verify_launch_authorization,
)
from freight.pilot_launch_gate import DataPath, LaunchRequest
from freight.readiness import PilotReadinessInput, assess_readiness
from freight.release_provenance import build_release_provenance
from freight.rights_evidence import load_json
from freight.separate_environment_evidence import load_environment


ROOT=Path(__file__).resolve().parents[1]
REGISTRY=load_json(ROOT/"freight/COMPONENT_RIGHTS_REGISTRY.json")
RIGHTS=load_json(ROOT/"freight/RIGHTS_EVIDENCE_MANIFEST.json")
DEPLOYMENT=load_current(ROOT)
TEMPLATE=load_environment(ROOT/"freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json")


def H(value:str)->str:
    return sha256(value.encode()).hexdigest()


def ready():
    return assess_readiness(PilotReadinessInput(
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
    ))


def verified_environment():
    e=deepcopy(TEMPLATE)
    e["evidence_status"]="VERIFIED"
    e["environment_id"]="manual-pilot-env-001"
    e["environment_evidence_ref"]="diligence-room/manual-pilot-env-001"
    e["environment_evidence_sha256"]=H("root")
    e["environment_configuration_sha256"]=H("config")
    e["provider_or_host"]="controlled-host"
    e["verified_by_role"]="security-reviewer"
    e["verified_at"]="2026-09-20"
    e["valid_until"]="2026-10-20"
    for name,control in e["controls"].items():
        control["value"]=True
        control["evidence_ref"]="evidence/"+name
        control["evidence_sha256"]=H(name)
    return e


def receipt():
    return build_launch_authorization(
        engagement_id="ENG-001",
        buyer_id="BUYER-A",
        business_unit="OPS",
        readiness=ready(),
        component_registry=REGISTRY,
        rights_manifest=RIGHTS,
        deployment_evidence=DEPLOYMENT,
        request=LaunchRequest(DataPath.SEPARATE_CONTROLLED_ENVIRONMENT),
        release_provenance=build_release_provenance(ROOT),
        separate_environment_evidence=verified_environment(),
        as_of_date="2026-09-21",
    )


def test_ready_launch_issues_deterministic_scope_bound_receipt():
    a=receipt()
    b=receipt()
    assert a==b
    assert a.engagement_id=="ENG-001"
    assert a.buyer_id=="BUYER-A"
    assert a.business_unit=="OPS"
    assert a.environment_scope_id=="manual-pilot-env-001"
    assert a.receipt_hash
    assert authorization_is_valid(a,as_of_date="2026-09-21")


def test_nonready_current_netlify_route_cannot_issue_receipt():
    with pytest.raises(ValueError,match="requires READY decision"):
        build_launch_authorization(
            engagement_id="ENG-001",
            buyer_id="BUYER-A",
            business_unit="OPS",
            readiness=ready(),
            component_registry=REGISTRY,
            rights_manifest=RIGHTS,
            deployment_evidence=DEPLOYMENT,
            request=LaunchRequest(DataPath.CURRENT_DEPLOYMENT),
            release_provenance=build_release_provenance(ROOT),
            as_of_date="2026-09-21",
        )


def test_receipt_expires_with_environment_evidence():
    r=receipt()
    assert "launch_authorization_expired" in verify_launch_authorization(
        r,as_of_date="2026-10-21"
    )


def test_receipt_hash_detects_tampering():
    r=receipt()
    tampered=r.__class__(
        **{
            **r.__dict__,
            "business_unit":"OTHER",
        }
    )
    assert "launch_authorization_hash_mismatch" in verify_launch_authorization(
        tampered,as_of_date="2026-09-21"
    )
