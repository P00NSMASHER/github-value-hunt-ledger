"""Validate a separate controlled Freight pilot environment.

A separate/manual pilot route may not become READY from a boolean assertion or
an unanchored evidence-reference string. VERIFIED status requires SHA-256
receipts, configuration fingerprinting, verifier metadata, and fresh evidence.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path


EVIDENCE_STATUSES={"DRAFT","VERIFIED"}
TENANT_STATES={"NOT_APPLICABLE","PROVEN"}
PARSER_STATES={"NOT_APPLICABLE","PROVEN"}
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")
MAX_VERIFICATION_DAYS=90

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


def _sha(value)->bool:
    return isinstance(value,str) and SHA256_RE.fullmatch(value) is not None


def _coerce_date(value, *, field:str, errors:list[str])->date|None:
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


def validate_environment_evidence(
    evidence:dict,
    *,
    as_of_date:date|str|None=None,
)->tuple[list[str],list[str]]:
    errors=[]
    conditions=[]

    if evidence.get("schema_version")!=2:
        errors.append("schema_version must be 2")

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
    if not _sha(evidence.get("environment_evidence_sha256")):
        conditions.append("separate_environment_evidence_sha256_missing_or_invalid")
    if not _sha(evidence.get("environment_configuration_sha256")):
        conditions.append("separate_environment_configuration_sha256_missing_or_invalid")

    if not _text(evidence.get("provider_or_host")):
        conditions.append("separate_environment_provider_or_host_missing")
    if not _text(evidence.get("verified_by_role")):
        conditions.append("separate_environment_verified_by_role_missing")

    verified_at=_coerce_date(
        evidence.get("verified_at"),
        field="verified_at",
        errors=errors,
    )
    valid_until=_coerce_date(
        evidence.get("valid_until"),
        field="valid_until",
        errors=errors,
    )
    as_of=_coerce_date(
        as_of_date,
        field="as_of_date",
        errors=errors,
    ) if as_of_date is not None else _today_utc()

    if verified_at is None:
        conditions.append("separate_environment_verified_at_missing")
    if valid_until is None:
        conditions.append("separate_environment_valid_until_missing")

    if verified_at is not None and valid_until is not None:
        if valid_until < verified_at:
            errors.append("valid_until_before_verified_at")
        elif (valid_until-verified_at).days>MAX_VERIFICATION_DAYS:
            conditions.append("separate_environment_verification_window_exceeds_90_days")

    if verified_at is not None and as_of is not None and as_of<verified_at:
        conditions.append("separate_environment_verification_in_future")
    if valid_until is not None and as_of is not None and as_of>valid_until:
        conditions.append("separate_environment_evidence_expired")

    controls=evidence.get("controls")
    if not isinstance(controls,dict):
        errors.append("controls must be an object")
        return errors,sorted(set(conditions))

    for name in BASE_CONTROLS:
        control=controls.get(name)
        if not isinstance(control,dict):
            errors.append(name+" control must be an object")
            continue
        if control.get("value") is not True:
            conditions.append(name+"_not_proven")
        if not _text(control.get("evidence_ref")):
            conditions.append(name+"_evidence_ref_missing")
        if not _sha(control.get("evidence_sha256")):
            conditions.append(name+"_evidence_sha256_missing_or_invalid")

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
        if not _sha(tenant.get("evidence_sha256")):
            conditions.append("separate_environment_cross_tenant_evidence_sha256_missing_or_invalid")

    parser_used=evidence.get("parser_runtime_used")
    if not isinstance(parser_used,bool):
        errors.append("parser_runtime_used must be boolean")
    elif parser_used is True:
        parser=evidence.get("parser_sandbox") or {}
        if parser.get("status") not in PARSER_STATES:
            errors.append("invalid parser_sandbox status")
        if parser.get("status")!="PROVEN":
            conditions.append("separate_environment_parser_sandbox_not_proven")
        for base in (
            "cpu_limit",
            "memory_limit",
            "time_limit",
            "network_isolation",
            "credential_isolation",
        ):
            ref_key=base+"_evidence_ref"
            sha_key=base+"_evidence_sha256"
            if not _text(parser.get(ref_key)):
                conditions.append("separate_environment_"+ref_key+"_missing")
            if not _sha(parser.get(sha_key)):
                conditions.append("separate_environment_"+sha_key+"_missing_or_invalid")

    return errors,sorted(set(conditions))


def environment_is_verified(
    evidence:dict,
    *,
    as_of_date:date|str|None=None,
)->bool:
    errors,conditions=validate_environment_evidence(
        evidence,
        as_of_date=as_of_date,
    )
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
    parser.add_argument("--as-of-date")
    parser.add_argument("--expect",choices=("VERIFIED","CONDITIONAL"))
    args=parser.parse_args()
    evidence=load_environment(args.path)
    errors,conditions=validate_environment_evidence(
        evidence,
        as_of_date=args.as_of_date,
    )
    state="VERIFIED" if environment_is_verified(
        evidence,
        as_of_date=args.as_of_date,
    ) else "CONDITIONAL"
    print(json.dumps({
        "state":state,
        "errors":errors,
        "conditions":conditions,
    },indent=2))
    if errors:
        raise SystemExit(1)
    if args.expect and state!=args.expect:
        raise SystemExit(f"expected {args.expect}, got {state}")
