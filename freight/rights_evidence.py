"""Evidence-backed rights diligence for Freight Recovery.

This module does not interpret contracts. It enforces a narrower invariant:
registry rights may not be represented as resolved unless a separately stored
executed evidence object is referenced by location and SHA-256.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_STATUSES = {"NOT_ATTACHED", "ATTACHED_UNVERIFIED", "ATTACHED_VERIFIED"}
SCOPE_STATES = {
    "UNKNOWN_REVIEW",
    "USER_ASSERTED_NOT_ATTACHED",
    "CONFIRMED_ALLOWED",
    "CONFIRMED_DENIED",
    "NOT_APPLICABLE",
}
REGISTRY_FIELDS = {
    "hosted_saas": "hosted_saas_status",
    "assignment": "assignment_status",
    "sublicensing": "sublicense_status",
    "change_of_control": "change_of_control_status",
}
UNKNOWN_REGISTRY = {"UNKNOWN", "UNKNOWN_REVIEW", None, ""}
PERMISSIVE_PUBLIC_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "CC0-1.0",
}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _entry_key(entry: dict) -> tuple[str, str]:
    return entry.get("repository"), entry.get("revision")


def validate_rights_evidence(
    registry: dict,
    manifest: dict,
    *,
    stage: str = "pilot",
) -> tuple[list[str], list[str]]:
    if stage not in {"pilot", "annual"}:
        raise ValueError("stage must be pilot or annual")

    errors: list[str] = []
    warnings: list[str] = []

    components = registry.get("components") or []
    entries = manifest.get("entries") or []
    if manifest.get("schema_version") != 1:
        errors.append("rights evidence manifest schema_version must be 1")

    by_key: dict[tuple[str, str], dict] = {}
    for index, entry in enumerate(entries):
        key = _entry_key(entry)
        if not all(isinstance(x, str) and x for x in key):
            errors.append(f"entries[{index}]: repository and revision are required")
            continue
        if key in by_key:
            errors.append(f"duplicate rights evidence entry: {key[0]}@{key[1]}")
            continue
        by_key[key] = entry

        status = entry.get("evidence_status")
        if status not in EVIDENCE_STATUSES:
            errors.append(f"{key[0]}: invalid evidence_status")

        location = entry.get("evidence_location")
        sha = entry.get("evidence_sha256")
        if status == "ATTACHED_VERIFIED":
            if not isinstance(location, str) or not location.strip():
                errors.append(f"{key[0]}: verified evidence requires evidence_location")
            if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
                errors.append(f"{key[0]}: verified evidence requires lowercase SHA-256")
        elif sha not in {None, ""}:
            errors.append(f"{key[0]}: evidence_sha256 requires ATTACHED_VERIFIED status")

        scopes = entry.get("scopes") or {}
        for scope in ("commercial_use", *REGISTRY_FIELDS):
            state = scopes.get(scope)
            if state not in SCOPE_STATES:
                errors.append(f"{key[0]}: invalid scope state for {scope}")
                continue
            if state in {"CONFIRMED_ALLOWED", "CONFIRMED_DENIED", "NOT_APPLICABLE"}:
                if status != "ATTACHED_VERIFIED":
                    errors.append(
                        f"{key[0]}: resolved scope {scope} requires ATTACHED_VERIFIED evidence"
                    )

    separate_permission_components = []
    for component in components:
        basis = component.get("commercial_use_basis") or ""
        public_license = component.get("public_license") or ""
        relies_on_separate_permission = (
            ("USER_ASSERTED" in basis or "SEPARATE_" in basis)
            and public_license not in PERMISSIVE_PUBLIC_LICENSES
        )
        if relies_on_separate_permission:
            separate_permission_components.append(component)

    for component in separate_permission_components:
        key = (component.get("repository"), component.get("revision"))
        entry = by_key.get(key)
        repo = component.get("repository") or "unknown"
        if entry is None:
            errors.append(f"{repo}: separate permission component missing rights evidence entry")
            continue

        scopes = entry.get("scopes") or {}
        if entry.get("evidence_status") != "ATTACHED_VERIFIED":
            errors.append(
                f"{repo}: controlled pilot requires attached and verified "
                "executed permission evidence"
            )

        if scopes.get("commercial_use") != "CONFIRMED_ALLOWED":
            errors.append(
                f"{repo}: commercial_use must be CONFIRMED_ALLOWED for runtime use"
            )

        for scope, registry_field in REGISTRY_FIELDS.items():
            registry_value = component.get(registry_field)
            evidence_value = scopes.get(scope)
            registry_resolved = registry_value not in UNKNOWN_REGISTRY
            evidence_resolved = evidence_value in {
                "CONFIRMED_ALLOWED",
                "CONFIRMED_DENIED",
                "NOT_APPLICABLE",
            }
            if registry_resolved and not evidence_resolved:
                errors.append(
                    f"{repo}: registry resolves {registry_field} without resolved evidence scope"
                )

        if stage == "annual":
            required = ("hosted_saas", "change_of_control")
            for scope in required:
                state = scopes.get(scope)
                if state not in {
                    "CONFIRMED_ALLOWED",
                    "CONFIRMED_DENIED",
                    "NOT_APPLICABLE",
                }:
                    errors.append(f"{repo}: annual diligence leaves {scope} unresolved")
                elif state == "CONFIRMED_DENIED":
                    errors.append(f"{repo}: annual diligence denies required {scope} rights")

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="freight/COMPONENT_RIGHTS_REGISTRY.json",
    )
    parser.add_argument(
        "--manifest",
        default="freight/RIGHTS_EVIDENCE_MANIFEST.json",
    )
    parser.add_argument("--stage", choices=("pilot", "annual"), default="pilot")
    parser.add_argument("--expect", choices=("CLEAR", "BLOCKED"))
    args = parser.parse_args()

    errors, warnings = validate_rights_evidence(
        load_json(args.registry),
        load_json(args.manifest),
        stage=args.stage,
    )
    state = "BLOCKED" if errors else "CLEAR"
    print(json.dumps({
        "stage": args.stage,
        "state": state,
        "errors": errors,
        "warnings": warnings,
    }, indent=2))
    if args.expect is not None:
        raise SystemExit(0 if state == args.expect else 1)
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
