"""Tamper-evident production incident lifecycle and post-incident review."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.incident_rollback import (
    ProductionIncidentAssessment,
    ValidatedRollbackReceipt,
)
from recoveryworks.models import (
    canonical_hash,
    freeze_json,
    normalize_sha256,
    normalize_utc_timestamp,
)
from recoveryworks.private_io import atomic_private_write, private_file_lock


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    normalized = value.strip()
    if any(ord(character) < 32 for character in normalized):
        raise ValueError(f"{name} cannot contain control characters")
    return normalized


class IncidentLifecycleState(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    ROLLBACK_APPROVED = "ROLLBACK_APPROVED"
    ROLLBACK_HANDOFF = "ROLLBACK_HANDOFF"
    ROLLBACK_VERIFIED = "ROLLBACK_VERIFIED"
    RECOVERY_CONFIRMED = "RECOVERY_CONFIRMED"
    CLOSED = "CLOSED"
    REVIEWED = "REVIEWED"


@dataclass(frozen=True)
class IncidentLifecycleEvent:
    sequence: int
    incident_id: str
    incident_proof_hash: str
    state: IncidentLifecycleState
    actor_id: str
    occurred_at: str
    note: str
    evidence_hashes: tuple[str, ...]
    metadata: Mapping[str, Any]
    previous_hash: str | None
    event_hash: str

    @classmethod
    def build(
        cls,
        *,
        sequence: int,
        incident_id: str,
        incident_proof_hash: str,
        state: IncidentLifecycleState,
        actor_id: str,
        occurred_at: str,
        note: str,
        evidence_hashes: tuple[str, ...] = (),
        metadata: Mapping[str, Any] | None = None,
        previous_hash: str | None = None,
    ) -> "IncidentLifecycleEvent":
        if type(sequence) is not int or sequence < 1:
            raise ValueError("incident event sequence must be positive")
        if not isinstance(state, IncidentLifecycleState):
            raise ValueError("state must be IncidentLifecycleState")
        hashes = tuple(
            sorted(normalize_sha256("evidence_hash", value) for value in evidence_hashes)
        )
        fields = {
            "sequence": sequence,
            "incident_id": _text("incident_id", incident_id),
            "incident_proof_hash": normalize_sha256(
                "incident_proof_hash", incident_proof_hash
            ),
            "state": state,
            "actor_id": _text("actor_id", actor_id),
            "occurred_at": normalize_utc_timestamp("occurred_at", occurred_at),
            "note": _text("note", note),
            "evidence_hashes": hashes,
            "metadata": freeze_json(metadata or {}, name="metadata"),
            "previous_hash": previous_hash,
        }
        identity = {
            "schema": 1,
            **fields,
            "state": state.value,
            "metadata": dict(fields["metadata"]),
            "evidence_hashes": list(hashes),
        }
        return cls(**fields, event_hash=canonical_hash(identity))

    def verify(self, previous_hash: str | None) -> None:
        if self.previous_hash != previous_hash:
            raise ValueError("incident journal previous_hash mismatch")
        rebuilt = IncidentLifecycleEvent.build(
            sequence=self.sequence,
            incident_id=self.incident_id,
            incident_proof_hash=self.incident_proof_hash,
            state=self.state,
            actor_id=self.actor_id,
            occurred_at=self.occurred_at,
            note=self.note,
            evidence_hashes=self.evidence_hashes,
            metadata=self.metadata,
            previous_hash=self.previous_hash,
        )
        if rebuilt.event_hash != self.event_hash:
            raise ValueError("incident journal event hash mismatch")

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "incident_id": self.incident_id,
            "incident_proof_hash": self.incident_proof_hash,
            "state": self.state.value,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at,
            "note": self.note,
            "evidence_hashes": list(self.evidence_hashes),
            "metadata": dict(self.metadata),
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }


_ALLOWED_TRANSITIONS = {
    IncidentLifecycleState.DETECTED: {
        IncidentLifecycleState.ACKNOWLEDGED,
    },
    IncidentLifecycleState.ACKNOWLEDGED: {
        IncidentLifecycleState.ESCALATED,
        IncidentLifecycleState.ROLLBACK_APPROVED,
    },
    IncidentLifecycleState.ESCALATED: {
        IncidentLifecycleState.ROLLBACK_APPROVED,
    },
    IncidentLifecycleState.ROLLBACK_APPROVED: {
        IncidentLifecycleState.ROLLBACK_HANDOFF,
    },
    IncidentLifecycleState.ROLLBACK_HANDOFF: {
        IncidentLifecycleState.ROLLBACK_VERIFIED,
    },
    IncidentLifecycleState.ROLLBACK_VERIFIED: {
        IncidentLifecycleState.RECOVERY_CONFIRMED,
    },
    IncidentLifecycleState.RECOVERY_CONFIRMED: {
        IncidentLifecycleState.CLOSED,
    },
    IncidentLifecycleState.CLOSED: {
        IncidentLifecycleState.REVIEWED,
    },
    IncidentLifecycleState.REVIEWED: set(),
}


class IncidentLifecycleJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def _load(self) -> tuple[str | None, list[IncidentLifecycleEvent]]:
        if not self.path.exists():
            return None, []
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("incident journal is not valid JSON") from exc
        if envelope.get("schema") != 1:
            raise ValueError("unsupported incident journal schema")
        rows = envelope.get("events")
        if not isinstance(rows, list):
            raise ValueError("incident journal events must be a list")
        events: list[IncidentLifecycleEvent] = []
        previous = None
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError("incident journal row must be an object")
            try:
                state = IncidentLifecycleState(row["state"])
            except (KeyError, ValueError) as exc:
                raise ValueError("invalid incident journal state") from exc
            event = IncidentLifecycleEvent(
                sequence=row["sequence"],
                incident_id=row["incident_id"],
                incident_proof_hash=row["incident_proof_hash"],
                state=state,
                actor_id=row["actor_id"],
                occurred_at=row["occurred_at"],
                note=row["note"],
                evidence_hashes=tuple(row.get("evidence_hashes", ())),
                metadata=row.get("metadata", {}),
                previous_hash=row.get("previous_hash"),
                event_hash=row["event_hash"],
            )
            event.verify(previous)
            if event.sequence != len(events) + 1:
                raise ValueError("incident journal sequence gap")
            previous = event.event_hash
            events.append(event)
        head = envelope.get("head_hash")
        if head != previous:
            raise ValueError("incident journal head hash mismatch")
        canonical = {
            "schema": 1,
            "head_hash": head,
            "events": [event.as_dict() for event in events],
        }
        expected_state_hash = canonical_hash(canonical)
        if envelope.get("state_hash") != expected_state_hash:
            raise ValueError("incident journal state hash mismatch")
        return head, events

    def events(self) -> tuple[IncidentLifecycleEvent, ...]:
        with private_file_lock(self.lock_path):
            _, events = self._load()
            return tuple(events)

    def append(
        self,
        incident: ProductionIncidentAssessment,
        *,
        state: IncidentLifecycleState,
        actor_id: str,
        occurred_at: str,
        note: str,
        evidence_hashes: tuple[str, ...] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> IncidentLifecycleEvent:
        with private_file_lock(self.lock_path):
            head, events = self._load()
            scoped = [event for event in events if event.incident_id == incident.incident_id]
            if not scoped:
                if state is not IncidentLifecycleState.DETECTED:
                    raise ValueError("incident lifecycle must begin at DETECTED")
            else:
                current = scoped[-1].state
                if state not in _ALLOWED_TRANSITIONS[current]:
                    raise ValueError(
                        f"invalid incident transition: {current.value} -> {state.value}"
                    )
            event = IncidentLifecycleEvent.build(
                sequence=len(events) + 1,
                incident_id=incident.incident_id,
                incident_proof_hash=incident.proof_hash,
                state=state,
                actor_id=actor_id,
                occurred_at=occurred_at,
                note=note,
                evidence_hashes=evidence_hashes,
                metadata=metadata,
                previous_hash=head,
            )
            events.append(event)
            canonical = {
                "schema": 1,
                "head_hash": event.event_hash,
                "events": [item.as_dict() for item in events],
            }
            envelope = {
                **canonical,
                "state_hash": canonical_hash(canonical),
            }
            atomic_private_write(
                self.path,
                (
                    json.dumps(
                        envelope,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                    )
                    + "\n"
                ).encode("utf-8"),
            )
            return event


@dataclass(frozen=True)
class IncidentClosureEvidence:
    closure_id: str
    incident_id: str
    incident_proof_hash: str
    rollback_receipt_proof_hash: str
    recovered_environment_snapshot_proof_hash: str
    closed_by: str
    closed_at: str
    closure_reason: str
    verified: bool = True

    def __post_init__(self) -> None:
        for name in ("incident_id", "closed_by", "closure_reason"):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in (
            "incident_proof_hash",
            "rollback_receipt_proof_hash",
            "recovered_environment_snapshot_proof_hash",
        ):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "closed_at",
            normalize_utc_timestamp("closed_at", self.closed_at)
        )
        if self.verified is not True:
            raise ValueError("closure evidence must be verified")
        expected = "recoveryworks-incident-closure:" + canonical_hash(self._identity())
        if self.closure_id != expected:
            raise ValueError("closure_id does not bind closure evidence")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "incident_id": self.incident_id,
            "incident_proof_hash": self.incident_proof_hash,
            "rollback_receipt_proof_hash": self.rollback_receipt_proof_hash,
            "recovered_environment_snapshot_proof_hash":
                self.recovered_environment_snapshot_proof_hash,
            "closed_by": self.closed_by,
            "closed_at": self.closed_at,
            "closure_reason": self.closure_reason,
            "verified": True,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())


def build_incident_closure(
    incident: ProductionIncidentAssessment,
    rollback: ValidatedRollbackReceipt,
    *,
    recovered_environment_snapshot_proof_hash: str,
    closed_by: str,
    closed_at: str,
    closure_reason: str,
) -> IncidentClosureEvidence:
    identity = {
        "schema": 1,
        "incident_id": incident.incident_id,
        "incident_proof_hash": incident.proof_hash,
        "rollback_receipt_proof_hash": rollback.proof_hash,
        "recovered_environment_snapshot_proof_hash": normalize_sha256(
            "recovered_environment_snapshot_proof_hash",
            recovered_environment_snapshot_proof_hash,
        ),
        "closed_by": _text("closed_by", closed_by),
        "closed_at": normalize_utc_timestamp("closed_at", closed_at),
        "closure_reason": _text("closure_reason", closure_reason),
        "verified": True,
    }
    return IncidentClosureEvidence(
        closure_id="recoveryworks-incident-closure:" + canonical_hash(identity),
        incident_id=incident.incident_id,
        incident_proof_hash=incident.proof_hash,
        rollback_receipt_proof_hash=rollback.proof_hash,
        recovered_environment_snapshot_proof_hash=
            identity["recovered_environment_snapshot_proof_hash"],
        closed_by=closed_by,
        closed_at=closed_at,
        closure_reason=closure_reason,
        verified=True,
    )


@dataclass(frozen=True)
class PostIncidentReview:
    review_id: str
    incident_id: str
    incident_proof_hash: str
    closure_proof_hash: str
    reviewer_id: str
    reviewed_at: str
    root_cause: str
    contributing_factors: tuple[str, ...]
    corrective_actions: tuple[str, ...]
    preventive_actions: tuple[str, ...]
    followup_owner_id: str
    followup_due_at: str
    actions_executed: bool = False

    def __post_init__(self) -> None:
        for name in (
            "incident_id", "reviewer_id", "root_cause",
            "followup_owner_id",
        ):
            object.__setattr__(self, name, _text(name, getattr(self, name)))
        for name in ("incident_proof_hash", "closure_proof_hash"):
            object.__setattr__(
                self, name, normalize_sha256(name, getattr(self, name))
            )
        object.__setattr__(
            self, "reviewed_at",
            normalize_utc_timestamp("reviewed_at", self.reviewed_at)
        )
        object.__setattr__(
            self, "followup_due_at",
            normalize_utc_timestamp("followup_due_at", self.followup_due_at)
        )
        for name in (
            "contributing_factors", "corrective_actions", "preventive_actions"
        ):
            values = tuple(_text(name, value) for value in getattr(self, name))
            if not values:
                raise ValueError(f"{name} must be non-empty")
            object.__setattr__(self, name, values)
        if self.actions_executed:
            raise ValueError("post-incident review cannot claim actions executed")
        expected = "recoveryworks-post-incident-review:" + canonical_hash(
            self._identity()
        )
        if self.review_id != expected:
            raise ValueError("review_id does not bind post-incident review")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "incident_id": self.incident_id,
            "incident_proof_hash": self.incident_proof_hash,
            "closure_proof_hash": self.closure_proof_hash,
            "reviewer_id": self.reviewer_id,
            "reviewed_at": self.reviewed_at,
            "root_cause": self.root_cause,
            "contributing_factors": list(self.contributing_factors),
            "corrective_actions": list(self.corrective_actions),
            "preventive_actions": list(self.preventive_actions),
            "followup_owner_id": self.followup_owner_id,
            "followup_due_at": self.followup_due_at,
            "actions_executed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "review_id": self.review_id,
            "proof_hash": self.proof_hash,
            "state": "POST_INCIDENT_REVIEW_RECORDED",
        }


def build_post_incident_review(
    incident: ProductionIncidentAssessment,
    closure: IncidentClosureEvidence,
    *,
    reviewer_id: str,
    reviewed_at: str,
    root_cause: str,
    contributing_factors: tuple[str, ...],
    corrective_actions: tuple[str, ...],
    preventive_actions: tuple[str, ...],
    followup_owner_id: str,
    followup_due_at: str,
) -> PostIncidentReview:
    if closure.incident_id != incident.incident_id:
        raise ValueError("closure incident mismatch")
    if closure.incident_proof_hash != incident.proof_hash:
        raise ValueError("closure incident proof mismatch")
    identity = {
        "schema": 1,
        "incident_id": incident.incident_id,
        "incident_proof_hash": incident.proof_hash,
        "closure_proof_hash": closure.proof_hash,
        "reviewer_id": _text("reviewer_id", reviewer_id),
        "reviewed_at": normalize_utc_timestamp("reviewed_at", reviewed_at),
        "root_cause": _text("root_cause", root_cause),
        "contributing_factors": list(contributing_factors),
        "corrective_actions": list(corrective_actions),
        "preventive_actions": list(preventive_actions),
        "followup_owner_id": _text("followup_owner_id", followup_owner_id),
        "followup_due_at": normalize_utc_timestamp(
            "followup_due_at", followup_due_at
        ),
        "actions_executed": False,
    }
    return PostIncidentReview(
        review_id="recoveryworks-post-incident-review:" + canonical_hash(identity),
        incident_id=incident.incident_id,
        incident_proof_hash=incident.proof_hash,
        closure_proof_hash=closure.proof_hash,
        reviewer_id=reviewer_id,
        reviewed_at=reviewed_at,
        root_cause=root_cause,
        contributing_factors=contributing_factors,
        corrective_actions=corrective_actions,
        preventive_actions=preventive_actions,
        followup_owner_id=followup_owner_id,
        followup_due_at=followup_due_at,
        actions_executed=False,
    )
