"""Shared helpers for date-scoped, proof-preserving branch adapters."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Mapping

from recoveryworks.engine import RecoveryObservation
from recoveryworks.models import Branch, EvidenceRef, RuleRef


def _date(value: str, field: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO YYYY-MM-DD") from exc


def effective_rule(rule: RuleRef | None, occurred_on: str) -> RuleRef | None:
    """Preserve the rule but revoke controlling status when its date window misses.

    A mismatched rule remains attached so a reviewer can see what was proposed,
    but RecoveryEngine will keep the resulting finding in REVIEW.
    """
    occurred = _date(occurred_on, "occurred_on")
    if rule is None:
        return None

    start = _date(rule.effective_from, "rule.effective_from")
    end = _date(rule.effective_to, "rule.effective_to") if rule.effective_to else None
    if end is not None and end < start:
        raise ValueError("rule effective_to cannot precede effective_from")

    applies = occurred >= start and (end is None or occurred <= end)
    if applies or not rule.verified_controlling:
        return rule

    metadata = dict(rule.metadata)
    metadata["authority_date_mismatch"] = {
        "occurred_on": occurred_on,
        "effective_from": rule.effective_from,
        "effective_to": rule.effective_to,
    }
    return replace(rule, verified_controlling=False, metadata=metadata)


def observation(
    *,
    branch: Branch,
    client_id: str,
    counterparty_id: str,
    reference: str,
    currency: str,
    expected_cents: int,
    actual_cents: int,
    occurred_on: str,
    rule: RuleRef | None,
    evidence: tuple[EvidenceRef, ...],
    reason: str,
    confidence_basis: str,
    metadata: Mapping[str, Any] | None = None,
) -> RecoveryObservation:
    merged = dict(metadata or {})
    merged.setdefault("occurred_on", occurred_on)
    merged.setdefault("adapter", f"recoveryworks.branches.{branch.value}")
    return RecoveryObservation(
        branch=branch,
        client_id=client_id,
        counterparty_id=counterparty_id,
        reference=reference,
        currency=currency,
        expected_cents=expected_cents,
        actual_cents=actual_cents,
        rule=effective_rule(rule, occurred_on),
        evidence=evidence,
        reason=reason,
        confidence_basis=confidence_basis,
        metadata=merged,
    )
