"""Tamper-evident RecoveryWorks pilot execution lifecycle."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping

from recoveryworks.models import canonical_hash, normalize_sha256, normalize_utc_timestamp
from recoveryworks.pilot_kickoff import PilotKickoffGate
from recoveryworks.private_io import atomic_private_write, private_file_lock


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


class PilotExecutionState(str, Enum):
    KICKOFF_AUTHORIZED = "KICKOFF_AUTHORIZED"
    INTAKE_FROZEN = "INTAKE_FROZEN"
    DIAGNOSTIC_COMPLETE = "DIAGNOSTIC_COMPLETE"
    EVIDENCE_REVIEW_COMPLETE = "EVIDENCE_REVIEW_COMPLETE"
    BUYER_REVIEW_READY = "BUYER_REVIEW_READY"
    CLOSEOUT_READY = "CLOSEOUT_READY"
    CLOSED = "CLOSED"


_ALLOWED = {
    PilotExecutionState.KICKOFF_AUTHORIZED: {PilotExecutionState.INTAKE_FROZEN},
    PilotExecutionState.INTAKE_FROZEN: {PilotExecutionState.DIAGNOSTIC_COMPLETE},
    PilotExecutionState.DIAGNOSTIC_COMPLETE: {PilotExecutionState.EVIDENCE_REVIEW_COMPLETE},
    PilotExecutionState.EVIDENCE_REVIEW_COMPLETE: {PilotExecutionState.BUYER_REVIEW_READY},
    PilotExecutionState.BUYER_REVIEW_READY: {PilotExecutionState.CLOSEOUT_READY},
    PilotExecutionState.CLOSEOUT_READY: {PilotExecutionState.CLOSED},
    PilotExecutionState.CLOSED: set(),
}


@dataclass(frozen=True)
class PilotExecutionEvent:
    sequence: int
    engagement_id: str
    kickoff_gate_proof_hash: str
    state: PilotExecutionState
    actor_id: str
    occurred_at: str
    evidence_hashes: tuple[str, ...]
    note: str
    previous_hash: str | None
    event_hash: str

    @classmethod
    def build(
        cls,
        *,
        sequence: int,
        engagement_id: str,
        kickoff_gate_proof_hash: str,
        state: PilotExecutionState,
        actor_id: str,
        occurred_at: str,
        evidence_hashes: tuple[str, ...],
        note: str,
        previous_hash: str | None,
    ) -> "PilotExecutionEvent":
        if type(sequence) is not int or sequence < 1:
            raise ValueError("sequence must be positive")
        if not isinstance(state, PilotExecutionState):
            raise ValueError("state must be PilotExecutionState")
        hashes = tuple(sorted(normalize_sha256("evidence_hash", h) for h in evidence_hashes))
        if not hashes:
            raise ValueError("pilot execution transitions require evidence hashes")
        fields = {
            "sequence": sequence,
            "engagement_id": _text("engagement_id", engagement_id),
            "kickoff_gate_proof_hash": normalize_sha256(
                "kickoff_gate_proof_hash", kickoff_gate_proof_hash
            ),
            "state": state,
            "actor_id": _text("actor_id", actor_id),
            "occurred_at": normalize_utc_timestamp("occurred_at", occurred_at),
            "evidence_hashes": hashes,
            "note": _text("note", note),
            "previous_hash": previous_hash,
        }
        identity = {
            "schema": 1,
            **fields,
            "state": state.value,
            "evidence_hashes": list(hashes),
        }
        return cls(**fields, event_hash=canonical_hash(identity))

    def verify(self, previous_hash: str | None) -> None:
        rebuilt = PilotExecutionEvent.build(
            sequence=self.sequence,
            engagement_id=self.engagement_id,
            kickoff_gate_proof_hash=self.kickoff_gate_proof_hash,
            state=self.state,
            actor_id=self.actor_id,
            occurred_at=self.occurred_at,
            evidence_hashes=self.evidence_hashes,
            note=self.note,
            previous_hash=self.previous_hash,
        )
        if self.previous_hash != previous_hash:
            raise ValueError("pilot execution previous_hash mismatch")
        if rebuilt.event_hash != self.event_hash:
            raise ValueError("pilot execution event hash mismatch")

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "engagement_id": self.engagement_id,
            "kickoff_gate_proof_hash": self.kickoff_gate_proof_hash,
            "state": self.state.value,
            "actor_id": self.actor_id,
            "occurred_at": self.occurred_at,
            "evidence_hashes": list(self.evidence_hashes),
            "note": self.note,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }


class PilotExecutionJournal:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name("." + self.path.name + ".lock")

    def _read(self) -> tuple[PilotExecutionEvent, ...]:
        if not self.path.exists():
            return ()
        envelope = json.loads(self.path.read_text(encoding="utf-8"))
        if envelope.get("schema") != 1:
            raise ValueError("unsupported pilot execution journal schema")
        previous = None
        events = []
        for index, row in enumerate(envelope.get("events", []), start=1):
            if not isinstance(row, dict):
                raise ValueError("pilot execution row is malformed")
            try:
                event = PilotExecutionEvent(
                    sequence=row["sequence"],
                    engagement_id=row["engagement_id"],
                    kickoff_gate_proof_hash=row["kickoff_gate_proof_hash"],
                    state=PilotExecutionState(row["state"]),
                    actor_id=row["actor_id"],
                    occurred_at=row["occurred_at"],
                    evidence_hashes=tuple(row["evidence_hashes"]),
                    note=row["note"],
                    previous_hash=row.get("previous_hash"),
                    event_hash=row["event_hash"],
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("pilot execution row is malformed") from exc
            if event.sequence != index:
                raise ValueError("pilot execution sequence gap")
            event.verify(previous)
            events.append(event)
            previous = event.event_hash
        if envelope.get("head_hash") != previous:
            raise ValueError("pilot execution head hash mismatch")
        canonical = {
            "schema": 1,
            "head_hash": previous,
            "events": [event.as_dict() for event in events],
        }
        if envelope.get("state_hash") != canonical_hash(canonical):
            raise ValueError("pilot execution state hash mismatch")
        return tuple(events)

    def events(self) -> tuple[PilotExecutionEvent, ...]:
        return self._read()

    def append(
        self,
        kickoff: PilotKickoffGate,
        *,
        state: PilotExecutionState,
        actor_id: str,
        occurred_at: str,
        evidence_hashes: tuple[str, ...],
        note: str,
    ) -> PilotExecutionEvent:
        with private_file_lock(self.lock_path):
            events = list(self._read())
            if not events:
                if state is not PilotExecutionState.KICKOFF_AUTHORIZED:
                    raise ValueError("pilot execution must begin at KICKOFF_AUTHORIZED")
            else:
                if events[-1].kickoff_gate_proof_hash != kickoff.proof_hash:
                    raise ValueError("pilot execution kickoff proof changed")
                if events[-1].engagement_id != kickoff.engagement_id:
                    raise ValueError("pilot execution engagement changed")
                if state not in _ALLOWED[events[-1].state]:
                    raise ValueError(
                        f"invalid pilot transition: {events[-1].state.value} -> {state.value}"
                    )
            evidence = tuple(evidence_hashes)
            if state is PilotExecutionState.KICKOFF_AUTHORIZED:
                evidence = tuple(set((*evidence, kickoff.proof_hash)))
            previous = events[-1].event_hash if events else None
            event = PilotExecutionEvent.build(
                sequence=len(events) + 1,
                engagement_id=kickoff.engagement_id,
                kickoff_gate_proof_hash=kickoff.proof_hash,
                state=state,
                actor_id=actor_id,
                occurred_at=occurred_at,
                evidence_hashes=evidence,
                note=note,
                previous_hash=previous,
            )
            events.append(event)
            canonical = {
                "schema": 1,
                "head_hash": event.event_hash,
                "events": [item.as_dict() for item in events],
            }
            atomic_private_write(
                self.path,
                (
                    json.dumps(
                        {**canonical, "state_hash": canonical_hash(canonical)},
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8"),
            )
            return event
