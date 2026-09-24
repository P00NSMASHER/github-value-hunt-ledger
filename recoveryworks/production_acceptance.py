"""Proof-bound production chaos/recovery acceptance results.

The fault injection itself lives in tests/rehearsals; this module freezes the
observed acceptance outcomes and refuses a passing report unless every required
scenario passed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from recoveryworks.models import canonical_hash, normalize_utc_timestamp


_REQUIRED_SCENARIOS = (
    "STALE_LEASE_RECOVERY",
    "CORRUPTED_STATE_FAIL_CLOSED",
    "ATOMIC_WRITE_FAILURE_FAIL_CLOSED",
    "TENANT_COLLISION_FAIL_CLOSED",
    "RESTORE_AFTER_CRASH",
    "ISOLATED_MULTI_PROVIDER_JOBS",
)


@dataclass(frozen=True)
class ProductionAcceptanceCheck:
    scenario: str
    passed: bool
    detail: str
    evidence_proof_hash: str | None = None

    def __post_init__(self) -> None:
        if self.scenario not in _REQUIRED_SCENARIOS:
            raise ValueError("unsupported production acceptance scenario")
        if self.passed is not True:
            raise ValueError("acceptance check artifact only represents a passing check")
        if not isinstance(self.detail, str) or not self.detail.strip():
            raise ValueError("acceptance check detail is required")

    @property
    def proof_hash(self) -> str:
        return canonical_hash({"schema": 1, **asdict(self)})


@dataclass(frozen=True)
class ProductionAcceptanceReport:
    report_id: str
    executed_at: str
    checks: tuple[ProductionAcceptanceCheck, ...]
    all_required_scenarios_passed: bool
    external_actions_performed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "executed_at",
            normalize_utc_timestamp("executed_at", self.executed_at),
        )
        checks = tuple(sorted(self.checks, key=lambda item: item.scenario))
        scenarios = tuple(item.scenario for item in checks)
        if scenarios != tuple(sorted(_REQUIRED_SCENARIOS)):
            raise ValueError("acceptance report must cover every required scenario exactly once")
        object.__setattr__(self, "checks", checks)
        if self.all_required_scenarios_passed is not True:
            raise ValueError("acceptance report requires all scenarios to pass")
        if self.external_actions_performed:
            raise ValueError("acceptance suite cannot perform external actions")
        expected = "recoveryworks-production-acceptance:" + canonical_hash(
            self._identity()
        )
        if self.report_id != expected:
            raise ValueError("report_id does not bind production acceptance report")

    def _identity(self) -> dict[str, Any]:
        return {
            "schema": 1,
            "executed_at": self.executed_at,
            "check_hashes": [item.proof_hash for item in self.checks],
            "all_required_scenarios_passed": True,
            "external_actions_performed": False,
        }

    @property
    def proof_hash(self) -> str:
        return canonical_hash(self._identity())

    def as_dict(self) -> dict[str, Any]:
        return {
            **self._identity(),
            "checks": [
                {**asdict(item), "proof_hash": item.proof_hash}
                for item in self.checks
            ],
            "report_id": self.report_id,
            "proof_hash": self.proof_hash,
            "state": "PRODUCTION_ACCEPTANCE_PASSED",
        }


def build_production_acceptance_report(
    checks: tuple[ProductionAcceptanceCheck, ...],
    *,
    executed_at: str,
) -> ProductionAcceptanceReport:
    normalized = normalize_utc_timestamp("executed_at", executed_at)
    sorted_checks = tuple(sorted(checks, key=lambda item: item.scenario))
    identity = {
        "schema": 1,
        "executed_at": normalized,
        "check_hashes": [item.proof_hash for item in sorted_checks],
        "all_required_scenarios_passed": True,
        "external_actions_performed": False,
    }
    return ProductionAcceptanceReport(
        report_id="recoveryworks-production-acceptance:" + canonical_hash(identity),
        executed_at=normalized,
        checks=sorted_checks,
        all_required_scenarios_passed=True,
        external_actions_performed=False,
    )
