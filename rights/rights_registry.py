"""Canonical rights/provenance registry validator.

Operational consistency control only; it does not interpret legal agreements.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

EVIDENCE_CLASSES={
    "PUBLIC_LICENSE_VERIFIED","OWNER_ATTESTED","EXECUTED_PERMISSION_VERIFIED",
    "UNKNOWN_REVIEW","DENIED",
}
SCOPE_STATES={"ALLOWED","ALLOWED_WITH_CONDITIONS","DENIED","UNKNOWN_REVIEW","NOT_APPLICABLE"}
SCOPES={
    "commercial_use","hosted_saas","redistribution","assignment","sublicensing",
    "change_of_control","datasets","model_weights","bundled_assets","trademarks_patents",
}
SHA256=re.compile(r"^[0-9a-f]{64}$")


def load_registry(path: str|Path="rights/RIGHTS_REGISTRY.json")->dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_registry(registry:dict)->list[str]:
    errors=[]
    if registry.get("schema_version")!=1:
        errors.append("schema_version must be 1")
    if set(registry.get("evidence_classes") or [])!=EVIDENCE_CLASSES:
        errors.append("evidence_classes mismatch")
    if set(registry.get("scope_statuses") or [])!=SCOPE_STATES:
        errors.append("scope_statuses mismatch")
    if set(registry.get("scopes") or [])!=SCOPES:
        errors.append("scopes mismatch")

    assertions=registry.get("global_assertions") or []
    for a in assertions:
        if a.get("automatic_scope_effect") is not False:
            errors.append(f"{a.get('assertion_key')}: global assertion must not auto-resolve scopes")
        if a.get("evidence_class") not in EVIDENCE_CLASSES:
            errors.append(f"{a.get('assertion_key')}: invalid evidence class")

    seen=set()
    for subject in registry.get("subjects") or []:
        key=subject.get("subject_key")
        if not key or key in seen:
            errors.append(f"duplicate/missing subject_key: {key}")
            continue
        seen.add(key)
        scopes=subject.get("scopes") or {}
        if set(scopes)!=SCOPES:
            errors.append(f"{key}: incomplete scope set")
            continue
        for scope,state in scopes.items():
            status=state.get("status")
            klass=state.get("evidence_class")
            sha=state.get("evidence_sha256")
            if status not in SCOPE_STATES:
                errors.append(f"{key}:{scope}: invalid status")
            if klass is not None and klass not in EVIDENCE_CLASSES:
                errors.append(f"{key}:{scope}: invalid evidence class")
            if status in {"ALLOWED","ALLOWED_WITH_CONDITIONS","DENIED"} and klass is None:
                errors.append(f"{key}:{scope}: resolved state requires evidence class")
            if status=="UNKNOWN_REVIEW" and klass not in {None,"UNKNOWN_REVIEW"}:
                errors.append(f"{key}:{scope}: unknown scope cannot claim stronger evidence")
            if klass=="EXECUTED_PERMISSION_VERIFIED" and not (isinstance(sha,str) and SHA256.fullmatch(sha)):
                errors.append(f"{key}:{scope}: executed permission requires SHA-256")
    return errors


def stage_readiness(subject:dict,stage:str)->dict:
    required={
        "ANALYSIS":[],
        "CONTROLLED_PILOT":["commercial_use"],
        "HOSTED_SAAS":["commercial_use","hosted_saas"],
        "ACQUIRER_DILIGENCE":[
            "commercial_use","hosted_saas","redistribution",
            "assignment","sublicensing","change_of_control",
        ],
    }
    if stage not in required:
        raise ValueError("unsupported rights stage")
    if stage=="ANALYSIS":
        return {"state":"ANALYSIS_ONLY","missing_scopes":[],"denied_scopes":[],"conditional_scopes":[]}

    missing=[]; denied=[]; conditional=[]
    for scope in required[stage]:
        row=subject["scopes"][scope]
        status=row["status"]
        if status=="UNKNOWN_REVIEW":
            missing.append(scope)
        elif status=="DENIED":
            denied.append(scope)
        elif status=="ALLOWED_WITH_CONDITIONS":
            conditional.append(scope)
        elif status=="ALLOWED" and row.get("evidence_class") not in {
            "PUBLIC_LICENSE_VERIFIED","OWNER_ATTESTED","EXECUTED_PERMISSION_VERIFIED"
        }:
            missing.append(scope)

    state="BLOCKED" if denied or missing else ("CONDITIONAL" if conditional else "READY")
    return {
        "state":state,
        "missing_scopes":missing,
        "denied_scopes":denied,
        "conditional_scopes":conditional,
    }


if __name__=="__main__":
    data=load_registry()
    errors=validate_registry(data)
    print(json.dumps({"state":"BLOCKED" if errors else "CLEAR","errors":errors},indent=2))
    raise SystemExit(1 if errors else 0)
