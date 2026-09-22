"""Deterministic Recovery Scan 360 client reporting.

This is the client-facing aggregation layer over the proof-bound Recovery Ledger.
It reports stage-specific dollars without promoting REVIEW findings into validated
or claimable recovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ledger import RecoveryLedger
from .models import CaseState, FindingState


@dataclass(frozen=True)
class RecoveryScan360Report:
    client_id: str
    currency: str
    totals: dict[str, int]
    branches: dict[str, dict[str, int]]
    case_states: dict[str, dict[str, int]]
    review_backlog: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "currency": self.currency,
            "totals": dict(self.totals),
            "branches": {k: dict(v) for k, v in self.branches.items()},
            "case_states": {k: dict(v) for k, v in self.case_states.items()},
            "review_backlog": [dict(item) for item in self.review_backlog],
        }


def build_scan360_report(ledger: RecoveryLedger, client_id: str) -> RecoveryScan360Report:
    if not isinstance(client_id, str) or not client_id.strip():
        raise ValueError("client_id is required")
    client_id = client_id.strip()

    records = [r for r in ledger.records() if r.finding.client_id == client_id]
    currencies = {r.finding.currency for r in records}
    if len(currencies) > 1:
        raise ValueError("scan360 report requires a single currency per client report")
    currency = next(iter(currencies), "USD")

    totals = {
        "cases": 0,
        "potential_cents": 0,
        "review_cents": 0,
        "validated_cents": 0,
        "authorized_cents": 0,
        "claimed_cents": 0,
        "recovered_cents": 0,
        "fee_cents": 0,
        "rejected_cents": 0,
    }
    branches: dict[str, dict[str, int]] = {}
    case_states: dict[str, dict[str, int]] = {}
    backlog: list[dict[str, Any]] = []

    for record in records:
        finding = record.finding
        amount = finding.potential_recovery_cents
        totals["cases"] += 1
        totals["potential_cents"] += amount

        if finding.state is FindingState.REVIEW:
            totals["review_cents"] += amount
        elif finding.state is FindingState.VALIDATED:
            totals["validated_cents"] += amount

        if record.case_state is CaseState.AUTHORIZED:
            totals["authorized_cents"] += amount
        elif record.case_state is CaseState.CLAIMED:
            totals["claimed_cents"] += amount
        elif record.case_state is CaseState.RECOVERED:
            totals["recovered_cents"] += record.recovered_cents
            totals["fee_cents"] += record.fee_cents
        elif record.case_state is CaseState.REJECTED:
            totals["rejected_cents"] += amount

        branch = branches.setdefault(finding.branch.value, {
            "cases": 0,
            "potential_cents": 0,
            "validated_cents": 0,
            "recovered_cents": 0,
            "fee_cents": 0,
        })
        branch["cases"] += 1
        branch["potential_cents"] += amount
        if finding.state is FindingState.VALIDATED:
            branch["validated_cents"] += amount
        branch["recovered_cents"] += record.recovered_cents
        branch["fee_cents"] += record.fee_cents

        state = case_states.setdefault(record.case_state.value, {
            "cases": 0,
            "potential_cents": 0,
            "recovered_cents": 0,
        })
        state["cases"] += 1
        state["potential_cents"] += amount
        state["recovered_cents"] += record.recovered_cents

        if record.case_state in {CaseState.REVIEW, CaseState.VALIDATED}:
            backlog.append({
                "finding_id": finding.finding_id,
                "branch": finding.branch.value,
                "counterparty_id": finding.counterparty_id,
                "reference": finding.reference,
                "state": record.case_state.value,
                "potential_recovery_cents": amount,
                "rule_verified": bool(
                    finding.rule is not None and finding.rule.verified_controlling
                ),
                "evidence_verified": all(ref.verified for ref in finding.evidence),
            })

    backlog.sort(
        key=lambda item: (
            -item["potential_recovery_cents"],
            item["branch"],
            item["finding_id"],
        )
    )
    branches = dict(sorted(branches.items()))
    case_states = dict(sorted(case_states.items()))

    return RecoveryScan360Report(
        client_id=client_id,
        currency=currency,
        totals=totals,
        branches=branches,
        case_states=case_states,
        review_backlog=tuple(backlog),
    )
