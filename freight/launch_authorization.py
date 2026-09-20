"""Deterministic launch-authorization receipt for Freight Recovery.

A receipt is issued only by re-running the final launch gate from its raw
inputs. It binds a READY decision to one engagement, buyer/BU scope, release
provenance, rights state, data path and environment evidence snapshot.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone

from freight.contracts import canonical_hash
from freight.pilot_launch_gate import (
    DataPath,
    LaunchRequest,
    LaunchRoute,
    LaunchStatus,
    evaluate_launch,
)
from freight.readiness import ReadinessAssessment


SHA256_RE=re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LaunchAuthorizationReceipt:
    engagement_id: str
    buyer_id: str
    business_unit: str
    data_path: str
    launch_route: str
    requires_multi_tenant_data_plane: bool
    requires_parser_runtime: bool
    environment_scope_id: str
    issued_on: str
    valid_until: str
    readiness_hash: str
    launch_request_hash: str
    launch_decision_hash: str
    release_provenance_hash: str
    component_registry_hash: str
    rights_evidence_hash: str
    environment_evidence_hash: str
    receipt_hash: str


def _text(name:str,value:str)->None:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(name+" is required")


def _sha(name:str,value:str|None)->None:
    if not isinstance(value,str) or SHA256_RE.fullmatch(value) is None:
        raise ValueError(name+" must be lowercase SHA-256")


def _parse_date(value:str, *, name:str)->date:
    _text(name,value)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(name+" must be ISO date") from exc


def _today()->date:
    return datetime.now(timezone.utc).date()


def _readiness_body(readiness:ReadinessAssessment)->dict:
    body=asdict(readiness)
    body["status"]=readiness.status.value
    return body


def _request_body(request:LaunchRequest)->dict:
    return {
        "data_path":request.data_path.value,
        "requires_multi_tenant_data_plane":request.requires_multi_tenant_data_plane,
        "requires_parser_runtime":request.requires_parser_runtime,
    }


def _decision_body(decision)->dict:
    return {
        "status":decision.status.value,
        "route":decision.route.value,
        "blockers":list(decision.blockers),
        "conditions":list(decision.conditions),
        "warnings":list(decision.warnings),
    }


def _receipt_body(receipt:LaunchAuthorizationReceipt)->dict:
    body=asdict(receipt)
    body.pop("receipt_hash")
    return {"schema":1,**body}


def build_launch_authorization(
    *,
    engagement_id:str,
    buyer_id:str,
    business_unit:str,
    readiness:ReadinessAssessment,
    component_registry:dict,
    rights_manifest:dict,
    deployment_evidence:dict|None,
    request:LaunchRequest,
    release_provenance:dict,
    separate_environment_evidence:dict|None=None,
    as_of_date:str,
)->LaunchAuthorizationReceipt:
    for name,value in (
        ("engagement_id",engagement_id),
        ("buyer_id",buyer_id),
        ("business_unit",business_unit),
    ):
        _text(name,value)

    decision=evaluate_launch(
        readiness=readiness,
        component_registry=component_registry,
        rights_manifest=rights_manifest,
        deployment_evidence=deployment_evidence,
        request=request,
        separate_environment_evidence=separate_environment_evidence,
        as_of_date=as_of_date,
    )
    if decision.status is not LaunchStatus.READY:
        reasons=list(decision.blockers)+list(decision.conditions)
        raise ValueError(
            "launch authorization requires READY decision"
            + (": "+",".join(reasons) if reasons else "")
        )

    if request.data_path is DataPath.CURRENT_DEPLOYMENT:
        if decision.route is not LaunchRoute.DEPLOYED_BLIND_PILOT:
            raise ValueError("READY current deployment route mismatch")
        if deployment_evidence is None:
            raise ValueError("deployment evidence required")
        environment=deployment_evidence
        scope=(environment.get("target") or {}).get("site_id")
    else:
        if decision.route is not LaunchRoute.CONTROLLED_MANUAL_BLIND_PILOT:
            raise ValueError("READY separate environment route mismatch")
        if separate_environment_evidence is None:
            raise ValueError("separate environment evidence required")
        environment=separate_environment_evidence
        scope=environment.get("environment_id")

    _text("environment_scope_id",scope)
    valid_until=environment.get("valid_until")
    _text("environment valid_until",valid_until)
    issued=_parse_date(as_of_date,name="as_of_date")
    expiry=_parse_date(valid_until,name="environment valid_until")
    if issued>expiry:
        raise ValueError("environment evidence expired before authorization")

    release_hash=release_provenance.get("provenance_hash")
    _sha("release provenance hash",release_hash)

    preliminary={
        "engagement_id":engagement_id,
        "buyer_id":buyer_id,
        "business_unit":business_unit,
        "data_path":request.data_path.value,
        "launch_route":decision.route.value,
        "requires_multi_tenant_data_plane":request.requires_multi_tenant_data_plane,
        "requires_parser_runtime":request.requires_parser_runtime,
        "environment_scope_id":scope,
        "issued_on":issued.isoformat(),
        "valid_until":expiry.isoformat(),
        "readiness_hash":canonical_hash(_readiness_body(readiness)),
        "launch_request_hash":canonical_hash(_request_body(request)),
        "launch_decision_hash":canonical_hash(_decision_body(decision)),
        "release_provenance_hash":release_hash,
        "component_registry_hash":canonical_hash(component_registry),
        "rights_evidence_hash":canonical_hash(rights_manifest),
        "environment_evidence_hash":canonical_hash(environment),
    }
    receipt_hash=canonical_hash({"schema":1,**preliminary})
    return LaunchAuthorizationReceipt(**preliminary,receipt_hash=receipt_hash)


def verify_launch_authorization(
    receipt:LaunchAuthorizationReceipt,
    *,
    as_of_date:str|None=None,
)->list[str]:
    errors=[]
    for name in ("engagement_id","buyer_id","business_unit","environment_scope_id"):
        value=getattr(receipt,name)
        if not isinstance(value,str) or not value.strip():
            errors.append(name+"_missing")

    if receipt.data_path not in {x.value for x in DataPath}:
        errors.append("invalid_data_path")
    if receipt.launch_route not in {
        LaunchRoute.DEPLOYED_BLIND_PILOT.value,
        LaunchRoute.CONTROLLED_MANUAL_BLIND_PILOT.value,
    }:
        errors.append("invalid_ready_launch_route")

    expected_route=(
        LaunchRoute.DEPLOYED_BLIND_PILOT.value
        if receipt.data_path==DataPath.CURRENT_DEPLOYMENT.value
        else LaunchRoute.CONTROLLED_MANUAL_BLIND_PILOT.value
    )
    if receipt.launch_route!=expected_route:
        errors.append("data_path_launch_route_mismatch")

    for name in (
        "readiness_hash",
        "launch_request_hash",
        "launch_decision_hash",
        "release_provenance_hash",
        "component_registry_hash",
        "rights_evidence_hash",
        "environment_evidence_hash",
        "receipt_hash",
    ):
        value=getattr(receipt,name)
        if not isinstance(value,str) or SHA256_RE.fullmatch(value) is None:
            errors.append(name+"_invalid")

    try:
        issued=_parse_date(receipt.issued_on,name="issued_on")
        expiry=_parse_date(receipt.valid_until,name="valid_until")
        if expiry<issued:
            errors.append("authorization_expiry_before_issue")
        as_of=_parse_date(as_of_date,name="as_of_date") if as_of_date else _today()
        if as_of<issued:
            errors.append("authorization_issued_in_future")
        if as_of>expiry:
            errors.append("launch_authorization_expired")
    except ValueError as exc:
        errors.append(str(exc))

    if canonical_hash(_receipt_body(receipt))!=receipt.receipt_hash:
        errors.append("launch_authorization_hash_mismatch")
    return sorted(set(errors))


def authorization_is_valid(
    receipt:LaunchAuthorizationReceipt,
    *,
    as_of_date:str|None=None,
)->bool:
    return not verify_launch_authorization(receipt,as_of_date=as_of_date)
