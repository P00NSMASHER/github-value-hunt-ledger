"""Reproducible RecoveryWorks container build provenance."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from recoveryworks.models import canonical_hash, normalize_git_commit_sha
from recoveryworks.private_io import atomic_private_write


_PINNED_BASE_IMAGE = (
    "python:3.12.14-slim-bookworm@sha256:"
    "392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e"
)
_IMAGE_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-f]{64}$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ContainerBuildManifest:
    manifest_id: str
    source_commit: str
    base_image_ref: str
    dockerfile_sha256: str
    dependency_lock_sha256: str
    dockerfile_path: str
    dependency_lock_path: str
    runtime_dependency_count: int
    third_party_runtime_dependencies: tuple[str, ...]
    reproducible_source_inputs: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_commit",
            normalize_git_commit_sha("source_commit", self.source_commit),
        )
        if _IMAGE_RE.fullmatch(self.base_image_ref) is None:
            raise ValueError("base_image_ref must be digest pinned")
        if self.base_image_ref != _PINNED_BASE_IMAGE:
            raise ValueError("unexpected production base image")
        for name in ("dockerfile_sha256", "dependency_lock_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError(f"{name} must be lowercase SHA-256")
        if self.runtime_dependency_count != len(self.third_party_runtime_dependencies):
            raise ValueError("runtime dependency count mismatch")
        if self.runtime_dependency_count != 0:
            raise ValueError(
                "current cloud production runtime is expected to be stdlib-only"
            )
        if self.reproducible_source_inputs is not True:
            raise ValueError("build manifest must require reproducible source inputs")
        expected = "recoveryworks-container-build:" + canonical_hash(self._identity())
        if self.manifest_id != expected:
            raise ValueError("manifest_id does not bind build provenance")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "source_commit": self.source_commit,
            "base_image_ref": self.base_image_ref,
            "dockerfile_sha256": self.dockerfile_sha256,
            "dependency_lock_sha256": self.dependency_lock_sha256,
            "dockerfile_path": self.dockerfile_path,
            "dependency_lock_path": self.dependency_lock_path,
            "runtime_dependency_count": self.runtime_dependency_count,
            "third_party_runtime_dependencies": list(
                self.third_party_runtime_dependencies
            ),
            "reproducible_source_inputs": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "manifest_id": self.manifest_id,
            "proof_hash": self.proof_hash,
            "state": "SOURCE_BUILD_INPUTS_FROZEN",
        }


def _runtime_dependencies(lock_path: Path) -> tuple[str, ...]:
    dependencies: list[str] = []
    for raw in lock_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        dependencies.append(line)
    return tuple(dependencies)


def build_container_build_manifest(
    *,
    source_commit: str,
    dockerfile_path: str | Path,
    dependency_lock_path: str | Path,
) -> ContainerBuildManifest:
    dockerfile = Path(dockerfile_path)
    lock = Path(dependency_lock_path)
    if not dockerfile.is_file() or dockerfile.is_symlink():
        raise ValueError("dockerfile must be a regular file")
    if not lock.is_file() or lock.is_symlink():
        raise ValueError("dependency lock must be a regular file")
    docker_text = dockerfile.read_text(encoding="utf-8")
    if f"FROM {_PINNED_BASE_IMAGE}" not in docker_text:
        raise ValueError("Dockerfile does not use the approved digest-pinned base")
    required_fragments = (
        "USER 65532:65532",
        "PYTHONHASHSEED=0",
        "COPY freight /app/freight",
        "python -m compileall",
        'ENTRYPOINT ["python", "-m", "recoveryworks.pilot_runner"]',
    )
    missing = [value for value in required_fragments if value not in docker_text]
    if missing:
        raise ValueError(
            "Dockerfile missing production invariants: " + ", ".join(missing)
        )
    dependencies = _runtime_dependencies(lock)
    source_commit = normalize_git_commit_sha("source_commit", source_commit)
    identity = {
        "schema": 1,
        "source_commit": source_commit,
        "base_image_ref": _PINNED_BASE_IMAGE,
        "dockerfile_sha256": _sha(dockerfile),
        "dependency_lock_sha256": _sha(lock),
        "dockerfile_path": str(dockerfile),
        "dependency_lock_path": str(lock),
        "runtime_dependency_count": len(dependencies),
        "third_party_runtime_dependencies": list(dependencies),
        "reproducible_source_inputs": True,
    }
    return ContainerBuildManifest(
        manifest_id="recoveryworks-container-build:" + canonical_hash(identity),
        source_commit=source_commit,
        base_image_ref=_PINNED_BASE_IMAGE,
        dockerfile_sha256=identity["dockerfile_sha256"],
        dependency_lock_sha256=identity["dependency_lock_sha256"],
        dockerfile_path=str(dockerfile),
        dependency_lock_path=str(lock),
        runtime_dependency_count=len(dependencies),
        third_party_runtime_dependencies=dependencies,
        reproducible_source_inputs=True,
    )


def write_container_build_manifest(
    manifest: ContainerBuildManifest,
    path: str | Path,
) -> None:
    atomic_private_write(
        Path(path),
        (
            json.dumps(
                manifest.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze RecoveryWorks production container source inputs."
    )
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--dockerfile",
        default="recoveryworks/deploy/Dockerfile.production",
    )
    parser.add_argument(
        "--lock",
        default="recoveryworks/requirements.production.lock",
    )
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    manifest = build_container_build_manifest(
        source_commit=args.source_commit,
        dockerfile_path=args.dockerfile,
        dependency_lock_path=args.lock,
    )
    if args.output:
        write_container_build_manifest(manifest, args.output)
    print(json.dumps(manifest.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
