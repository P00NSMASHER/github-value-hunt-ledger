"""Source-observation receipts for money-bearing RecoveryWorks inputs.

This layer preserves the distinction between an observed object, a verified
empty source/window, a partial observation, and an unavailable source. A
successful empty result is evidence; a failed or partial connector is not.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

from .models import canonical_hash


class SourceState(str, Enum):
    PRESENT = "PRESENT"
    VERIFIED_EMPTY = "VERIFIED_EMPTY"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class SourceCoverageReceipt:
    source_id: str
    object_type: str
    window: str
    state: SourceState
    source_hash: str
    locator: str
    observed_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("source_id", "object_type", "window", "source_hash", "locator", "observed_at"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.state, SourceState):
            raise ValueError("state must be a SourceState")

    @property
    def conclusive(self) -> bool:
        return self.state in {SourceState.PRESENT, SourceState.VERIFIED_EMPTY}

    @property
    def proof_hash(self) -> str:
        payload = asdict(self)
        payload["state"] = self.state.value
        return canonical_hash({"schema": 1, **payload})


def coverage_is_conclusive(receipts: tuple[SourceCoverageReceipt, ...]) -> bool:
    """Return True for legacy/no-receipt observations or wholly conclusive coverage.

    An empty tuple is deliberately backward compatible: branches must opt into
    source-coverage receipts explicitly. Once receipts are supplied, every
    supplied source/window must be conclusive.
    """
    return not receipts or all(receipt.conclusive for receipt in receipts)


def coverage_blockers(receipts: tuple[SourceCoverageReceipt, ...]) -> tuple[str, ...]:
    return tuple(
        f"{receipt.source_id}:{receipt.object_type}:{receipt.window}:{receipt.state.value}"
        for receipt in receipts
        if not receipt.conclusive
    )
