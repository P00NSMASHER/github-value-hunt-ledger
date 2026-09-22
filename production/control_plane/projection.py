from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .canonical import canonical_json_sha256, canonical_json_text


PROJECTION_SCHEMA = "control-plane-projection-v1"


def _unique_nonempty_strings(
    name: str,
    values: Sequence[str],
) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must contain non-empty strings")
        if value in seen:
            raise ValueError(f"{name} contains duplicate field {value}")
        seen.add(value)
        out.append(value)
    return tuple(out)


@dataclass(frozen=True)
class ProjectionContract:
    """Declarative boundary between candidate semantics and assignment metadata."""

    name: str
    protected_fields: tuple[str, ...]
    normalized_list_fields: tuple[str, ...] = ()
    required_candidate_fields: tuple[str, ...] = ()
    projection_hash_field: str = "projection_sha256"

    def __init__(
        self,
        *,
        name: str,
        protected_fields: Sequence[str],
        normalized_list_fields: Sequence[str] = (),
        required_candidate_fields: Sequence[str] = (),
        projection_hash_field: str = "projection_sha256",
    ) -> None:
        if not isinstance(name, str) or not name:
            raise ValueError("contract name is required")
        protected = _unique_nonempty_strings(
            "protected_fields",
            protected_fields,
        )
        normalized = _unique_nonempty_strings(
            "normalized_list_fields",
            normalized_list_fields,
        )
        required = _unique_nonempty_strings(
            "required_candidate_fields",
            required_candidate_fields,
        )
        if not protected:
            raise ValueError("protected_fields must not be empty")
        if not set(normalized).issubset(protected):
            raise ValueError(
                "normalized_list_fields must be protected fields"
            )
        if not set(required).issubset(protected):
            raise ValueError(
                "required_candidate_fields must be protected fields"
            )
        if (
            not isinstance(projection_hash_field, str)
            or not projection_hash_field
        ):
            raise ValueError("projection_hash_field is required")
        if projection_hash_field in protected:
            raise ValueError(
                "projection_hash_field cannot also be protected"
            )

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "protected_fields", protected)
        object.__setattr__(
            self,
            "normalized_list_fields",
            normalized,
        )
        object.__setattr__(
            self,
            "required_candidate_fields",
            required,
        )
        object.__setattr__(
            self,
            "projection_hash_field",
            projection_hash_field,
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": PROJECTION_SCHEMA,
            "name": self.name,
            "protected_fields": list(self.protected_fields),
            "normalized_list_fields": list(
                self.normalized_list_fields
            ),
            "required_candidate_fields": list(
                self.required_candidate_fields
            ),
            "projection_hash_field": self.projection_hash_field,
        }


def _normalized_value(
    field: str,
    value: Any,
    contract: ProjectionContract,
) -> Any:
    if field not in contract.normalized_list_fields:
        return value
    if value is None:
        return []
    if not isinstance(value, list):
        raise TypeError(
            f"{field} must be a list or null for list normalization"
        )
    return value


def protected_snapshot(
    candidate: Mapping[str, Any],
    contract: ProjectionContract,
) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise TypeError("candidate must be a mapping")
    if not isinstance(contract, ProjectionContract):
        raise TypeError("contract must be a ProjectionContract")

    missing = [
        field
        for field in contract.required_candidate_fields
        if field not in candidate
        or candidate.get(field) is None
        or candidate.get(field) == ""
    ]
    if missing:
        raise ValueError(
            "candidate missing required protected fields: "
            + ", ".join(missing)
        )

    snapshot = {
        field: _normalized_value(
            field,
            candidate.get(field),
            contract,
        )
        for field in contract.protected_fields
    }
    # Canonical round-trip both validates JSON and deep-copies nested values,
    # so assignment mutations can never mutate the source candidate by alias.
    return json.loads(canonical_json_text(snapshot))


def projection_sha256(
    candidate: Mapping[str, Any],
    contract: ProjectionContract,
) -> str:
    return canonical_json_sha256(
        {
            "schema": PROJECTION_SCHEMA,
            "contract": contract.identity_payload(),
            "protected": protected_snapshot(candidate, contract),
        }
    )


def project_assignment(
    candidate: Mapping[str, Any],
    assignment_fields: Mapping[str, Any],
    contract: ProjectionContract,
) -> dict[str, Any]:
    """Copy protected candidate state and add assignment-only metadata."""
    if not isinstance(assignment_fields, Mapping):
        raise TypeError("assignment_fields must be a mapping")
    snapshot = protected_snapshot(candidate, contract)

    forbidden = set(snapshot)
    forbidden.add(contract.projection_hash_field)
    overlap = sorted(forbidden.intersection(assignment_fields))
    if overlap:
        raise ValueError(
            "assignment_fields cannot override protected fields: "
            + ", ".join(overlap)
        )

    assignment = dict(snapshot)
    assignment.update(dict(assignment_fields))
    assignment[contract.projection_hash_field] = projection_sha256(
        candidate,
        contract,
    )
    canonical_json_text(assignment)
    return assignment


def assignment_projection_errors(
    candidate: Mapping[str, Any],
    assignment: Mapping[str, Any],
    contract: ProjectionContract,
) -> tuple[str, ...]:
    if not isinstance(assignment, Mapping):
        raise TypeError("assignment must be a mapping")

    try:
        expected = protected_snapshot(candidate, contract)
    except (TypeError, ValueError) as exc:
        return (f"candidate_invalid:{exc}",)

    errors: list[str] = []
    for field, expected_value in expected.items():
        try:
            actual = _normalized_value(
                field,
                assignment.get(field),
                contract,
            )
        except TypeError:
            errors.append(f"protected_field_invalid:{field}")
            continue
        if actual != expected_value:
            errors.append(f"protected_field_drift:{field}")

    supplied_hash = assignment.get(contract.projection_hash_field)
    if not isinstance(supplied_hash, str):
        errors.append("projection_hash_missing")
    else:
        expected_hash = projection_sha256(candidate, contract)
        if supplied_hash != expected_hash:
            errors.append("projection_hash_mismatch")

    return tuple(sorted(set(errors)))


def validate_assignment_projection(
    candidate: Mapping[str, Any],
    assignment: Mapping[str, Any],
    contract: ProjectionContract,
) -> None:
    errors = assignment_projection_errors(
        candidate,
        assignment,
        contract,
    )
    if errors:
        raise ValueError(
            "invalid assignment projection: " + "; ".join(errors)
        )
