from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .canonical import canonical_json_sha256, canonical_json_text


_TOKEN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_REVISION = re.compile(r"^[a-f0-9]{64}$")
WORK_SCHEMA = "control-plane-work-v1"


def _require_token(name: str, value: Any) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError(
            f"{name} must match [a-z0-9][a-z0-9-]{{0,63}}"
        )
    return value


@dataclass(frozen=True, init=False)
class WorkSpec:
    """Immutable semantic description of one unit of control-plane work."""

    namespace: str
    kind: str
    source_id: str
    schema_version: int
    _semantic_json: str = field(repr=False)

    def __init__(
        self,
        *,
        namespace: str,
        kind: str,
        source_id: str,
        semantic: Mapping[str, Any],
        schema_version: int = 1,
    ) -> None:
        namespace = _require_token("namespace", namespace)
        kind = _require_token("kind", kind)
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id is required")
        if schema_version != 1:
            raise ValueError("unsupported WorkSpec schema_version")
        if not isinstance(semantic, Mapping):
            raise TypeError("semantic must be a mapping")

        semantic_json = canonical_json_text(dict(semantic))
        object.__setattr__(self, "namespace", namespace)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "_semantic_json", semantic_json)

    @property
    def semantic(self) -> dict[str, Any]:
        # Return a new object so callers cannot mutate the frozen specification.
        return json.loads(self._semantic_json)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": WORK_SCHEMA,
            "schema_version": self.schema_version,
            "namespace": self.namespace,
            "kind": self.kind,
            "source_id": self.source_id,
            "semantic": self.semantic,
        }


@dataclass(frozen=True, init=False)
class WorkIdentity:
    """Durable semantic identity with a short display ID and full SHA-256."""

    work_id: str
    revision_sha256: str
    _identity_payload_json: str = field(repr=False)

    def __init__(
        self,
        *,
        work_id: str,
        revision_sha256: str,
        identity_payload: Mapping[str, Any],
    ) -> None:
        if not isinstance(work_id, str) or not work_id:
            raise ValueError("work_id is required")
        if not isinstance(revision_sha256, str):
            raise ValueError("revision_sha256 is required")
        if not isinstance(identity_payload, Mapping):
            raise TypeError("identity_payload must be a mapping")

        object.__setattr__(self, "work_id", work_id)
        object.__setattr__(self, "revision_sha256", revision_sha256)
        object.__setattr__(
            self,
            "_identity_payload_json",
            canonical_json_text(dict(identity_payload)),
        )

    @property
    def identity_payload(self) -> dict[str, Any]:
        return json.loads(self._identity_payload_json)


def build_work_identity(spec: WorkSpec) -> WorkIdentity:
    if not isinstance(spec, WorkSpec):
        raise TypeError("spec must be a WorkSpec")
    payload = spec.identity_payload()
    revision = canonical_json_sha256(payload)
    work_id = (
        f"WORK:{spec.namespace}:{spec.kind}:{revision[:16]}"
    )
    return WorkIdentity(
        work_id=work_id,
        revision_sha256=revision,
        identity_payload=payload,
    )


def _spec_from_identity_payload(
    payload: Mapping[str, Any],
) -> WorkSpec:
    if payload.get("schema") != WORK_SCHEMA:
        raise ValueError("unsupported work identity schema")
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported work identity schema_version")
    semantic = payload.get("semantic")
    if not isinstance(semantic, Mapping):
        raise ValueError("work identity semantic payload is required")
    return WorkSpec(
        namespace=payload.get("namespace"),
        kind=payload.get("kind"),
        source_id=payload.get("source_id"),
        semantic=semantic,
        schema_version=payload.get("schema_version"),
    )


def validate_work_identity(identity: WorkIdentity) -> None:
    """Recompute identity from its semantic payload and fail on any drift."""
    if not isinstance(identity, WorkIdentity):
        raise TypeError("identity must be a WorkIdentity")
    if not _REVISION.fullmatch(identity.revision_sha256):
        raise ValueError("revision_sha256 must be 64 lowercase hex characters")

    rebuilt = build_work_identity(
        _spec_from_identity_payload(identity.identity_payload)
    )
    if rebuilt.revision_sha256 != identity.revision_sha256:
        raise ValueError("revision_sha256 does not match semantic payload")
    if rebuilt.work_id != identity.work_id:
        raise ValueError("work_id does not match semantic payload")
