"""Generic deterministic control-plane primitives shared by Hunter products."""

from .canonical import canonical_json_bytes, canonical_json_sha256, canonical_json_text
from .work import (
    WorkIdentity,
    WorkSpec,
    build_work_identity,
    validate_work_identity,
)

__all__ = [
    "WorkIdentity",
    "WorkSpec",
    "build_work_identity",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "canonical_json_text",
    "validate_work_identity",
]
