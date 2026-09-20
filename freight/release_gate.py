"""Release/rights gate for Freight Recovery.

The gate intentionally distinguishes a controlled read-only pilot from a hosted
annual SaaS deployment. It does not interpret contract text; it records missing
operability evidence as blockers/review items.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0-1.0"}
UNKNOWN = {"UNKNOWN", "UNKNOWN_REVIEW", "REVIEW", ""}


def load_registry(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def validate_registry(registry: dict, stage: str = "pilot") -> tuple[list[str], list[str]]:
    if stage not in {"pilot", "annual"}:
        raise ValueError("stage must be pilot or annual")

    errors: list[str] = []
    warnings: list[str] = []
    components = registry.get("components")
    if not isinstance(components, list) or not components:
        return ["registry.components must be a non-empty list"], warnings

    seen: set[tuple[str, str]] = set()
    for index, component in enumerate(components):
        prefix = f"components[{index}]"
        for field in ("repository", "revision", "role", "public_license", "commercial_use_basis"):
            value = component.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} is required")

        repository = component.get("repository", "")
        revision = component.get("revision", "")
        if revision and not SHA40.fullmatch(revision):
            errors.append(f"{repository or prefix}: revision must be full 40-char SHA")

        key = (repository, revision)
        if key in seen:
            errors.append(f"duplicate component revision: {repository}@{revision}")
        seen.add(key)

        basis = component.get("commercial_use_basis", "")
        if not basis or basis in UNKNOWN:
            errors.append(f"{repository}: commercial-use basis unresolved")

        public_license = component.get("public_license", "")
        runtime_status = component.get("runtime_status", "")
        is_independent = runtime_status in {"KEEP_INDEPENDENT", "COMPARATOR_NOT_PRIMARY_RUNTIME"}

        if stage == "pilot":
            if "USER_ASSERTED" in basis and public_license not in PERMISSIVE:
                warnings.append(
                    f"{repository}: controlled pilot depends on separately documented permission"
                )
        else:
            if is_independent:
                continue
            if "USER_ASSERTED" in basis and public_license not in PERMISSIVE:
                hosted = component.get("hosted_saas_status", "UNKNOWN_REVIEW")
                change = component.get("change_of_control_status", "UNKNOWN_REVIEW")
                if hosted in UNKNOWN:
                    errors.append(f"{repository}: hosted/SaaS rights unresolved for annual deployment")
                if change in UNKNOWN:
                    warnings.append(f"{repository}: change-of-control rights unresolved")

    return errors, warnings


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        default="freight/COMPONENT_RIGHTS_REGISTRY.json",
    )
    parser.add_argument("--stage", choices=("pilot", "annual"), default="pilot")
    args = parser.parse_args()

    errors, warnings = validate_registry(load_registry(args.registry), args.stage)
    print(json.dumps({"stage": args.stage, "errors": errors, "warnings": warnings}, indent=2))
    raise SystemExit(1 if errors else 0)
