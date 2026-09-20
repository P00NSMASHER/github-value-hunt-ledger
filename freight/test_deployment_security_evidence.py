from copy import deepcopy

from freight.deployment_security_evidence import (
    evidence_conditions,
    load_current,
    validate_evidence,
)


def test_current_deployment_evidence_is_valid_and_conservative():
    evidence=load_current()
    assert validate_evidence(evidence)==[]
    assert evidence_conditions(evidence,as_of_date="2026-09-20")==[]
    assert evidence["access_control"]["status"]=="CONFIG_PROVEN"
    assert evidence["cross_tenant_isolation"]["status"].startswith("UNPROVEN")
    assert evidence["parser_sandbox"]["status"].startswith("UNPROVEN")


def test_current_deployment_evidence_expires():
    evidence=load_current()
    conditions=evidence_conditions(evidence,as_of_date="2026-09-28")
    assert "deployment_evidence_expired" in conditions


def test_cross_tenant_cannot_be_marked_proven_without_dual_tenant_probe():
    evidence=deepcopy(load_current())
    evidence["cross_tenant_isolation"]["status"]="PROVEN"
    errors=validate_evidence(evidence)
    assert any("data_plane_id" in x for x in errors)
    assert any("at least two tenant probes" in x for x in errors)
    assert any("negative probe" in x for x in errors)


def test_parser_cannot_be_marked_proven_without_runtime_boundaries():
    evidence=deepcopy(load_current())
    evidence["parser_sandbox"]["status"]="PROVEN"
    errors=validate_evidence(evidence)
    assert any("runtime_provider" in x for x in errors)
    assert any("network_isolation_evidence_ref" in x for x in errors)


def test_invalid_freshness_dates_fail_structurally():
    evidence=deepcopy(load_current())
    evidence["valid_until"]="09/27/2026"
    errors=validate_evidence(evidence)
    assert "valid_until_must_be_iso_date" in errors


def test_real_mfa_gap_is_preserved():
    evidence=load_current()
    assert evidence["access_control"]["team_mfa_enforced"] is False
    assert any(
        f["id"]=="DEP-SEC-001" and f["status"]=="OPEN"
        for f in evidence["findings"]
    )
