"""Dry-run deployment contract for the Cletrics + RecoveryOS pilot.

This is intentionally the first half of deployment work. It validates an
supported-provider read-only pilot layout and emits the deterministic local commands/paths
that a later launcher will execute. It performs no provisioning, network
access, container startup, cloud mutation, or external action.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import canonical_hash, normalize_git_commit_sha


_SUPPORTED_PROVIDERS = {"aws", "azure", "gcp"}


@dataclass(frozen=True)
class PilotCommand:
    purpose: str
    argv: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise ValueError("command purpose is required")
        if not self.argv or any(not isinstance(item, str) or not item for item in self.argv):
            raise ValueError("command argv must contain non-empty strings")

    def as_dict(self) -> dict[str, Any]:
        return {"purpose": self.purpose, "argv": list(self.argv)}


@dataclass(frozen=True)
class PilotDeploymentPlan:
    deployment_id: str
    client_id: str
    provider: str
    base_dir: str
    bundle_path: str
    ledger_path: str
    receipt_registry_path: str
    report_path: str
    commands: tuple[PilotCommand, ...]
    security_assertions: tuple[str, ...]
    provisioning_allowed: bool = False

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "deployment_id": self.deployment_id,
            "client_id": self.client_id,
            "provider": self.provider,
            "base_dir": self.base_dir,
            "bundle_path": self.bundle_path,
            "ledger_path": self.ledger_path,
            "receipt_registry_path": self.receipt_registry_path,
            "report_path": self.report_path,
            "commands": [command.as_dict() for command in self.commands],
            "security_assertions": list(self.security_assertions),
            "provisioning_allowed": self.provisioning_allowed,
        })

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "commands": [command.as_dict() for command in self.commands],
            "proof_hash": self.proof_hash,
            "dry_run": True,
        }


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


def _mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be boolean")
    return value


def _input_file(base: Path, value: Any, *, name: str) -> Path:
    raw = Path(_text(name, value))
    path = raw if raw.is_absolute() else base / raw
    if not path.is_file():
        raise ValueError(f"{name} does not exist as a file: {path}")
    return path


def _output_path(base: Path, value: Any, *, name: str) -> Path:
    raw = Path(_text(name, value))
    path = raw if raw.is_absolute() else base / raw
    if path.exists() and path.is_dir():
        raise ValueError(f"{name} must be a file path")
    return path


def build_pilot_deployment_plan(
    spec: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
) -> PilotDeploymentPlan:
    if spec.get("schema") != 1:
        raise ValueError("unsupported pilot deployment schema")
    base = Path(base_dir).resolve()
    deployment_id = _text("deployment_id", spec.get("deployment_id"))
    client_id = _text("client_id", spec.get("client_id"))
    provider = _text("provider", spec.get("provider")).lower()
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            "pilot deployment provider must be one of: "
            + ", ".join(sorted(_SUPPORTED_PROVIDERS))
        )

    security = _mapping("security", spec.get("security"))
    access_mode = _text("security.cloud_access_mode", security.get("cloud_access_mode"))
    if access_mode != "READ_ONLY":
        raise ValueError("pilot cloud access must be READ_ONLY")
    if _bool(
        "security.recoveryos_provider_write_credentials",
        security.get("recoveryos_provider_write_credentials"),
    ):
        raise ValueError("RecoveryOS must not receive provider write credentials")
    if _bool(
        "security.remediation_execution_enabled",
        security.get("remediation_execution_enabled"),
    ):
        raise ValueError("pilot remediation execution must remain disabled")
    if _bool(
        "security.external_actions_enabled",
        security.get("external_actions_enabled"),
    ):
        raise ValueError("pilot external actions must remain disabled")
    if not _bool(
        "security.private_state_required",
        security.get("private_state_required"),
    ):
        raise ValueError("pilot private-state requirement must be enabled")

    cletrics = _mapping("cletrics", spec.get("cletrics"))
    focus = _input_file(base, cletrics.get("focus_csv"), name="cletrics.focus_csv")
    meter = _input_file(base, cletrics.get("meter_csv"), name="cletrics.meter_csv")
    rates = _input_file(
        base,
        _mapping("recoveryos", spec.get("recoveryos")).get("rates_csv"),
        name="recoveryos.rates_csv",
    )
    release = _text("cletrics.release", cletrics.get("release"))
    commit = cletrics.get("commit")
    image_digest = cletrics.get("image_digest")
    if commit:
        commit = normalize_git_commit_sha("cletrics.commit", commit)
    elif not image_digest:
        raise ValueError("cletrics.commit or cletrics.image_digest is required")

    period = _mapping("period", spec.get("period"))
    period_start = _text("period.start", period.get("start"))
    period_end = _text("period.end", period.get("end"))
    exported_at = _text("period.exported_at", period.get("exported_at"))

    optional_cli: list[str] = []
    for key, flag in (
        ("anomaly_csv", "--anomaly"),
        ("reconciliation_csv", "--reconciliation"),
        ("savings_csv", "--savings"),
    ):
        value = cletrics.get(key)
        if value:
            path = _input_file(base, value, name=f"cletrics.{key}")
            optional_cli.extend((flag, str(path)))

    recoveryos = _mapping("recoveryos", spec.get("recoveryos"))
    bundle = _output_path(base, recoveryos.get("bundle_path"), name="recoveryos.bundle_path")
    ledger = _output_path(base, recoveryos.get("ledger_path"), name="recoveryos.ledger_path")
    registry = _output_path(
        base,
        recoveryos.get("receipt_registry_path"),
        name="recoveryos.receipt_registry_path",
    )
    report = _output_path(base, recoveryos.get("report_path"), name="recoveryos.report_path")

    export_argv = [
        "python",
        "-m",
        "recoveryworks.integrations.cletrics_exporter",
        "--focus",
        str(focus),
        "--meter",
        str(meter),
        "--output",
        str(bundle),
        "--client-id",
        client_id,
        "--cletrics-release",
        release,
        "--exported-at",
        exported_at,
        "--period-start",
        period_start,
        "--period-end",
        period_end,
    ]
    if commit:
        export_argv.extend(("--cletrics-commit", commit))
    else:
        export_argv.extend(("--cletrics-image-digest", _text("cletrics.image_digest", image_digest)))
    export_argv.extend(optional_cli)

    commands = (
        PilotCommand(
            purpose="export-cletrics-recoveryos-bundle",
            argv=tuple(export_argv),
        ),
        PilotCommand(
            purpose="continuous-recovery-scan-api",
            argv=(
                "python",
                "-m",
                "recoveryworks.pilot_runner",
                "--bundle",
                str(bundle),
                "--rates",
                str(rates),
                "--ledger",
                str(ledger),
                "--registry",
                str(registry),
                "--report",
                str(report),
                "--client-id",
                client_id,
                "--dry-run-contract-only",
            ),
        ),
    )
    assertions = (
        f"{provider.upper()} access declared READ_ONLY",
        "RecoveryOS provider write credentials disabled",
        "remediation execution disabled",
        "external recovery actions disabled",
        "ledger and receipt registry designated private state",
    )
    identity = {
        "schema": 1,
        "deployment_id": deployment_id,
        "client_id": client_id,
        "provider": provider,
        "base_dir": str(base),
        "bundle_path": str(bundle),
        "ledger_path": str(ledger),
        "receipt_registry_path": str(registry),
        "report_path": str(report),
        "commands": [command.as_dict() for command in commands],
        "security_assertions": list(assertions),
        "provisioning_allowed": False,
    }
    return PilotDeploymentPlan(
        deployment_id=deployment_id,
        client_id=client_id,
        provider=provider,
        base_dir=str(base),
        bundle_path=str(bundle),
        ledger_path=str(ledger),
        receipt_registry_path=str(registry),
        report_path=str(report),
        commands=commands,
        security_assertions=assertions,
        provisioning_allowed=False,
    )


def load_pilot_spec(path: str | Path) -> Mapping[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("pilot deployment spec must be readable JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError("pilot deployment spec must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Cletrics + RecoveryOS pilot deployment contract."
    )
    parser.add_argument("--spec", required=True)
    parser.add_argument("--base-dir", default=".")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="required in this implementation; provisioning is not implemented",
    )
    args = parser.parse_args(argv)
    if not args.dry_run:
        parser.error(
            "only --dry-run is supported; provisioning/startup is intentionally not implemented yet"
        )
    plan = build_pilot_deployment_plan(
        load_pilot_spec(args.spec),
        base_dir=args.base_dir,
    )
    print(json.dumps(plan.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
