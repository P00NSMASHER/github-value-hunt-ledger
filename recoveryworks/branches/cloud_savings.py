"""Separate prospective cloud-savings reporting.

Savings estimates are not RecoveryOS recoveries. Only explicit
SAVINGS_OPPORTUNITY signals contribute to the estimated savings total.
Anomaly exposure and reconciliation drift are reported separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .cloud_signals import CloudSignal, CloudSignalType
from .cloud_savings_evidence import CloudSavingsMeasurement, SavingsEvidenceState


@dataclass(frozen=True)
class CloudSavingsReport:
    signal_count: int
    savings_opportunity_count: int
    estimated_savings_opportunity_cents: int
    anomaly_count: int
    estimated_anomaly_exposure_cents: int
    reconciliation_drift_count: int
    reconciliation_drift_cents: int
    realized_savings_cents: int
    realized_measurement_count: int
    realized_measurements: tuple[dict[str, Any], ...]
    opportunities: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_count": self.signal_count,
            "savings_opportunity_count": self.savings_opportunity_count,
            "estimated_savings_opportunity_cents": self.estimated_savings_opportunity_cents,
            "anomaly_count": self.anomaly_count,
            "estimated_anomaly_exposure_cents": self.estimated_anomaly_exposure_cents,
            "reconciliation_drift_count": self.reconciliation_drift_count,
            "reconciliation_drift_cents": self.reconciliation_drift_cents,
            "realized_savings_cents": self.realized_savings_cents,
            "realized_measurement_count": self.realized_measurement_count,
            "realized_measurements": [dict(item) for item in self.realized_measurements],
            "opportunities": [dict(item) for item in self.opportunities],
        }


def build_cloud_savings_report(
    signals: Iterable[CloudSignal],
    realized_measurements: Iterable[CloudSavingsMeasurement] = (),
) -> CloudSavingsReport:
    rows = tuple(signals)
    opportunity_total = 0
    anomaly_total = 0
    reconciliation_total = 0
    opportunities: list[dict[str, Any]] = []
    anomaly_count = 0
    reconciliation_count = 0

    for signal in rows:
        amount = signal.estimated_impact_cents or 0
        if signal.signal_type is CloudSignalType.SAVINGS_OPPORTUNITY:
            opportunity_total += amount
            opportunities.append({
                "signal_id": signal.signal_id,
                "provider": signal.provider,
                "account_id": signal.account_id,
                "service_id": signal.service_id,
                "resource_id": signal.resource_id,
                "category": signal.metadata.get("savings_category"),
                "recommendation": signal.metadata.get("recommendation"),
                "remediation_action": signal.metadata.get("remediation_action"),
                "estimated_savings_cents": amount,
                "confidence": signal.confidence,
                "source_hash": signal.source_hash,
            })
        elif signal.signal_type is CloudSignalType.ANOMALY:
            anomaly_count += 1
            anomaly_total += amount
        elif signal.signal_type is CloudSignalType.RECONCILIATION_DRIFT:
            reconciliation_count += 1
            reconciliation_total += amount

    measurement_index: dict[str, CloudSavingsMeasurement] = {}
    for measurement in realized_measurements:
        previous = measurement_index.get(measurement.measurement_id)
        if previous is not None and previous.proof_hash != measurement.proof_hash:
            raise ValueError("conflicting realized-savings measurement id")
        measurement_index[measurement.measurement_id] = measurement
    verified_measurements = [
        measurement
        for measurement in measurement_index.values()
        if measurement.state is SavingsEvidenceState.VERIFIED
    ]
    realized_rows = tuple(
        measurement.as_dict()
        for measurement in sorted(
            verified_measurements, key=lambda item: item.measurement_id
        )
    )
    realized_total = sum(
        measurement.realized_savings_cents
        for measurement in verified_measurements
    )

    opportunities.sort(
        key=lambda item: (
            -item["estimated_savings_cents"],
            item["provider"],
            item["service_id"],
            item["signal_id"],
        )
    )
    return CloudSavingsReport(
        signal_count=len(rows),
        savings_opportunity_count=len(opportunities),
        estimated_savings_opportunity_cents=opportunity_total,
        anomaly_count=anomaly_count,
        estimated_anomaly_exposure_cents=anomaly_total,
        reconciliation_drift_count=reconciliation_count,
        reconciliation_drift_cents=reconciliation_total,
        realized_savings_cents=realized_total,
        realized_measurement_count=len(verified_measurements),
        realized_measurements=realized_rows,
        opportunities=tuple(opportunities),
    )
