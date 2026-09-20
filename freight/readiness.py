"""Machine-scored Data Readiness / Authority Diagnostic for Freight Recovery.

The numeric score is for planning. Hard blockers always dominate the score.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

class ReadinessStatus(str, Enum):
    BLOCKED = "BLOCKED"
    CONDITIONAL = "CONDITIONAL"
    READY = "READY"

@dataclass(frozen=True)
class PilotReadinessInput:
    authorization_documented: bool
    read_only_access: bool
    population_reproducible: bool
    incumbent_output_sealable: bool
    settlement_observable: bool
    material_authority_reconstructable: bool
    customer_identity_stable: bool
    carrier_identity_stable: bool
    retention_defined: bool
    deletion_defined: bool
    invoice_source_coverage: float
    authority_source_coverage: float
    shipment_evidence_coverage: float

@dataclass(frozen=True)
class ReadinessAssessment:
    status: ReadinessStatus
    score: int
    blockers: tuple[str, ...]
    conditions: tuple[str, ...]
    recommended_offer: str

HARD_BLOCKERS = (
    ("authorization_documented", "buyer_authorization_missing"),
    ("read_only_access", "read_only_access_not_established"),
    ("population_reproducible", "population_cannot_be_frozen_reproducibly"),
    ("incumbent_output_sealable", "incumbent_output_cannot_remain_sealed"),
    ("settlement_observable", "later_settlement_cannot_be_observed"),
    ("material_authority_reconstructable", "controlling_authority_not_reconstructable"),
    ("customer_identity_stable", "customer_identity_unresolved"),
    ("carrier_identity_stable", "carrier_identity_unresolved"),
    ("retention_defined", "retention_policy_undefined"),
    ("deletion_defined", "deletion_policy_undefined"),
)

COVERAGE_THRESHOLDS = (
    ("invoice_source_coverage", 0.95, "invoice_source_coverage_below_95pct"),
    ("authority_source_coverage", 0.90, "authority_source_coverage_below_90pct"),
    ("shipment_evidence_coverage", 0.80, "shipment_evidence_coverage_below_80pct"),
)

def _validate_ratio(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or value < 0 or value > 1:
        raise ValueError(f"{name} must be between 0 and 1")

def assess_readiness(inp: PilotReadinessInput) -> ReadinessAssessment:
    for name, _, _ in COVERAGE_THRESHOLDS:
        _validate_ratio(name, getattr(inp, name))

    blockers = tuple(
        reason for field, reason in HARD_BLOCKERS if not getattr(inp, field)
    )

    binary_score = sum(1 for field, _ in HARD_BLOCKERS if getattr(inp, field))
    # 65 points for hard operational prerequisites, 35 for source coverage.
    score = round(
        binary_score / len(HARD_BLOCKERS) * 65
        + inp.invoice_source_coverage * 12
        + inp.authority_source_coverage * 15
        + inp.shipment_evidence_coverage * 8
    )
    score = max(0, min(score, 100))

    conditions = tuple(
        reason
        for field, threshold, reason in COVERAGE_THRESHOLDS
        if getattr(inp, field) < threshold
    )

    if blockers:
        return ReadinessAssessment(
            ReadinessStatus.BLOCKED,
            score,
            blockers,
            conditions,
            "DATA_READINESS_DIAGNOSTIC",
        )
    if conditions:
        return ReadinessAssessment(
            ReadinessStatus.CONDITIONAL,
            score,
            blockers,
            conditions,
            "DATA_READINESS_DIAGNOSTIC",
        )
    return ReadinessAssessment(
        ReadinessStatus.READY,
        score,
        (),
        (),
        "BLIND_FREIGHT_AUDIT_ACCEPTANCE_TEST",
    )

def from_dict(data: dict) -> PilotReadinessInput:
    fields = PilotReadinessInput.__dataclass_fields__
    missing = [name for name in fields if name not in data]
    if missing:
        raise ValueError("missing readiness fields: " + ", ".join(missing))
    extra = sorted(set(data) - set(fields))
    if extra:
        raise ValueError("unknown readiness fields: " + ", ".join(extra))
    return PilotReadinessInput(**data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    args = parser.parse_args()
    data = json.loads(Path(args.input_json).read_text())
    assessment = assess_readiness(from_dict(data))
    payload = asdict(assessment)
    payload["status"] = assessment.status.value
    print(json.dumps(payload, indent=2))
    raise SystemExit(0)
