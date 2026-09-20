from copy import deepcopy
from hashlib import sha256
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
AS_OF="2026-09-21"


def H(value:str)->str:
    return sha256(value.encode()).hexdigest()


def verified_base():
    e=deepcopy(TEMPLATE)
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


def test_template_is_structurally_valid_but_not_verified():
    errors,conditions=validate_environment_evidence(TEMPLATE,as_of_date=AS_OF)
    assert errors==[]
    assert environment_is_verified(TEMPLATE,as_of_date=AS_OF) is False
    assert "separate_environment_evidence_not_verified" in conditions


def test_verified_single_tenant_no_parser_environment_can_pass():
    e=verified_base()
    errors,conditions=validate_environment_evidence(e,as_of_date=AS_OF)
    assert errors==[]
    assert conditions==[]
    assert environment_is_verified(e,as_of_date=AS_OF) is True


def test_plain_reference_without_hash_cannot_verify():
    e=verified_base()
    e["controls"]["mfa_enforced"]["evidence_sha256"]=None
    errors,conditions=validate_environment_evidence(e,as_of_date=AS_OF)
    assert errors==[]
    assert "mfa_enforced_evidence_sha256_missing_or_invalid" in conditions
    assert environment_is_verified(e,as_of_date=AS_OF) is False


def test_expired_environment_evidence_becomes_conditional():
    e=verified_base()
    errors,conditions=validate_environment_evidence(
        e,
        as_of_date="2026-10-21",
    )
    assert errors==[]
    assert "separate_environment_evidence_expired" in conditions
    assert environment_is_verified(e,as_of_date="2026-10-21") is False


def test_overlong_verification_window_is_conditional():
    e=verified_base()
    e["valid_until"]="2027-01-31"
    errors,conditions=validate_environment_evidence(e,as_of_date=AS_OF)
    assert errors==[]
    assert "separate_environment_verification_window_exceeds_90_days" in conditions


def test_multi_tenant_environment_requires_hashed_isolation_evidence():
    e=verified_base()
    e["single_tenant"]=False
    errors,conditions=validate_environment_evidence(e,as_of_date=AS_OF)
    assert errors==[]
    assert "separate_environment_cross_tenant_isolation_not_proven" in conditions

    e["multi_tenant_isolation"]={
        "status":"PROVEN",
        "evidence_ref":"evidence/tenant-negative-test",
        "evidence_sha256":H("tenant-negative-test"),
    }
    errors,conditions=validate_environment_evidence(e,as_of_date=AS_OF)
    assert errors==[]
    assert conditions==[]


def test_parser_environment_requires_hashed_sandbox_evidence():
    e=verified_base()
    e["parser_runtime_used"]=True
    errors,conditions=validate_environment_evidence(e,as_of_date=AS_OF)
    assert errors==[]
    assert "separate_environment_parser_sandbox_not_proven" in conditions
    assert "separate_environment_network_isolation_evidence_sha256_missing_or_invalid" in conditions

    e["parser_sandbox"]={
        "status":"PROVEN",
        "cpu_limit_evidence_ref":"evidence/cpu",
        "cpu_limit_evidence_sha256":H("cpu"),
        "memory_limit_evidence_ref":"evidence/memory",
        "memory_limit_evidence_sha256":H("memory"),
        "time_limit_evidence_ref":"evidence/time",
        "time_limit_evidence_sha256":H("time"),
        "network_isolation_evidence_ref":"evidence/network",
        "network_isolation_evidence_sha256":H("network"),
        "credential_isolation_evidence_ref":"evidence/credentials",
        "credential_isolation_evidence_sha256":H("credentials"),
    }
    errors,conditions=validate_environment_evidence(e,as_of_date=AS_OF)
    assert errors==[]
    assert conditions==[]


def test_bad_iso_date_is_structural_error():
    e=verified_base()
    e["verified_at"]="20-09-2026"
    errors,_=validate_environment_evidence(e,as_of_date=AS_OF)
    assert "verified_at_must_be_iso_date" in errors
