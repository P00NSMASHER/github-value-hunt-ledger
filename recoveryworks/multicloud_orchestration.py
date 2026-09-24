"""Planning-only multi-cloud pilot orchestration.

This half-step validates separate AWS/Azure/GCP pilot jobs for one client while
preserving provider-level proof and state isolation. It does not execute the
jobs, combine ledgers, combine receipts, or aggregate financial totals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import canonical_hash
from recoveryworks.pilot_deployment import (
    PilotDeploymentPlan,
    build_pilot_deployment_plan,
)
from recoveryworks.private_io import atomic_private_write


@dataclass(frozen=True)
class MultiCloudProviderPlan:
    provider: str
    deployment_id: str
    deployment_plan_proof_hash: str
    bundle_path: str
    ledger_path: str
    receipt_registry_path: str
    report_path: str

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            **asdict(self),
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class MultiCloudOrchestrationPlan:
    orchestration_id: str
    client_id: str
    currency: str
    providers: tuple[str, ...]
    provider_plans: tuple[MultiCloudProviderPlan, ...]
    provider_isolation_required: bool = True
    shared_ledger_allowed: bool = False
    shared_receipt_registry_allowed: bool = False
    shared_financial_rollup_enabled: bool = False
    cross_provider_authority_reuse_allowed: bool = False
    execution_enabled: bool = False

    def __post_init__(self) -> None:
        if self.provider_isolation_required is not True:
            raise ValueError("multi-cloud planning requires provider isolation")
        for name in (
            "shared_ledger_allowed",
            "shared_receipt_registry_allowed",
            "shared_financial_rollup_enabled",
            "cross_provider_authority_reuse_allowed",
            "execution_enabled",
        ):
            if getattr(self, name):
                raise ValueError(f"{name} must remain false in orchestration 11a")
        expected = "multicloud-orchestration:" + canonical_hash(self._identity())
        if self.orchestration_id != expected:
            raise ValueError("orchestration_id does not bind the orchestration plan")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "client_id": self.client_id,
            "currency": self.currency,
            "providers": list(self.providers),
            "provider_plan_hashes": [
                plan.proof_hash for plan in self.provider_plans
            ],
            "provider_isolation_required": True,
            "shared_ledger_allowed": False,
            "shared_receipt_registry_allowed": False,
            "shared_financial_rollup_enabled": False,
            "cross_provider_authority_reuse_allowed": False,
            "execution_enabled": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "orchestration_id": self.orchestration_id,
            "provider_plans": [plan.as_dict() for plan in self.provider_plans],
            "proof_hash": self.proof_hash,
            "state": "DRY_RUN_PLANNED",
        }

    def to_markdown(self) -> str:
        lines = [
            "# Multi-Cloud Pilot Orchestration — Dry Run",
            "",
            f"Client: {self.client_id}",
            f"Currency: {self.currency}",
            f"Providers: {', '.join(provider.upper() for provider in self.providers)}",
            f"Plan proof: {self.proof_hash}",
            "",
            "## Isolation contract",
            "",
            "- Separate evidence bundle per provider",
            "- Separate RecoveryOS ledger per provider",
            "- Separate Cletrics receipt registry per provider",
            "- Separate assurance report per provider",
            "- Cross-provider authority reuse prohibited",
            "- Shared financial rollup disabled",
            "- Execution disabled",
            "",
            "## Provider jobs",
            "",
        ]
        for plan in self.provider_plans:
            lines.extend([
                f"### {plan.provider.upper()}",
                "",
                f"- Deployment id: {plan.deployment_id}",
                f"- Deployment proof: {plan.deployment_plan_proof_hash}",
                f"- Ledger: {plan.ledger_path}",
                f"- Receipt registry: {plan.receipt_registry_path}",
                f"- Report: {plan.report_path}",
                "",
            ])
        return "\n".join(lines)


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _provider_plan(plan: PilotDeploymentPlan) -> MultiCloudProviderPlan:
    return MultiCloudProviderPlan(
        provider=plan.provider,
        deployment_id=plan.deployment_id,
        deployment_plan_proof_hash=plan.proof_hash,
        bundle_path=plan.bundle_path,
        ledger_path=plan.ledger_path,
        receipt_registry_path=plan.receipt_registry_path,
        report_path=plan.report_path,
    )


def build_multicloud_orchestration_plan(
    spec: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
) -> MultiCloudOrchestrationPlan:
    if spec.get("schema") != 1:
        raise ValueError("unsupported multi-cloud orchestration schema")
    client_id = _text("client_id", spec.get("client_id"))
    currency = _text("currency", spec.get("currency", "USD")).upper()
    jobs = spec.get("jobs")
    if not isinstance(jobs, list) or not 2 <= len(jobs) <= 3:
        raise ValueError("multi-cloud orchestration requires 2 or 3 provider jobs")

    provider_plans: list[MultiCloudProviderPlan] = []
    seen_providers: set[str] = set()
    seen_deployments: set[str] = set()
    path_roles: dict[str, str] = {}

    for index, job in enumerate(jobs):
        if not isinstance(job, Mapping):
            raise ValueError(f"jobs[{index}] must be an object")
        if _text(f"jobs[{index}].client_id", job.get("client_id")) != client_id:
            raise ValueError("all multi-cloud jobs must use the same client_id")
        job_currency = _text(
            f"jobs[{index}].currency", job.get("currency", "USD")
        ).upper()
        if job_currency != currency:
            raise ValueError("all multi-cloud jobs must use the same currency")
        deployment = build_pilot_deployment_plan(job, base_dir=base_dir)
        if deployment.provider in seen_providers:
            raise ValueError(
                f"duplicate provider job: {deployment.provider}"
            )
        if deployment.deployment_id in seen_deployments:
            raise ValueError(
                f"duplicate deployment_id: {deployment.deployment_id}"
            )
        seen_providers.add(deployment.provider)
        seen_deployments.add(deployment.deployment_id)

        for role, value in (
            ("bundle", deployment.bundle_path),
            ("ledger", deployment.ledger_path),
            ("receipt_registry", deployment.receipt_registry_path),
            ("report", deployment.report_path),
        ):
            path = str(Path(value).resolve())
            previous = path_roles.get(path)
            if previous is not None:
                raise ValueError(
                    "multi-cloud jobs cannot share state/output paths: "
                    f"{path} used by {previous} and "
                    f"{deployment.provider}.{role}"
                )
            path_roles[path] = f"{deployment.provider}.{role}"
        provider_plans.append(_provider_plan(deployment))

    provider_plans.sort(key=lambda item: item.provider)
    providers = tuple(item.provider for item in provider_plans)
    identity = {
        "schema": 1,
        "client_id": client_id,
        "currency": currency,
        "providers": list(providers),
        "provider_plan_hashes": [
            plan.proof_hash for plan in provider_plans
        ],
        "provider_isolation_required": True,
        "shared_ledger_allowed": False,
        "shared_receipt_registry_allowed": False,
        "shared_financial_rollup_enabled": False,
        "cross_provider_authority_reuse_allowed": False,
        "execution_enabled": False,
    }
    return MultiCloudOrchestrationPlan(
        orchestration_id="multicloud-orchestration:" + canonical_hash(identity),
        client_id=client_id,
        currency=currency,
        providers=providers,
        provider_plans=tuple(provider_plans),
    )


def write_multicloud_orchestration_plan(
    plan: MultiCloudOrchestrationPlan,
    *,
    json_path: str | Path,
    markdown_path: str | Path,
) -> None:
    atomic_private_write(
        Path(json_path),
        (
            json.dumps(
                plan.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(markdown_path),
        (plan.to_markdown() + "\n").encode("utf-8"),
    )
