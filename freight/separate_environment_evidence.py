"""Validate a separate controlled Freight pilot environment.

A separate/manual pilot route may not become READY from a boolean assertion.
It requires a structured evidence manifest whose controls are explicitly
verified and source-referenced.
"""
from __future__ import annotations

import json
from pathlib import Path

EVIDENCE_STATUSES={"DRAFT","VERIFIED"}
TENANT_STATES={"NOT_APPLICABLE","PROVEN"}
PARSER_STATES={"NOT_APPLICABLE","PROVEN"}

BASE_CONTROLS=(
    "mfa_enforced",
    "encrypted_at_rest",
    "encrypted_in_transit",
    "access_scope_defined",
    "read_only_ingestion",
    "retention_defined",
    "deletion_defined",
    "customer_data_excluded_from_current_netlify",
)


def _text(value)->bool:
    return isinstance(value,str) and bool(value.strip())


def validate_environment_evidence(evidence:dict)->tuple[list[str],list[str]]:
    errors=[]
    conditions=[]

    if evidence.get("schema_version")!=1:
        errors.append("schema_version must be 1")

    status=evidence.get("evidence_status")
    if status not in EVIDENCE_STATUSES:
        errors.append("invalid evidence_status")
        return errors,conditions

    if status!="VERIFIED":
        conditions.append("separate_environment_evidence_not_verified")

    environment_id=evidence.get("environment_id")
    if not _text(environment_id) or environment_id=="REPLACE_WITH_UNIQUE_ENVIRONMENT_ID":
        conditions.append("separate_environment_id_not_final")

    if not _text(evidence.get("environment_evidence_ref")):
        conditions.append("separate_environment_evidence_ref_missing")

    if not _text(evidence.get("provider_or_host")):
        conditions.append("separate_environment_provider_or_host_missing")

    controls=evidence.get("controls")
    if not isinstance(controls,dict):
        errors.append("controls must be an object")
        return errors,conditions

    for name in BASE_CONTROLS:
        control=controls.get(name)
        if not isinstance(control,dict):
            errors.append(name+" control must be an object")
            continue
        if control.get("value") is not True:
            conditions.append(name+"_not_proven")
        if not _text(control.get("evidence_ref")):
            conditions.append(name+"_evidence_ref_missing")

    single_tenant=evidence.get("single_tenant")
    if not isinstance(single_tenant,bool):
        errors.append("single_tenant must be boolean")
    elif single_tenant is False:
        tenant=evidence.get("multi_tenant_isolation") or {}
        if tenant.get("status") not in TENANT_STATES:
            errors.append("invalid multi_tenant_isolation status")
        if tenant.get("status")!="PROVEN":
            conditions.append("separate_environment_cross_tenant_isolation_not_proven")
        if not _text(tenant.get("evidence_ref")):
            conditions.append("separate_environment_cross_tenant_evidence_ref_missing")

    parser_used=evidence.get("parser_runtime_used")
    if not isinstance(parser_used,bool):
        errors.append("parser_runtime_used must be boolean")
    elif parser_used is True:
        parser=evidence.get("parser_sandbox") or {}
        if parser.get("status") not in PARSER_STATES:
            errors.append("invalid parser_sandbox status")
        if parser.get("status")!="PROVEN":
            conditions.append("separate_environment_parser_sandbox_not_proven")
        for key in (
            "cpu_limit_evidence_ref",
            "memory_limit_evidence_ref",
            "time_limit_evidence_ref",
            "network_isolation_evidence_ref",
            "credential_isolation_evidence_ref",
        ):
            if not _text(parser.get(key)):
                conditions.append("separate_environment_"+key+"_missing")

    return errors,sorted(set(conditions))


def environment_is_verified(evidence:dict)->bool:
    errors,conditions=validate_environment_evidence(evidence)
    return (
        evidence.get("evidence_status")=="VERIFIED"
        and not errors
        and not conditions
    )


def load_environment(path:str|Path)->dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="freight/SEPARATE_ENVIRONMENT_EVIDENCE_TEMPLATE.json",
    )
    parser.add_argument("--expect",choices=("VERIFIED","CONDITIONAL"))
    args=parser.parse_args()
    evidence=load_environment(args.path)
    errors,conditions=validate_environment_evidence(evidence)
    state="VERIFIED" if environment_is_verified(evidence) else "CONDITIONAL"
    print(json.dumps({
        "state":state,
        "errors":errors,
        "conditions":conditions,
    },indent=2))
    if errors:
        raise SystemExit(1)
    if args.expect and state!=args.expect:
        raise SystemExit(f"expected {args.expect}, got {state}")
