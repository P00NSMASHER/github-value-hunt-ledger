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
from recoveryworks.pilot_runner import PilotRunResult, run_local_pilot
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
    source_input_roles: dict[str, str] = {}

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

        cletrics = job.get("cletrics")
        recoveryos = job.get("recoveryos")
        if not isinstance(cletrics, Mapping) or not isinstance(recoveryos, Mapping):
            raise ValueError("each provider job requires cletrics and recoveryos objects")
        for role, value in (
            ("focus_csv", cletrics.get("focus_csv")),
            ("meter_csv", cletrics.get("meter_csv")),
            ("anomaly_csv", cletrics.get("anomaly_csv")),
            ("reconciliation_csv", cletrics.get("reconciliation_csv")),
            ("savings_csv", cletrics.get("savings_csv")),
            ("rates_csv", recoveryos.get("rates_csv")),
            ("discounts_csv", recoveryos.get("discounts_csv")),
            ("commitments_csv", recoveryos.get("commitments_csv")),
            ("allocations_csv", recoveryos.get("allocations_csv")),
        ):
            if not value:
                continue
            source_path = Path(str(value))
            if not source_path.is_absolute():
                source_path = Path(base_dir) / source_path
            source_key = str(source_path.resolve())
            previous = source_input_roles.get(source_key)
            if previous is not None:
                raise ValueError(
                    "multi-cloud jobs cannot reuse provider evidence/authority inputs: "
                    f"{source_key} used by {previous} and "
                    f"{deployment.provider}.{role}"
                )
            source_input_roles[source_key] = f"{deployment.provider}.{role}"

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


@dataclass(frozen=True)
class MultiCloudProviderRun:
    provider: str
    deployment_id: str
    deployment_plan_proof_hash: str
    state_head_hash: str | None
    assurance_report_path: str
    assurance_report_proof_hash: str
    pilot: PilotRunResult

    def __post_init__(self) -> None:
        if self.provider != self.pilot.export_receipt.provider:
            raise ValueError("provider run does not match exported provider scope")
        if self.deployment_plan_proof_hash != self.pilot.deployment_plan_hash:
            raise ValueError("provider run deployment proof mismatch")
        if self.assurance_report_path != self.pilot.report_path:
            raise ValueError("provider run report path mismatch")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "provider": self.provider,
            "deployment_id": self.deployment_id,
            "deployment_plan_proof_hash": self.deployment_plan_proof_hash,
            "state_head_hash": self.state_head_hash,
            "assurance_report_path": self.assurance_report_path,
            "assurance_report_proof_hash": self.assurance_report_proof_hash,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "deployment_id": self.deployment_id,
            "deployment_plan_proof_hash": self.deployment_plan_proof_hash,
            "state_head_hash": self.state_head_hash,
            "assurance_report_path": self.assurance_report_path,
            "assurance_report_proof_hash": self.assurance_report_proof_hash,
            "proof_hash": self.proof_hash,
        }


@dataclass(frozen=True)
class MultiCloudExecutionResult:
    orchestration_plan_id: str
    orchestration_plan_proof_hash: str
    client_id: str
    currency: str
    provider_runs: tuple[MultiCloudProviderRun, ...]
    provider_isolation_preserved: bool = True
    combined_financial_rollup_enabled: bool = False
    cross_provider_authority_reuse_allowed: bool = False
    cloud_mutation_performed: bool = False
    external_actions_performed: bool = False

    def __post_init__(self) -> None:
        if self.provider_isolation_preserved is not True:
            raise ValueError("multi-cloud execution must preserve provider isolation")
        for name in (
            "combined_financial_rollup_enabled",
            "cross_provider_authority_reuse_allowed",
            "cloud_mutation_performed",
            "external_actions_performed",
        ):
            if getattr(self, name):
                raise ValueError(f"{name} must remain false in orchestration 11b")
        providers = tuple(run.provider for run in self.provider_runs)
        if len(providers) < 2 or len(set(providers)) != len(providers):
            raise ValueError("multi-cloud execution requires unique provider runs")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "orchestration_plan_id": self.orchestration_plan_id,
            "orchestration_plan_proof_hash": self.orchestration_plan_proof_hash,
            "client_id": self.client_id,
            "currency": self.currency,
            "provider_run_hashes": [run.proof_hash for run in self.provider_runs],
            "provider_isolation_preserved": True,
            "combined_financial_rollup_enabled": False,
            "cross_provider_authority_reuse_allowed": False,
            "cloud_mutation_performed": False,
            "external_actions_performed": False,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            "orchestration_plan_id": self.orchestration_plan_id,
            "orchestration_plan_proof_hash": self.orchestration_plan_proof_hash,
            "client_id": self.client_id,
            "currency": self.currency,
            "provider_runs": [run.as_dict() for run in self.provider_runs],
            "provider_isolation_preserved": True,
            "combined_financial_rollup_enabled": False,
            "cross_provider_authority_reuse_allowed": False,
            "cloud_mutation_performed": False,
            "external_actions_performed": False,
            "proof_hash": self.proof_hash,
            "state": "PROVIDER_JOBS_COMPLETED_SEPARATELY",
        }


def _load_assurance_report(path: str | Path) -> Mapping[str, Any]:
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("provider assurance report is not readable JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("provider assurance report must be a JSON object")
    proof_hash = payload.get("proof_hash")
    if not isinstance(proof_hash, str) or len(proof_hash) != 64:
        raise ValueError("provider assurance report proof hash missing")
    identity = {key: value for key, value in payload.items() if key != "proof_hash"}
    if canonical_hash(identity) != proof_hash:
        raise ValueError("provider assurance report proof hash mismatch")
    return payload


def run_multicloud_orchestration(
    spec: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
) -> MultiCloudExecutionResult:
    """Execute local read-only provider pilots without creating a combined ledger."""
    plan = build_multicloud_orchestration_plan(spec, base_dir=base_dir)
    jobs = spec.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")
    jobs_by_provider: dict[str, Mapping[str, Any]] = {}
    for job in jobs:
        if not isinstance(job, Mapping):
            raise ValueError("provider job must be an object")
        deployment = build_pilot_deployment_plan(job, base_dir=base_dir)
        jobs_by_provider[deployment.provider] = job

    runs: list[MultiCloudProviderRun] = []
    for provider_plan in plan.provider_plans:
        job = jobs_by_provider[provider_plan.provider]
        pilot = run_local_pilot(job, base_dir=base_dir)
        if pilot.deployment_plan_hash != provider_plan.deployment_plan_proof_hash:
            raise ValueError(
                f"{provider_plan.provider} deployment changed after orchestration planning"
            )
        report = _load_assurance_report(pilot.report_path)
        if report.get("client_id") != plan.client_id:
            raise ValueError("provider assurance report client mismatch")
        if report.get("currency") != plan.currency:
            raise ValueError("provider assurance report currency mismatch")
        runs.append(MultiCloudProviderRun(
            provider=provider_plan.provider,
            deployment_id=provider_plan.deployment_id,
            deployment_plan_proof_hash=provider_plan.deployment_plan_proof_hash,
            state_head_hash=pilot.continuous_result.scan.state_head_hash,
            assurance_report_path=pilot.report_path,
            assurance_report_proof_hash=str(report["proof_hash"]),
            pilot=pilot,
        ))

    runs.sort(key=lambda item: item.provider)
    return MultiCloudExecutionResult(
        orchestration_plan_id=plan.orchestration_id,
        orchestration_plan_proof_hash=plan.proof_hash,
        client_id=plan.client_id,
        currency=plan.currency,
        provider_runs=tuple(runs),
    )
