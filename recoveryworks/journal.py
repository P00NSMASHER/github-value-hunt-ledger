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
    SettlementEvidence,
    canonical_hash,
    freeze_json,
    normalize_utc_timestamp,
    thaw_json,
)


@dataclass(frozen=True)
class JournalEvent:
    sequence: int
    occurred_at: str
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
        occurred_at: str,
        action: str,
        finding_id: str,
        payload: Mapping[str, Any],
        previous_hash: str | None,
    ) -> "JournalEvent":
        if type(sequence) is not int or sequence < 1:
            raise ValueError("sequence must be positive")
        if not isinstance(action, str) or not isinstance(finding_id, str):
            raise ValueError("action and finding_id must be strings")
        if not action.strip() or not finding_id.strip():
            raise ValueError("action and finding_id are required")
        if any(ord(character) < 32 for character in action.strip() + finding_id.strip()):
            raise ValueError("action and finding_id cannot contain control characters")
        if not isinstance(payload, Mapping):
            raise ValueError("journal payload must be an object")
        normalized_time = normalize_utc_timestamp("occurred_at", occurred_at)
        frozen_payload = freeze_json(payload, name="journal payload")
        body = {
            "schema": 2,
            "sequence": sequence,
            "occurred_at": normalized_time,
            "action": action.strip(),
            "finding_id": finding_id.strip(),
            "payload": frozen_payload,
            "previous_hash": previous_hash,
        }
        return cls(
            sequence=sequence,
            occurred_at=normalized_time,
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
            occurred_at=self.occurred_at,
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

    def append(
        self,
        action: str,
        finding_id: str,
        payload: Mapping[str, Any],
        *,
        occurred_at: str,
    ) -> JournalEvent:
        event = JournalEvent.build(
            sequence=len(self._events) + 1,
            occurred_at=occurred_at,
            action=action,
            finding_id=finding_id,
            payload=payload,
            previous_hash=self.head_hash,
        )
        if self._events and event.occurred_at < self._events[-1].occurred_at:
            raise ValueError("journal occurred_at values must be nondecreasing")
        self._events.append(event)
        return event

    def events(self) -> tuple[JournalEvent, ...]:
        return tuple(self._events)

    def verify(self) -> None:
        previous = None
        previous_time = None
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.sequence != expected_sequence:
                raise ValueError("journal sequence gap")
            event.verify(previous)
            if previous_time is not None and event.occurred_at < previous_time:
                raise ValueError("journal occurred_at values must be nondecreasing")
            previous = event.event_hash
            previous_time = event.occurred_at

    def export(self) -> dict[str, Any]:
        self.verify()
        return {
            "schema": 2,
            "head_hash": self.head_hash,
            "events": [thaw_json(asdict(event)) for event in self._events],
        }

    @classmethod
    def from_export(cls, payload: Mapping[str, Any]) -> "RecoveryJournal":
        if payload.get("schema") != 2:
            raise ValueError("unsupported journal schema")
        journal = cls()
        for raw in payload.get("events", []):
            event = JournalEvent.build(
                sequence=raw["sequence"],
                occurred_at=raw["occurred_at"],
                action=raw["action"],
                finding_id=raw["finding_id"],
                payload=raw.get("payload", {}),
                previous_hash=raw.get("previous_hash"),
            )
            if event.event_hash != raw["event_hash"]:
                raise ValueError("journal event hash mismatch")
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
        "rule": None if finding.rule is None else thaw_json(asdict(finding.rule)),
        "evidence": [thaw_json(asdict(ref)) for ref in finding.evidence],
        "state": finding.state.value,
        "reason": finding.reason,
        "confidence_basis": finding.confidence_basis,
        "metadata": thaw_json(finding.metadata),
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


def settlement_to_payload(settlement: SettlementEvidence) -> dict[str, Any]:
    return {**thaw_json(asdict(settlement)), "proof_hash": settlement.proof_hash}


def settlement_from_payload(payload: Mapping[str, Any]) -> SettlementEvidence:
    settlement = SettlementEvidence(
        settlement_id=payload["settlement_id"],
        finding_id=payload["finding_id"],
        source_hash=payload["source_hash"],
        source_locator=payload["source_locator"],
        observed_at=payload["observed_at"],
        recovered_cents=payload["recovered_cents"],
        currency=payload["currency"],
        verified=payload["verified"],
        metadata=payload.get("metadata", {}),
    )
    supplied_hash = payload.get("proof_hash")
    if supplied_hash is not None and supplied_hash != settlement.proof_hash:
        raise ValueError("settlement proof_hash mismatch")
    return settlement
