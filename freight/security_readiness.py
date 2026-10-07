"""Validate Phase 3 Step 1 RecoveryOS security-readiness evidence.

This validator separates internally evidenced controls from external assurance.
It intentionally refuses to treat readiness work as SOC 2, ISO 27001, a
penetration test, provider encryption proof, or provider backup/restore proof.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


PROVEN = "PROVEN"
PARTIAL = "PARTIAL"
PENDING_EXTERNAL = "PENDING_EXTERNAL"
NOT_APPLICABLE = "NOT_APPLICABLE"
VALID_STATES = {PROVEN, PARTIAL, PENDING_EXTERNAL, NOT_APPLICABLE}

EXTERNAL_CONTROLS = {
    "mfa",
    "enterprise_sso",
    "independent_penetration_test",
    "soc2_type2",
    "iso27001",
    "provider_encryption_evidence",
    "provider_backup_restore_evidence",
}


@dataclass(frozen=True)
class SecurityReadinessSummary:
    proven: int
    partial: int
    pending_external: int
    not_applicable: int
    external_required: tuple[str, ...]


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_security_readiness(payload: dict) -> list[str]:
    errors: list[str] = []
    target = payload.get("target") or {}
    for key in ("provider", "project_id", "production_url", "data_plane"):
        if not _text(target.get(key)):
            errors.append(f"target.{key} required")

    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    controls = payload.get("controls")
    if not isinstance(controls, dict) or not controls:
        return errors + ["controls must be a non-empty object"]

    for name, control in controls.items():
        if not isinstance(control, dict):
            errors.append(f"control {name} must be an object")
            continue
        state = control.get("state")
        if state not in VALID_STATES:
            errors.append(f"control {name} has invalid state")
        if not _text(control.get("evidence")):
            errors.append(f"control {name} requires evidence/boundary text")

    authentication = controls.get("authentication") or {}
    if authentication.get("state") == PROVEN:
        facts = authentication.get("facts") or {}
        if facts.get("password_min_length", 0) < 12:
            errors.append("PROVEN authentication requires password minimum >=12")
        if facts.get("secure_cookie") is not True:
            errors.append("PROVEN authentication requires Secure cookie")
        if facts.get("httponly_cookie") is not True:
            errors.append("PROVEN authentication requires HttpOnly cookie")
        if facts.get("same_site") not in {"Lax", "Strict"}:
            errors.append("PROVEN authentication requires SameSite protection")
        if int(facts.get("session_max_hours") or 0) > 24:
            errors.append("PROVEN authentication session exceeds 24 hours")
        if facts.get("case_insensitive_unique_email") is not True:
            errors.append("PROVEN authentication requires case-insensitive unique email")
        if facts.get("login_rate_limit") is not True:
            errors.append("PROVEN authentication requires login rate limiting")

    tenant = controls.get("cross_tenant_isolation") or {}
    if tenant.get("state") == PROVEN:
        facts = tenant.get("facts") or {}
        if int(facts.get("distinct_tenants_tested") or 0) < 2:
            errors.append("PROVEN cross-tenant isolation requires >=2 tenants")
        if facts.get("negative_cross_tenant_insert_rejected") is not True:
            errors.append("PROVEN cross-tenant isolation requires rejected negative probe")

    audit = controls.get("tamper_evident_audit_chain") or {}
    if audit.get("state") == PROVEN:
        facts = audit.get("facts") or {}
        if int(facts.get("synthetic_events_verified") or 0) < 1:
            errors.append("PROVEN audit chain requires verified synthetic events")
        if int(facts.get("invalid_hashes") or -1) != 0:
            errors.append("PROVEN audit chain requires zero invalid hashes")
        if int(facts.get("broken_links") or -1) != 0:
            errors.append("PROVEN audit chain requires zero broken links")

    api_keys = controls.get("api_key_security") or {}
    if api_keys.get("state") == PROVEN:
        facts = api_keys.get("facts") or {}
        if facts.get("stored_hashed_only") is not True:
            errors.append("PROVEN API key security requires hash-only storage")
        if facts.get("scopes_separated") is not True:
            errors.append("PROVEN API key security requires separated scopes")
        if facts.get("revocation_supported") is not True:
            errors.append("PROVEN API key security requires revocation")

    payment = controls.get("payment_lifecycle_guards") or {}
    if payment.get("state") == PROVEN:
        facts = payment.get("facts") or {}
        for key in (
            "authorization_required",
            "amount_match_enforced",
            "transition_order_enforced",
            "immutable_events",
        ):
            if facts.get(key) is not True:
                errors.append(f"PROVEN payment lifecycle requires {key}")

    parser = controls.get("parser_sandbox") or {}
    if parser.get("state") == NOT_APPLICABLE:
        facts = parser.get("facts") or {}
        if facts.get("production_parser_runtime_present") is not False:
            errors.append("NOT_APPLICABLE parser sandbox requires no production parser runtime")

    for name in EXTERNAL_CONTROLS:
        control = controls.get(name)
        if not isinstance(control, dict):
            errors.append(f"external control {name} missing")
            continue
        if control.get("state") != PENDING_EXTERNAL:
            errors.append(f"{name} must remain PENDING_EXTERNAL until independent evidence exists")

    claims = payload.get("claim_boundary") or []
    if not isinstance(claims, list) or not claims:
        errors.append("claim_boundary required")
    forbidden = ("SOC 2 certified", "ISO 27001 certified", "penetration tested", "fully compliant")
    joined = " ".join(str(x) for x in claims)
    if any(term.lower() in joined.lower() for term in forbidden):
        errors.append("claim boundary contains unsupported certification/security claim")

    return errors


def summarize_security_readiness(payload: dict) -> SecurityReadinessSummary:
    errors = validate_security_readiness(payload)
    if errors:
        raise ValueError("; ".join(errors))
    controls = payload["controls"]
    counts = {state: 0 for state in VALID_STATES}
    for control in controls.values():
        counts[control["state"]] += 1
    external = tuple(sorted(
        name for name in EXTERNAL_CONTROLS
        if controls[name]["state"] == PENDING_EXTERNAL
    ))
    return SecurityReadinessSummary(
        proven=counts[PROVEN],
        partial=counts[PARTIAL],
        pending_external=counts[PENDING_EXTERNAL],
        not_applicable=counts[NOT_APPLICABLE],
        external_required=external,
    )


def load_current(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parents[1]
    path = root / "freight" / "PHASE3_SECURITY_READINESS_2026-10-07.json"
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    payload = load_current()
    errors = validate_security_readiness(payload)
    if errors:
        print(json.dumps({"state": "INVALID", "errors": errors}, indent=2))
        raise SystemExit(1)
    summary = summarize_security_readiness(payload)
    print(json.dumps({
        "state": "INTERNAL_SECURITY_ENGINEERING_COMPLETE_EXTERNAL_ASSURANCE_PENDING",
        "proven": summary.proven,
        "partial": summary.partial,
        "pending_external": summary.pending_external,
        "not_applicable": summary.not_applicable,
        "external_required": list(summary.external_required),
    }, indent=2))
