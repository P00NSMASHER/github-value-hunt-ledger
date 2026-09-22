"""Durable, tamper-evident RecoveryLedger snapshots.

Snapshots are local artifacts. They preserve the exact finding proofs, lifecycle
records, and hash-linked audit events needed to resume RecoveryOS without
recomputing or silently mutating historical dollars.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .ledger import LedgerEvent, LedgerRecord, RecoveryLedger
from .models import (
    Branch,
    CaseState,
    EvidenceRef,
    FindingState,
    RecoveryFinding,
    RecoveryMode,
    RuleRef,
    canonical_hash,
)


def _rule_to_dict(rule: RuleRef | None) -> dict[str, Any] | None:
    if rule is None:
        return None
    return {**asdict(rule), "proof_hash": rule.proof_hash}


def _evidence_to_dict(ref: EvidenceRef) -> dict[str, Any]:
    return {**asdict(ref), "proof_hash": ref.proof_hash}


def _finding_to_dict(finding: RecoveryFinding) -> dict[str, Any]:
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
        "rule": _rule_to_dict(finding.rule),
        "evidence": [_evidence_to_dict(ref) for ref in finding.evidence],
        "state": finding.state.value,
        "reason": finding.reason,
        "confidence_basis": finding.confidence_basis,
        "metadata": dict(finding.metadata),
        "proof_hash": finding.proof_hash,
    }


def _record_to_dict(record: LedgerRecord) -> dict[str, Any]:
    return {
        "finding": _finding_to_dict(record.finding),
        "case_state": record.case_state.value,
        "reviewer_approved": record.reviewer_approved,
        "reviewer_id": record.reviewer_id,
        "review_note": record.review_note,
        "authorization_id": record.authorization_id,
        "claim_evidence": (
            _evidence_to_dict(record.claim_evidence)
            if record.claim_evidence is not None else None
        ),
        "recovery_evidence": (
            _evidence_to_dict(record.recovery_evidence)
            if record.recovery_evidence is not None else None
        ),
        "settlement_total_cents": record.settlement_total_cents,
        "recovered_cents": record.recovered_cents,
        "fee_cents": record.fee_cents,
        "updated_at": record.updated_at,
        "record_hash": record.record_hash,
    }


def _event_to_dict(event: LedgerEvent) -> dict[str, Any]:
    return {
        "sequence": event.sequence,
        "finding_id": event.finding_id,
        "action": event.action,
        "prior_state": event.prior_state,
        "new_state": event.new_state,
        "actor_id": event.actor_id,
        "note": event.note,
        "at": event.at,
        "previous_event_hash": event.previous_event_hash,
        "metadata": dict(event.metadata),
        "event_hash": event.event_hash,
    }


def _key_bytes(integrity_key: str | bytes) -> bytes:
    if isinstance(integrity_key, bytes):
        key = integrity_key
    elif isinstance(integrity_key, str):
        key = integrity_key.encode("utf-8")
    else:
        raise ValueError("integrity_key must be str or bytes")
    if not key:
        raise ValueError("integrity_key cannot be empty")
    return key


def _sign(export_hash: str, integrity_key: str | bytes) -> str:
    return hmac.new(
        _key_bytes(integrity_key),
        export_hash.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def export_ledger(
    ledger: RecoveryLedger,
    integrity_key: str | bytes | None = None,
) -> dict[str, Any]:
    core = {
        "schema": 1,
        "records": [_record_to_dict(record) for record in ledger.records()],
        "events": [_event_to_dict(event) for event in ledger.events()],
        "audit_head": ledger.audit_head,
        "ledger_snapshot_hash": ledger.snapshot_hash,
    }
    export_hash = canonical_hash(core)
    payload = {**core, "export_hash": export_hash}
    if integrity_key is not None:
        payload["signature_alg"] = "HMAC-SHA256"
        payload["signature"] = _sign(export_hash, integrity_key)
    return payload


def _as_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _load_rule(value: Any) -> RuleRef | None:
    if value is None:
        return None
    item = _as_mapping(value, "rule")
    rule = RuleRef(
        rule_id=item["rule_id"],
        source_hash=item["source_hash"],
        effective_from=item["effective_from"],
        effective_to=item.get("effective_to"),
        verified_controlling=item["verified_controlling"],
        source_locator=item["source_locator"],
        jurisdiction=item.get("jurisdiction"),
        metadata=item.get("metadata", {}),
    )
    if rule.proof_hash != item.get("proof_hash"):
        raise ValueError("rule proof hash mismatch")
    return rule


def _load_evidence(value: Any) -> EvidenceRef:
    item = _as_mapping(value, "evidence")
    ref = EvidenceRef(
        evidence_id=item["evidence_id"],
        source_hash=item["source_hash"],
        locator=item["locator"],
        kind=item["kind"],
        verified=item["verified"],
        metadata=item.get("metadata", {}),
    )
    if ref.proof_hash != item.get("proof_hash"):
        raise ValueError("evidence proof hash mismatch")
    return ref


def _load_finding(value: Any) -> RecoveryFinding:
    item = _as_mapping(value, "finding")
    evidence_raw = item.get("evidence")
    if not isinstance(evidence_raw, list):
        raise ValueError("finding evidence must be a list")
    finding = RecoveryFinding(
        finding_id=item["finding_id"],
        branch=Branch(item["branch"]),
        client_id=item["client_id"],
        counterparty_id=item["counterparty_id"],
        reference=item["reference"],
        currency=item["currency"],
        mode=RecoveryMode(item["mode"]),
        expected_cents=item["expected_cents"],
        actual_cents=item["actual_cents"],
        rule=_load_rule(item.get("rule")),
        evidence=tuple(_load_evidence(raw) for raw in evidence_raw),
        state=FindingState(item["state"]),
        reason=item["reason"],
        confidence_basis=item["confidence_basis"],
        metadata=item.get("metadata", {}),
    )
    if finding.proof_hash != item.get("proof_hash"):
        raise ValueError("finding proof hash mismatch")
    return finding


def _load_record(value: Any) -> LedgerRecord:
    item = _as_mapping(value, "record")
    record = LedgerRecord(
        finding=_load_finding(item["finding"]),
        case_state=CaseState(item["case_state"]),
        reviewer_approved=item.get("reviewer_approved", False),
        reviewer_id=item.get("reviewer_id"),
        review_note=item.get("review_note"),
        authorization_id=item.get("authorization_id"),
        claim_evidence=(
            _load_evidence(item["claim_evidence"])
            if item.get("claim_evidence") is not None else None
        ),
        recovery_evidence=(
            _load_evidence(item["recovery_evidence"])
            if item.get("recovery_evidence") is not None else None
        ),
        settlement_total_cents=item.get("settlement_total_cents"),
        recovered_cents=item.get("recovered_cents", 0),
        fee_cents=item.get("fee_cents", 0),
        updated_at=item.get("updated_at"),
    )
    if record.record_hash != item.get("record_hash"):
        raise ValueError("ledger record hash mismatch")
    return record


def _load_event(value: Any) -> LedgerEvent:
    item = _as_mapping(value, "event")
    event = LedgerEvent(
        sequence=item["sequence"],
        finding_id=item["finding_id"],
        action=item["action"],
        prior_state=item.get("prior_state"),
        new_state=item["new_state"],
        actor_id=item.get("actor_id"),
        note=item.get("note"),
        at=item["at"],
        previous_event_hash=item.get("previous_event_hash"),
        metadata=item.get("metadata", {}),
    )
    if event.event_hash != item.get("event_hash"):
        raise ValueError("ledger event hash mismatch")
    return event


def import_ledger(
    payload: Any,
    integrity_key: str | bytes | None = None,
    *,
    require_signature: bool = False,
) -> RecoveryLedger:
    root = _as_mapping(payload, "ledger snapshot")
    if root.get("schema") != 1:
        raise ValueError("unsupported ledger snapshot schema")

    signature = root.get("signature")
    signature_alg = root.get("signature_alg")
    if integrity_key is not None:
        if not signature:
            raise ValueError("signed ledger required when integrity_key is supplied")
        if signature_alg != "HMAC-SHA256":
            raise ValueError("unsupported ledger signature algorithm")
        expected_signature = _sign(str(root.get("export_hash", "")), integrity_key)
        if not hmac.compare_digest(expected_signature, str(signature)):
            raise ValueError("ledger HMAC signature mismatch")
    elif signature is not None:
        raise ValueError("signed ledger requires integrity_key for verification")
    elif require_signature:
        raise ValueError("ledger signature is required")

    core = {
        "schema": root["schema"],
        "records": root.get("records"),
        "events": root.get("events"),
        "audit_head": root.get("audit_head"),
        "ledger_snapshot_hash": root.get("ledger_snapshot_hash"),
    }
    if canonical_hash(core) != root.get("export_hash"):
        raise ValueError("ledger export hash mismatch")

    records_raw = root.get("records")
    events_raw = root.get("events")
    if not isinstance(records_raw, list) or not isinstance(events_raw, list):
        raise ValueError("records and events must be lists")

    records = tuple(_load_record(item) for item in records_raw)
    events = [_load_event(item) for item in events_raw]

    ledger = RecoveryLedger()
    record_ids: set[str] = set()
    proof_hashes: set[str] = set()
    for record in records:
        finding_id = record.finding.finding_id
        proof_hash = record.finding.proof_hash
        if finding_id in record_ids or proof_hash in proof_hashes:
            raise ValueError("duplicate finding identity in ledger snapshot")
        record_ids.add(finding_id)
        proof_hashes.add(proof_hash)
        ledger._records[finding_id] = record
        ledger._proof_index[proof_hash] = finding_id
    ledger._events = events

    if not ledger.verify_event_chain():
        raise ValueError("ledger audit chain is invalid")
    if ledger.audit_head != root.get("audit_head"):
        raise ValueError("ledger audit head mismatch")
    if ledger.snapshot_hash != root.get("ledger_snapshot_hash"):
        raise ValueError("ledger snapshot hash mismatch")

    events_by_finding: dict[str, list[LedgerEvent]] = {}
    for event in events:
        if event.finding_id not in record_ids:
            raise ValueError("audit event references unknown finding")
        events_by_finding.setdefault(event.finding_id, []).append(event)

    for record in records:
        case_events = events_by_finding.get(record.finding.finding_id, [])
        if not case_events or case_events[0].action != "ADDED":
            raise ValueError("each ledger record requires an ADDED event")
        if case_events[-1].new_state != record.case_state.value:
            raise ValueError("ledger record state does not match final audit event")

    return ledger


def save_ledger(
    path: str | Path,
    ledger: RecoveryLedger,
    integrity_key: str | bytes | None = None,
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(destination.name + ".tmp")
    rendered = json.dumps(
        export_ledger(ledger, integrity_key=integrity_key),
        sort_keys=True,
        indent=2,
    ) + "\n"
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, destination)
    try:
        os.chmod(destination, 0o600)
    except OSError:
        pass
    return destination


def load_ledger(
    path: str | Path,
    integrity_key: str | bytes | None = None,
    *,
    require_signature: bool = False,
) -> RecoveryLedger:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    return import_ledger(
        payload,
        integrity_key=integrity_key,
        require_signature=require_signature,
    )
