"""Isolated RecoveryOS adapter for the vendored freight-audit domain engine.

The deterministic rule engine is pinned to aiparallel0/freight-audit commit
e7869162cf9cb23f6d520a0cd71f87cf973d8c28. This module deliberately stops at
raw freight-domain findings. It does not create RecoveryObservation or
RecoveryFinding objects yet; Step 2 will bind each finding to RecoveryOS
RuleRef/EvidenceRef proof without allowing overlapping audit rules to double
count recoverable dollars.
"""
from __future__ import annotations

from dataclasses import dataclass

from .freight_audit_vendor import (
    CarrierInvoice,
    EngineConfig,
    Finding,
    FindingType,
    LineItem,
    MatchEngine,
    MatchResult,
    ProofOfDelivery,
    RateConfirmation,
    Severity,
    is_same_load,
    normalize_category,
)

UPSTREAM_REPOSITORY = "aiparallel0/freight-audit"
UPSTREAM_COMMIT = "e7869162cf9cb23f6d520a0cd71f87cf973d8c28"
ENGINE_ID = f"{UPSTREAM_REPOSITORY}:src/freight_audit/match.py"


@dataclass(frozen=True)
class FreightAuditDomainResult:
    match: MatchResult
    engine_id: str = ENGINE_ID
    engine_commit: str = UPSTREAM_COMMIT

    @property
    def findings(self) -> tuple[Finding, ...]:
        return tuple(self.match.findings)

    @property
    def load_id(self) -> str:
        return self.match.load_id

    @property
    def severity(self) -> Severity:
        return self.match.severity

    @property
    def net_money_impact_cents(self) -> int:
        return self.match.net_money_impact_cents

    @property
    def auto_approvable(self) -> bool:
        return self.match.auto_approvable


class FreightAuditDomainAdapter:
    """Run the pinned deterministic freight audit without crossing the proof boundary."""

    engine_id = ENGINE_ID
    engine_commit = UPSTREAM_COMMIT

    def __init__(self, config: EngineConfig | None = None):
        self._engine = MatchEngine(config)

    def audit(
        self,
        rate_confirmation: RateConfirmation | None,
        invoice: CarrierInvoice | None,
        pod: ProofOfDelivery | None,
    ) -> FreightAuditDomainResult:
        return FreightAuditDomainResult(
            self._engine.match(rate_confirmation, invoice, pod)
        )


__all__ = [
    "CarrierInvoice",
    "ENGINE_ID",
    "EngineConfig",
    "Finding",
    "FindingType",
    "FreightAuditDomainAdapter",
    "FreightAuditDomainResult",
    "LineItem",
    "MatchResult",
    "ProofOfDelivery",
    "RateConfirmation",
    "Severity",
    "UPSTREAM_COMMIT",
    "UPSTREAM_REPOSITORY",
    "is_same_load",
    "normalize_category",
]
