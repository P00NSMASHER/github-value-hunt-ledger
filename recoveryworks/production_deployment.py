"""Production deployment packaging and local preflight for RecoveryOS pilots.

This module creates/validates container and volume contracts and renders a
networkless Docker Compose batch deployment. It does not build images, start
containers, provision infrastructure, or contact any external provider.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import importlib.util
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from recoveryworks.models import canonical_hash
from recoveryworks.pilot_deployment import (
    PilotDeploymentPlan,
    build_pilot_deployment_plan,
    load_pilot_spec,
)
from recoveryworks.private_io import (
    atomic_private_write,
    private_permissions_verified,
)


_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")
_USER_RE = re.compile(r"^([1-9]\d*):([1-9]\d*)$")
_REQUIRED_VOLUME_ROLES = ("config", "inputs", "state", "reports")


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


@dataclass(frozen=True)
class ProductionVolumeContract:
    role: str
    host_path: str
    container_path: str
    read_only: bool
    private_required: bool

    def __post_init__(self) -> None:
        role = _text("role", self.role)
        if role not in _REQUIRED_VOLUME_ROLES:
            raise ValueError(f"unsupported production volume role: {role}")
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "host_path", _text("host_path", self.host_path))
        container = _text("container_path", self.container_path)
        if not container.startswith("/"):
            raise ValueError("container_path must be absolute")
        object.__setattr__(self, "container_path", container)
        if type(self.read_only) is not bool or type(self.private_required) is not bool:
            raise ValueError("volume flags must be boolean")
        if role in {"config", "inputs"} and not self.read_only:
            raise ValueError(f"{role} volume must be read-only")
        if role in {"state", "reports"}:
            if self.read_only:
                raise ValueError(f"{role} volume must be writable")
            if not self.private_required:
                raise ValueError(f"{role} volume must require private storage")


@dataclass(frozen=True)
class ProductionServiceContract:
    image_ref: str
    user: str
    command: tuple[str, ...]
    read_only_root_filesystem: bool
    privileged: bool
    host_network: bool
    network_disabled: bool
    no_new_privileges: bool
    cap_drop_all: bool
    provider_write_credentials: bool
    remediation_execution_enabled: bool
    external_actions_enabled: bool

    def __post_init__(self) -> None:
        image = _text("image_ref", self.image_ref)
        if _IMAGE_RE.fullmatch(image) is None:
            raise ValueError("production image must be pinned by sha256 digest")
        object.__setattr__(self, "image_ref", image)
        user = _text("user", self.user)
        if _USER_RE.fullmatch(user) is None:
            raise ValueError("production container user must be non-root numeric uid:gid")
        object.__setattr__(self, "user", user)
        if not self.command or any(
            not isinstance(item, str) or not item for item in self.command
        ):
            raise ValueError("production service command must be non-empty")
        required_true = (
            "read_only_root_filesystem",
            "network_disabled",
            "no_new_privileges",
            "cap_drop_all",
        )
        for name in required_true:
            if getattr(self, name) is not True:
                raise ValueError(f"{name} must be true")
        prohibited = (
            "privileged",
            "host_network",
            "provider_write_credentials",
            "remediation_execution_enabled",
            "external_actions_enabled",
        )
        for name in prohibited:
            if getattr(self, name):
                raise ValueError(f"{name} must be false")


@dataclass(frozen=True)
class ProductionDeploymentContract:
    deployment_id: str
    pilot_spec_path: str
    service: ProductionServiceContract
    volumes: tuple[ProductionVolumeContract, ...]
    pilot_plan_proof_hash: str
    provisioning_enabled: bool = False
    container_start_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "deployment_id", _text("deployment_id", self.deployment_id)
        )
        object.__setattr__(
            self, "pilot_spec_path", _text("pilot_spec_path", self.pilot_spec_path)
        )
        if self.provisioning_enabled or self.container_start_enabled:
            raise ValueError("step 13a packaging cannot provision or start containers")
        roles = tuple(volume.role for volume in self.volumes)
        if set(roles) != set(_REQUIRED_VOLUME_ROLES) or len(roles) != 4:
            raise ValueError(
                "production deployment requires exactly config/inputs/state/reports volumes"
            )
        host_paths = [str(Path(volume.host_path).resolve()) for volume in self.volumes]
        container_paths = [volume.container_path for volume in self.volumes]
        if len(set(host_paths)) != len(host_paths):
            raise ValueError("production volumes cannot share host paths")
        if len(set(container_paths)) != len(container_paths):
            raise ValueError("production volumes cannot share container paths")
        expected = "recoveryos-production-deployment:" + canonical_hash(
            self._identity()
        )
        if self.deployment_id != expected:
            raise ValueError("deployment_id does not bind production deployment")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "pilot_spec_path": self.pilot_spec_path,
            "service": {
                **asdict(self.service),
                "command": list(self.service.command),
            },
            "volumes": [asdict(volume) for volume in self.volumes],
            "pilot_plan_proof_hash": self.pilot_plan_proof_hash,
            "provisioning_enabled": False,
            "container_start_enabled": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "deployment_id": self.deployment_id,
            "proof_hash": self.proof_hash,
            "state": "PACKAGED_NOT_PROVISIONED",
        }


@dataclass(frozen=True)
class ProductionCheckResult:
    check: str
    deployment_proof_hash: str
    passed: bool
    assertions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "deployment_proof_hash": self.deployment_proof_hash,
            "passed": self.passed,
            "assertions": list(self.assertions),
        }


def _resolve_dir(base: Path, value: Any, *, name: str) -> Path:
    raw = Path(_text(name, value))
    path = raw if raw.is_absolute() else base / raw
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{name} must be an existing non-symlink directory: {path}")
    return path.resolve()


def _dir_private_shape(path: Path) -> bool:
    if os.name == "nt":
        return True
    return (path.stat().st_mode & 0o077) == 0


def build_production_deployment_contract(
    spec: Mapping[str, Any],
    *,
    base_dir: str | Path = ".",
) -> ProductionDeploymentContract:
    if spec.get("schema") != 1:
        raise ValueError("unsupported production deployment schema")
    base = Path(base_dir).resolve()
    pilot_spec_raw = Path(_text("pilot_spec", spec.get("pilot_spec")))
    pilot_spec_path = (
        pilot_spec_raw if pilot_spec_raw.is_absolute() else base / pilot_spec_raw
    )
    if pilot_spec_path.is_symlink() or not pilot_spec_path.is_file():
        raise ValueError("pilot_spec must be an existing non-symlink file")
    pilot_spec = load_pilot_spec(pilot_spec_path)
    pilot_plan: PilotDeploymentPlan = build_pilot_deployment_plan(
        pilot_spec, base_dir=base
    )

    service_raw = spec.get("service")
    volumes_raw = spec.get("volumes")
    if not isinstance(service_raw, Mapping):
        raise ValueError("service must be an object")
    if not isinstance(volumes_raw, Mapping):
        raise ValueError("volumes must be an object")

    volumes: list[ProductionVolumeContract] = []
    for role in _REQUIRED_VOLUME_ROLES:
        row = volumes_raw.get(role)
        if not isinstance(row, Mapping):
            raise ValueError(f"volumes.{role} must be an object")
        host = _resolve_dir(base, row.get("host_path"), name=f"volumes.{role}.host_path")
        private_required = bool(row.get("private_required", role in {"state", "reports"}))
        if private_required and not _dir_private_shape(host):
            raise PermissionError(f"private production directory is too permissive: {host}")
        volumes.append(ProductionVolumeContract(
            role=role,
            host_path=str(host),
            container_path=_text(
                f"volumes.{role}.container_path", row.get("container_path")
            ),
            read_only=row.get("read_only"),
            private_required=private_required,
        ))

    service = ProductionServiceContract(
        image_ref=service_raw.get("image_ref"),
        user=service_raw.get("user"),
        command=tuple(service_raw.get("command") or ()),
        read_only_root_filesystem=service_raw.get("read_only_root_filesystem"),
        privileged=service_raw.get("privileged"),
        host_network=service_raw.get("host_network"),
        network_disabled=service_raw.get("network_disabled"),
        no_new_privileges=service_raw.get("no_new_privileges"),
        cap_drop_all=service_raw.get("cap_drop_all"),
        provider_write_credentials=service_raw.get("provider_write_credentials"),
        remediation_execution_enabled=service_raw.get("remediation_execution_enabled"),
        external_actions_enabled=service_raw.get("external_actions_enabled"),
    )
    identity = {
        "schema": 1,
        "pilot_spec_path": str(pilot_spec_path.resolve()),
        "service": {
            **asdict(service),
            "command": list(service.command),
        },
        "volumes": [asdict(volume) for volume in volumes],
        "pilot_plan_proof_hash": pilot_plan.proof_hash,
        "provisioning_enabled": False,
        "container_start_enabled": False,
    }
    return ProductionDeploymentContract(
        deployment_id="recoveryos-production-deployment:" + canonical_hash(identity),
        pilot_spec_path=str(pilot_spec_path.resolve()),
        service=service,
        volumes=tuple(volumes),
        pilot_plan_proof_hash=pilot_plan.proof_hash,
        provisioning_enabled=False,
        container_start_enabled=False,
    )


def check_production_health(
    deployment: ProductionDeploymentContract,
) -> ProductionCheckResult:
    modules = (
        "recoveryworks.pilot_runner",
        "recoveryworks.cloud_assurance_report",
        "recoveryworks.integrations.cletrics_exporter",
        "recoveryworks.integrations.cletrics_continuous",
    )
    missing = [name for name in modules if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError("production runtime modules missing: " + ", ".join(missing))
    assertions = (
        "deployment contract integrity validated",
        "runtime modules importable",
        "container image digest pinned",
        "non-root user required",
        "root filesystem read-only",
        "container network disabled",
        "all Linux capabilities dropped",
        "no-new-privileges enabled",
        "provider write credentials prohibited",
        "remediation execution prohibited",
        "external actions prohibited",
    )
    return ProductionCheckResult(
        check="health",
        deployment_proof_hash=deployment.proof_hash,
        passed=True,
        assertions=assertions,
    )


def check_production_readiness(
    deployment: ProductionDeploymentContract,
) -> ProductionCheckResult:
    # Re-validate the exact pilot spec and all mounted input references.
    pilot_spec = load_pilot_spec(deployment.pilot_spec_path)
    build_pilot_deployment_plan(
        pilot_spec,
        base_dir=Path(deployment.pilot_spec_path).parent.parent,
    )
    volume_index = {volume.role: volume for volume in deployment.volumes}
    checked_paths: list[str] = []
    for role in _REQUIRED_VOLUME_ROLES:
        path = Path(volume_index[role].host_path)
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"production volume disappeared or became unsafe: {role}")
        if volume_index[role].private_required and not _dir_private_shape(path):
            raise PermissionError(f"production private volume is too permissive: {role}")
        checked_paths.append(str(path))

    # Verify private writable volumes using a private sentinel, then remove it.
    for role in ("state", "reports"):
        directory = Path(volume_index[role].host_path)
        sentinel = directory / ".recoveryos-readiness"
        atomic_private_write(sentinel, deployment.proof_hash.encode("ascii"))
        try:
            if not private_permissions_verified(sentinel):
                raise PermissionError(f"{role} readiness sentinel is not private")
        finally:
            if sentinel.exists():
                sentinel.unlink()

    assertions = (
        "pilot spec revalidated",
        "config and input mounts present",
        "state and report mounts private and writable",
        "all production mounts remain non-symlink directories",
        "no container or infrastructure provisioning performed",
    )
    return ProductionCheckResult(
        check="readiness",
        deployment_proof_hash=deployment.proof_hash,
        passed=True,
        assertions=assertions,
    )


def render_production_compose(
    deployment: ProductionDeploymentContract,
) -> str:
    volumes = {volume.role: volume for volume in deployment.volumes}
    command = json.dumps(list(deployment.service.command))
    preflight_command = json.dumps([
        "python",
        "-m",
        "recoveryworks.production_deployment",
        "--manifest",
        "/config/production.json",
        "--base-dir",
        "/workspace",
        "--check",
        "readiness",
    ])
    mounts = [
        f"      - {volumes['config'].host_path}:/config:ro",
        f"      - {volumes['inputs'].host_path}:/inputs:ro",
        f"      - {volumes['state'].host_path}:/state:rw",
        f"      - {volumes['reports'].host_path}:/reports:rw",
    ]
    common = [
        f"    image: {deployment.service.image_ref}",
        f"    user: \"{deployment.service.user}\"",
        "    read_only: true",
        "    network_mode: none",
        "    cap_drop:",
        "      - ALL",
        "    security_opt:",
        "      - no-new-privileges:true",
        "    tmpfs:",
        "      - /tmp:rw,noexec,nosuid,size=64m",
        *mounts,
    ]
    lines = [
        "services:",
        "  recoveryos-preflight:",
        *common,
        f"    command: {preflight_command}",
        "    restart: \"no\"",
        "  recoveryos-pilot:",
        *common,
        f"    command: {command}",
        "    depends_on:",
        "      recoveryos-preflight:",
        "        condition: service_completed_successfully",
        "    restart: \"no\"",
        "",
    ]
    return "\n".join(lines)


def write_production_deployment_package(
    deployment: ProductionDeploymentContract,
    *,
    manifest_path: str | Path,
    compose_path: str | Path,
) -> None:
    atomic_private_write(
        Path(manifest_path),
        (
            json.dumps(
                deployment.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    atomic_private_write(
        Path(compose_path),
        (render_production_compose(deployment) + "\n").encode("utf-8"),
    )


def load_production_spec(path: str | Path) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("production deployment spec must be readable JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError("production deployment spec must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate RecoveryOS production deployment packaging."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--check", choices=("health", "readiness"), required=True)
    args = parser.parse_args(argv)
    deployment = build_production_deployment_contract(
        load_production_spec(args.manifest),
        base_dir=args.base_dir,
    )
    result = (
        check_production_health(deployment)
        if args.check == "health"
        else check_production_readiness(deployment)
    )
    print(json.dumps(result.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
