"""Validate Freight deployment-security evidence without allowing missing controls to masquerade as passes."""
from __future__ import annotations

import json
from pathlib import Path


CROSS_TENANT_STATES={
    "UNPROVEN_NO_MULTI_TENANT_DATA_PLANE_DISCOVERED",
    "PROVEN",
}
PARSER_STATES={
    "UNPROVEN_NO_PARSER_RUNTIME_DISCOVERED",
    "PROVEN",
}


def validate_evidence(evidence: dict) -> list[str]:
    errors=[]
    target=evidence.get("target") or {}
    if not target.get("provider") or not target.get("project_name") or not target.get("site_id"):
        errors.append("target provider/project_name/site_id required")

    access=evidence.get("access_control") or {}
    if access.get("status")=="CONFIG_PROVEN":
        if access.get("sso_team_login_required") is not True:
            errors.append("CONFIG_PROVEN access requires sso_team_login_required=true")
        if "team_mfa_enforced" not in access:
            errors.append("CONFIG_PROVEN access must record MFA enforcement state")

    tenant=evidence.get("cross_tenant_isolation") or {}
    if tenant.get("status") not in CROSS_TENANT_STATES:
        errors.append("invalid cross_tenant_isolation status")
    if tenant.get("status")=="PROVEN":
        if not tenant.get("data_plane_id"):
            errors.append("PROVEN cross-tenant isolation requires data_plane_id")
        if int(tenant.get("distinct_tenant_probe_count") or 0)<2:
            errors.append("PROVEN cross-tenant isolation requires at least two tenant probes")
        if tenant.get("negative_cross_tenant_probe_passed") is not True:
            errors.append("PROVEN cross-tenant isolation requires passed negative probe")

    parser=evidence.get("parser_sandbox") or {}
    if parser.get("status") not in PARSER_STATES:
        errors.append("invalid parser_sandbox status")
    if parser.get("status")=="PROVEN":
        if not parser.get("runtime_provider"):
            errors.append("PROVEN parser sandbox requires runtime_provider")
        for key in (
            "cpu_limit_evidence_ref",
            "memory_limit_evidence_ref",
            "time_limit_evidence_ref",
            "network_isolation_evidence_ref",
            "credential_isolation_evidence_ref",
        ):
            if not parser.get(key):
                errors.append("PROVEN parser sandbox requires "+key)

    findings=evidence.get("findings") or []
    ids=[f.get("id") for f in findings]
    if len(ids)!=len(set(ids)):
        errors.append("duplicate finding ids")
    return errors


def load_current(root: Path | None=None) -> dict:
    root=root or Path(__file__).resolve().parents[1]
    return json.loads(
        (root/"freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json").read_text(encoding="utf-8")
    )


if __name__=="__main__":
    current=load_current()
    errors=validate_evidence(current)
    print(json.dumps({"errors":errors},indent=2))
    raise SystemExit(1 if errors else 0)
