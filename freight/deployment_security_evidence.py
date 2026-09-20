"""Validate Freight deployment-security evidence without allowing stale or missing controls to masquerade as passes."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path


CROSS_TENANT_STATES={
    "UNPROVEN_NO_MULTI_TENANT_DATA_PLANE_DISCOVERED",
    "PROVEN",
}
PARSER_STATES={
    "UNPROVEN_NO_PARSER_RUNTIME_DISCOVERED",
    "PROVEN",
}


def _text(value)->bool:
    return isinstance(value,str) and bool(value.strip())


def _date(value, *, field:str, errors:list[str])->date|None:
    if isinstance(value,date):
        return value
    if not _text(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(field+"_must_be_iso_date")
        return None


def _today_utc()->date:
    return datetime.now(timezone.utc).date()


def validate_evidence(evidence: dict) -> list[str]:
    errors=[]
    target=evidence.get("target") or {}
    if not target.get("provider") or not target.get("project_name") or not target.get("site_id"):
        errors.append("target provider/project_name/site_id required")

    collected=_date(evidence.get("collected_at"),field="collected_at",errors=errors)
    valid_until=_date(evidence.get("valid_until"),field="valid_until",errors=errors)
    if collected is None:
        errors.append("collected_at required")
    if valid_until is None:
        errors.append("valid_until required")
    if collected is not None and valid_until is not None and valid_until<collected:
        errors.append("valid_until_before_collected_at")

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


def evidence_conditions(
    evidence:dict,
    *,
    as_of_date:date|str|None=None,
)->list[str]:
    errors=[]
    collected=_date(evidence.get("collected_at"),field="collected_at",errors=errors)
    valid_until=_date(evidence.get("valid_until"),field="valid_until",errors=errors)
    if errors or collected is None or valid_until is None:
        return ["deployment_evidence_freshness_unverifiable"]
    as_of=_date(as_of_date,field="as_of_date",errors=errors) if as_of_date is not None else _today_utc()
    if errors or as_of is None:
        return ["deployment_evidence_as_of_invalid"]
    conditions=[]
    if as_of<collected:
        conditions.append("deployment_evidence_observation_in_future")
    if as_of>valid_until:
        conditions.append("deployment_evidence_expired")
    return conditions


def load_current(root: Path | None=None) -> dict:
    root=root or Path(__file__).resolve().parents[1]
    return json.loads(
        (root/"freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json").read_text(encoding="utf-8")
    )


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--as-of-date")
    parser.add_argument("--expect",choices=("FRESH","STALE"))
    args=parser.parse_args()
    current=load_current()
    errors=validate_evidence(current)
    conditions=evidence_conditions(current,as_of_date=args.as_of_date)
    state="FRESH" if not conditions else "STALE"
    print(json.dumps({"state":state,"errors":errors,"conditions":conditions},indent=2))
    if errors:
        raise SystemExit(1)
    if args.expect and state!=args.expect:
        raise SystemExit(f"expected {args.expect}, got {state}")
