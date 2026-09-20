"""Final launch gate for Freight Recovery paid pilot execution.

Buyer/data readiness, legal operability, and environment security are separate
claims. The chosen data path must pass its own evidence gate before
confidential customer data is accepted.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from freight.deployment_security_evidence import (
    evidence_conditions,
    validate_evidence,
)
from freight.readiness import (
    ReadinessAssessment,
    ReadinessStatus,
    assess_readiness,
    from_dict,
)
from freight.release_gate import validate_registry
from freight.rights_evidence import validate_rights_evidence
from freight.separate_environment_evidence import validate_environment_evidence


class DataPath(str, Enum):
    CURRENT_DEPLOYMENT = "CURRENT_DEPLOYMENT"
    SEPARATE_CONTROLLED_ENVIRONMENT = "SEPARATE_CONTROLLED_ENVIRONMENT"


class LaunchStatus(str, Enum):
    BLOCKED = "BLOCKED"
    CONDITIONAL = "CONDITIONAL"
    READY = "READY"


class LaunchRoute(str, Enum):
    DATA_READINESS_DIAGNOSTIC = "DATA_READINESS_DIAGNOSTIC"
    DEPLOYED_PILOT_BLOCKED = "DEPLOYED_PILOT_BLOCKED"
    DEPLOYED_BLIND_PILOT = "DEPLOYED_BLIND_PILOT"
    SEPARATE_ENVIRONMENT_PENDING = "SEPARATE_ENVIRONMENT_PENDING"
    CONTROLLED_MANUAL_BLIND_PILOT = "CONTROLLED_MANUAL_BLIND_PILOT"


@dataclass(frozen=True)
class LaunchRequest:
    data_path: DataPath
    requires_multi_tenant_data_plane: bool = False
    requires_parser_runtime: bool = False


@dataclass(frozen=True)
class LaunchDecision:
    status: LaunchStatus
    route: LaunchRoute
    blockers: tuple[str, ...]
    conditions: tuple[str, ...]
    warnings: tuple[str, ...]


def _blocked_route(request: LaunchRequest) -> LaunchRoute:
    return (
        LaunchRoute.DEPLOYED_PILOT_BLOCKED
        if request.data_path is DataPath.CURRENT_DEPLOYMENT
        else LaunchRoute.SEPARATE_ENVIRONMENT_PENDING
    )


def evaluate_launch(
    *,
    readiness: ReadinessAssessment,
    component_registry: dict,
    rights_manifest: dict,
    deployment_evidence: dict | None,
    request: LaunchRequest,
    separate_environment_evidence: dict | None = None,
    as_of_date: str | None = None,
) -> LaunchDecision:
    blockers: list[str] = []
    conditions: list[str] = []
    warnings: list[str] = []

    if readiness.status is not ReadinessStatus.READY:
        blockers.extend(readiness.blockers)
        conditions.extend(readiness.conditions)
        return LaunchDecision(
            LaunchStatus.BLOCKED,
            LaunchRoute.DATA_READINESS_DIAGNOSTIC,
            tuple(blockers),
            tuple(conditions),
            tuple(warnings),
        )

    registry_errors, registry_warnings = validate_registry(
        component_registry,
        stage="pilot",
    )
    rights_errors, rights_warnings = validate_rights_evidence(
        component_registry,
        rights_manifest,
        stage="pilot",
    )
    blockers.extend(registry_errors)
    blockers.extend(rights_errors)
    warnings.extend(registry_warnings)
    warnings.extend(rights_warnings)

    if blockers:
        return LaunchDecision(
            LaunchStatus.BLOCKED,
            _blocked_route(request),
            tuple(blockers),
            tuple(conditions),
            tuple(warnings),
        )

    if request.data_path is DataPath.CURRENT_DEPLOYMENT:
        if deployment_evidence is None:
            blockers.append("deployment_evidence_missing")
        else:
            blockers.extend(
                "deployment_evidence_invalid:" + x
                for x in validate_evidence(deployment_evidence)
            )
            blockers.extend(
                evidence_conditions(
                    deployment_evidence,
                    as_of_date=as_of_date,
                )
            )

        if blockers:
            return LaunchDecision(
                LaunchStatus.BLOCKED,
                LaunchRoute.DEPLOYED_PILOT_BLOCKED,
                tuple(blockers),
                tuple(conditions),
                tuple(warnings),
            )

        access = deployment_evidence.get("access_control") or {}
        inventory = deployment_evidence.get("deployment_inventory") or {}
        tenant = deployment_evidence.get("cross_tenant_isolation") or {}
        parser = deployment_evidence.get("parser_sandbox") or {}

        if access.get("status") != "CONFIG_PROVEN":
            blockers.append("deployment_access_control_not_proven")
        if access.get("sso_team_login_required") is not True:
            blockers.append("deployment_sso_not_required")
        if access.get("team_mfa_enforced") is not True:
            blockers.append("deployment_team_mfa_not_enforced")

        if inventory.get("status") == "NO_DISCOVERED_FREIGHT_BACKEND_OR_DATA_PLANE":
            blockers.append("customer_data_plane_not_discovered")

        if request.requires_multi_tenant_data_plane:
            if tenant.get("status") != "PROVEN":
                blockers.append("cross_tenant_isolation_not_proven")

        if request.requires_parser_runtime:
            if parser.get("status") != "PROVEN":
                blockers.append("parser_sandbox_not_proven")

        if blockers:
            return LaunchDecision(
                LaunchStatus.BLOCKED,
                LaunchRoute.DEPLOYED_PILOT_BLOCKED,
                tuple(blockers),
                tuple(conditions),
                tuple(warnings),
            )

        return LaunchDecision(
            LaunchStatus.READY,
            LaunchRoute.DEPLOYED_BLIND_PILOT,
            (),
            (),
            tuple(warnings),
        )

    if request.data_path is DataPath.SEPARATE_CONTROLLED_ENVIRONMENT:
        if separate_environment_evidence is None:
            conditions.append("separate_environment_evidence_manifest_missing")
            return LaunchDecision(
                LaunchStatus.CONDITIONAL,
                LaunchRoute.SEPARATE_ENVIRONMENT_PENDING,
                (),
                tuple(conditions),
                tuple(warnings),
            )

        environment_errors, environment_conditions = validate_environment_evidence(
            separate_environment_evidence,
            as_of_date=as_of_date,
        )
        if environment_errors:
            blockers.extend(
                "separate_environment_evidence_invalid:" + x
                for x in environment_errors
            )
            return LaunchDecision(
                LaunchStatus.BLOCKED,
                LaunchRoute.SEPARATE_ENVIRONMENT_PENDING,
                tuple(blockers),
                tuple(environment_conditions),
                tuple(warnings),
            )

        if environment_conditions:
            return LaunchDecision(
                LaunchStatus.CONDITIONAL,
                LaunchRoute.SEPARATE_ENVIRONMENT_PENDING,
                (),
                tuple(environment_conditions),
                tuple(warnings),
            )

        return LaunchDecision(
            LaunchStatus.READY,
            LaunchRoute.CONTROLLED_MANUAL_BLIND_PILOT,
            (),
            (),
            tuple(warnings),
        )

    raise ValueError("unsupported data path")


def _load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("readiness_json")
    parser.add_argument(
        "--data-path",
        choices=("current", "separate"),
        default="current",
    )
    parser.add_argument("--requires-multi-tenant", action="store_true")
    parser.add_argument("--requires-parser", action="store_true")
    parser.add_argument("--separate-evidence-json")
    parser.add_argument("--as-of-date")
    parser.add_argument("--expect", choices=("BLOCKED", "CONDITIONAL", "READY"))
    args = parser.parse_args()

    readiness_input = from_dict(_load(args.readiness_json))
    readiness = assess_readiness(readiness_input)
    root = Path(__file__).resolve().parents[1]

    request = LaunchRequest(
        data_path=(
            DataPath.CURRENT_DEPLOYMENT
            if args.data_path == "current"
            else DataPath.SEPARATE_CONTROLLED_ENVIRONMENT
        ),
        requires_multi_tenant_data_plane=args.requires_multi_tenant,
        requires_parser_runtime=args.requires_parser,
    )

    separate_environment_evidence = (
        _load(args.separate_evidence_json)
        if args.separate_evidence_json
        else None
    )

    decision = evaluate_launch(
        readiness=readiness,
        component_registry=_load(root / "freight/COMPONENT_RIGHTS_REGISTRY.json"),
        rights_manifest=_load(root / "freight/RIGHTS_EVIDENCE_MANIFEST.json"),
        deployment_evidence=_load(
            root / "freight/DEPLOYMENT_SECURITY_EVIDENCE_2026-09-20.json"
        ),
        request=request,
        separate_environment_evidence=separate_environment_evidence,
        as_of_date=args.as_of_date,
    )
    payload = asdict(decision)
    payload["status"] = decision.status.value
    payload["route"] = decision.route.value
    print(json.dumps(payload, indent=2))

    if args.expect and decision.status.value != args.expect:
        raise SystemExit(
            f"expected launch status {args.expect}, got {decision.status.value}"
        )


if __name__ == "__main__":
    main()
