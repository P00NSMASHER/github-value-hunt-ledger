from copy import deepcopy
from pathlib import Path

from freight.separate_environment_evidence import (
    environment_is_verified,
    load_environment,
    validate_environment_evidence,
)

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=load_environment(
    ROOT/"freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json"
)


def verified_base():
    e=deepcopy(TEMPLATE)
    e["evidence_status"]="VERIFIED"
    e["environment_id"]="manual-pilot-env-001"
    e["environment_evidence_ref"]="diligence-room/manual-pilot-env-001"
    e["provider_or_host"]="controlled-host-001"
    for control in e["controls"].values():
        control["value"]=True
        control["evidence_ref"]="evidence/"+str(len(control["evidence_ref"] or ""))+"ref"
    return e


def test_template_is_structurally_valid_but_not_verified():
    errors,conditions=validate_environment_evidence(TEMPLATE)
    assert errors==[]
    assert environment_is_verified(TEMPLATE) is False
    assert "separate_environment_evidence_not_verified" in conditions


def test_verified_single_tenant_no_parser_environment_can_pass():
    e=verified_base()
    errors,conditions=validate_environment_evidence(e)
    assert errors==[]
    assert conditions==[]
    assert environment_is_verified(e) is True


def test_multi_tenant_environment_requires_isolation_evidence():
    e=verified_base()
    e["single_tenant"]=False
    errors,conditions=validate_environment_evidence(e)
    assert errors==[]
    assert "separate_environment_cross_tenant_isolation_not_proven" in conditions

    e["multi_tenant_isolation"]={
        "status":"PROVEN",
        "evidence_ref":"evidence/tenant-negative-test",
    }
    errors,conditions=validate_environment_evidence(e)
    assert errors==[]
    assert conditions==[]


def test_parser_environment_requires_full_sandbox_evidence():
    e=verified_base()
    e["parser_runtime_used"]=True
    errors,conditions=validate_environment_evidence(e)
    assert errors==[]
    assert "separate_environment_parser_sandbox_not_proven" in conditions
    assert "separate_environment_network_isolation_evidence_ref_missing" in conditions

    e["parser_sandbox"]={
        "status":"PROVEN",
        "cpu_limit_evidence_ref":"evidence/cpu",
        "memory_limit_evidence_ref":"evidence/memory",
        "time_limit_evidence_ref":"evidence/time",
        "network_isolation_evidence_ref":"evidence/network",
        "credential_isolation_evidence_ref":"evidence/credentials",
    }
    errors,conditions=validate_environment_evidence(e)
    assert errors==[]
    assert conditions==[]


def test_missing_base_control_reference_prevents_verification():
    e=verified_base()
    e["controls"]["mfa_enforced"]["evidence_ref"]=None
    errors,conditions=validate_environment_evidence(e)
    assert errors==[]
    assert "mfa_enforced_evidence_ref_missing" in conditions
    assert environment_is_verified(e) is False
