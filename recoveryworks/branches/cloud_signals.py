"""Non-money cloud-cost signals.

CloudSignal is intentionally incapable of becoming a RecoveryObservation.
Signals may contain estimates, anomaly scores, forecast drift, waste, or other
investigative context, but they never represent controlling commercial
authority or validated recoverable dollars.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping

from recoveryworks.models import canonical_hash, freeze_json, normalize_sha256, normalize_utc_timestamp


class CloudSignalType(str, Enum):
    ANOMALY = "ANOMALY"
    RECONCILIATION_DRIFT = "RECONCILIATION_DRIFT"
    SAVINGS_OPPORTUNITY = "SAVINGS_OPPORTUNITY"


@dataclass(frozen=True)
class CloudSignal:
    signal_id: str
    signal_type: CloudSignalType
    provider: str
    account_id: str
    service_id: str
    detected_at: str
    detection_method: str
    source_hash: str
    source_locator: str
    severity: str | None = None
    resource_id: str | None = None
    region: str | None = None
    estimated_impact_cents: int | None = None
    confidence: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("signal_id","provider","account_id","service_id","detection_method","source_locator"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.signal_type, CloudSignalType):
            raise ValueError("signal_type must be a CloudSignalType")
        object.__setattr__(self, "detected_at", normalize_utc_timestamp("detected_at", self.detected_at))
        object.__setattr__(self, "source_hash", normalize_sha256("source_hash", self.source_hash))
        for name in ("severity","resource_id","region"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"{name} must be non-empty when supplied")
                object.__setattr__(self, name, value.strip())
        if self.estimated_impact_cents is not None:
            if type(self.estimated_impact_cents) is not int or self.estimated_impact_cents < 0:
                raise ValueError("estimated_impact_cents must be a non-negative integer")
        if self.confidence is not None:
            try:
                confidence = Decimal(str(self.confidence))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError("confidence must be numeric") from exc
            if confidence < 0 or confidence > 1:
                raise ValueError("confidence must be between 0 and 1")
            object.__setattr__(self, "confidence", str(confidence))
        object.__setattr__(self, "metadata", freeze_json(self.metadata, name="metadata"))

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema":1,
            "signal_id":self.signal_id,
            "signal_type":self.signal_type.value,
            "provider":self.provider,
            "account_id":self.account_id,
            "service_id":self.service_id,
            "detected_at":self.detected_at,
            "detection_method":self.detection_method,
            "source_hash":self.source_hash,
            "source_locator":self.source_locator,
            "severity":self.severity,
            "resource_id":self.resource_id,
            "region":self.region,
            "estimated_impact_cents":self.estimated_impact_cents,
            "confidence":self.confidence,
            "metadata":dict(self.metadata),
        })

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["signal_type"] = self.signal_type.value
        return value
