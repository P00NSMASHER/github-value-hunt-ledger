"""Tamper-evident durable journal for RecoveryWorks.

The journal records every lifecycle transition as a hash-chained event. Bundles
are deterministic JSON-compatible structures that can be stored in a private
durable store and verified before replay.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .models import (
    Branch,
    EvidenceRef,
    FindingState,
    RecoveryFinding,
    RecoveryMode,
    RuleRef,
    canonical_hash,
)


@dataclass(frozen=True)
class JournalEvent:
    sequence: int
    action: str
    finding_id: str
    payload: Mapping[str, Any]
    previous_hash: str | None
    event_hash: str

    @classmethod
    def build(
        cls,
        *,
        sequence: int,
        action: str,
        finding_id: str,
        payload: Mapping[str, Any],
        previous_hash: str | None,
    ) -> "JournalEvent":
        if sequence < 1:
            raise ValueError("sequence must be positive")
        if not action.strip() or not finding_id.strip():
            raise ValueError("action and finding_id are required")
        body = {
            "schema": 1,
            "sequence": sequence,
            "action": action.strip(),
            "finding_id": finding_id.strip(),
            "payload": dict(payload),
            "previous_hash": previous_hash,
        }
        return cls(
            sequence=sequence,
            action=body["action"],
            finding_id=body["finding_id"],
            payload=body["payload"],
            previous_hash=previous_hash,
            event_hash=canonical_hash(body),
        )

    def verify(self, expected_previous: str | None) -> None:
        if self.previous_hash != expected_previous:
            raise ValueError("journal chain previous_hash mismatch")
        rebuilt = JournalEvent.build(
            sequence=self.sequence,
            action=self.action,
            finding_id=self.finding_id,
            payload=self.payload,
            previous_hash=self.previous_hash,
        )
        if rebuilt.event_hash != self.event_hash:
            raise ValueError("journal event hash mismatch")


class RecoveryJournal:
    def __init__(self) -> None:
        self._events: list[JournalEvent] = []

    @property
    def head_hash(self) -> str | None:
        return self._events[-1].event_hash if self._events else None

    def append(self, action: str, finding_id: str, payload: Mapping[str, Any]) -> JournalEvent:
        event = JournalEvent.build(
            sequence=len(self._events) + 1,
            action=action,
            finding_id=finding_id,
            payload=payload,
            previous_hash=self.head_hash,
        )
        self._events.append(event)
        return event

    def events(self) -> tuple[JournalEvent, ...]:
        return tuple(self._events)

    def verify(self) -> None:
        previous = None
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.sequence != expected_sequence:
                raise ValueError("journal sequence gap")
            event.verify(previous)
            previous = event.event_hash

    def export(self) -> dict[str, Any]:
        self.verify()
        return {
            "schema": 1,
            "head_hash": self.head_hash,
            "events": [asdict(event) for event in self._events],
        }

    @classmethod
    def from_export(cls, payload: Mapping[str, Any]) -> "RecoveryJournal":
        if payload.get("schema") != 1:
            raise ValueError("unsupported journal schema")
        journal = cls()
        for raw in payload.get("events", []):
            event = JournalEvent(
                sequence=raw["sequence"],
                action=raw["action"],
                finding_id=raw["finding_id"],
                payload=raw.get("payload", {}),
                previous_hash=raw.get("previous_hash"),
                event_hash=raw["event_hash"],
            )
            journal._events.append(event)
        journal.verify()
        if payload.get("head_hash") != journal.head_hash:
            raise ValueError("journal head_hash mismatch")
        return journal


def finding_to_payload(finding: RecoveryFinding) -> dict[str, Any]:
    return {
        "finding_id": finding.finding_id,
        "branch": finding.branch.value,
        "client_id": finding.client_id,
        "counterparty_id": finding.counterparty_id,
        "reference": finding.reference,
        "currency": finding.currency,
        "mode": finding.mode.value,
        "expected_cents": finding.expected_cents,
        "actual_cents": finding.actual_cents,
        "rule": None if finding.rule is None else asdict(finding.rule),
        "evidence": [asdict(ref) for ref in finding.evidence],
        "state": finding.state.value,
        "reason": finding.reason,
        "confidence_basis": finding.confidence_basis,
        "metadata": dict(finding.metadata),
        "proof_hash": finding.proof_hash,
    }


def finding_from_payload(payload: Mapping[str, Any]) -> RecoveryFinding:
    rule_raw = payload.get("rule")
    rule = RuleRef(**rule_raw) if rule_raw is not None else None
    finding = RecoveryFinding(
        finding_id=payload["finding_id"],
        branch=Branch(payload["branch"]),
        client_id=payload["client_id"],
        counterparty_id=payload["counterparty_id"],
        reference=payload["reference"],
        currency=payload["currency"],
        mode=RecoveryMode(payload["mode"]),
        expected_cents=payload["expected_cents"],
        actual_cents=payload["actual_cents"],
        rule=rule,
        evidence=tuple(EvidenceRef(**raw) for raw in payload["evidence"]),
        state=FindingState(payload["state"]),
        reason=payload["reason"],
        confidence_basis=payload["confidence_basis"],
        metadata=payload.get("metadata", {}),
    )
    supplied_hash = payload.get("proof_hash")
    if supplied_hash is not None and supplied_hash != finding.proof_hash:
        raise ValueError("finding proof_hash mismatch")
    return finding
