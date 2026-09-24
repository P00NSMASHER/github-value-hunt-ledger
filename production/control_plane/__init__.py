"""Generic deterministic control-plane primitives shared by Hunter products."""

from .canonical import canonical_json_bytes, canonical_json_sha256, canonical_json_text
from .projection import (
    ProjectionContract,
    assignment_projection_errors,
    project_assignment,
    projection_sha256,
    protected_snapshot,
    validate_assignment_projection,
)
from .work import (
    WorkIdentity,
    WorkSpec,
    build_work_identity,
    validate_work_identity,
)

__all__ = [
    "ProjectionContract",
    "WorkIdentity",
    "WorkSpec",
    "build_work_identity",
    "assignment_projection_errors",
    "project_assignment",
    "projection_sha256",
    "protected_snapshot",
    "validate_assignment_projection",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "canonical_json_text",
    "validate_work_identity",
]
