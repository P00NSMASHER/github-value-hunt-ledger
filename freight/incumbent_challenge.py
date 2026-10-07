"""Second-look incumbent challenge engine for RecoveryOS phase 1.

The engine freezes the incumbent's known universe before challenger attribution.
It never converts a candidate into recovered value. Its only money-bearing output
is a conservative net-new candidate amount that must still pass human review,
authorization, claim, and settlement.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from freight.contracts import canonical_hash

INCUMBENT_STATES = {
    "FINDING",
    "AUTOMATIC_CREDIT",
    "PREEXISTING_CREDIT",
    "OPEN_CLAIM",
    "KNOWN_DISPUTE",
}
ATTRIBUTION_STATES = {"CHALLENGER_ONLY", "INCUMBENT_KNOWN", "SUPPRESSED", "REVIEW"}
MAX_CENTS = 2**63 - 1


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    value = value.strip()
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{name} contains control characters")
    return value


def _cents(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value <= MAX_CENTS:
        raise ValueError(f"{name} must be non-negative integer cents")
    return value


def _ppm(name: str, value: int) -> int:
    if type(value) is not int or not 0 <= value <= 1_000_000:
        raise ValueError(f"{name} must be an integer in [0, 1000000]")
    return value


@dataclass(frozen=True)
class IncumbentMatter:
    matter_id: str
    economic_key: str
    state: str
    amount_cents: int
    source_hash: str

    def __post_init__(self) -> None:
        _text("matter_id", self.matter_id)
        _text("economic_key", self.economic_key)
        if self.state not in INCUMBENT_STATES:
            raise ValueError("unsupported incumbent state")
        _cents("amount_cents", self.amount_cents)
        _text("source_hash", self.source_hash)


@dataclass(frozen=True)
class FrozenIncumbentSnapshot:
    buyer_id: str
    business_unit: str
    population_hash: str
    source_hash: str
    matters: tuple[IncumbentMatter, ...]
    snapshot_hash: str


@dataclass(frozen=True)
class ChallengeCandidate:
    candidate_id: str
    economic_key: str
    record_hash: str
    category: str
    billed_cents: int
    expected_cents: int
    confidence_ppm: int
    evidence_hashes: tuple[str, ...] = ()
    blocker_codes: tuple[str, ...] = ()

    @property
    def variance_cents(self) -> int:
        return max(self.billed_cents - self.expected_cents, 0)

    def __post_init__(self) -> None:
        _text("candidate_id", self.candidate_id)
        _text("economic_key", self.economic_key)
        _text("record_hash", self.record_hash)
        _text("category", self.category)
        _cents("billed_cents", self.billed_cents)
        _cents("expected_cents", self.expected_cents)
        _ppm("confidence_ppm", self.confidence_ppm)
        for value in self.evidence_hashes:
            _text("evidence_hash", value)
        for value in self.blocker_codes:
            _text("blocker_code", value)


@dataclass(frozen=True)
class ChallengeDisposition:
    candidate_id: str
    economic_key: str
    attribution_state: str
    candidate_variance_cents: int
    net_new_candidate_cents: int
    matched_incumbent_matter_ids: tuple[str, ...]
    blocker_codes: tuple[str, ...]
    disposition_hash: str


@dataclass(frozen=True)
class ChallengeBatch:
    incumbent_snapshot_hash: str
    dispositions: tuple[ChallengeDisposition, ...]
    challenger_only_cents: int
    incumbent_known_cents: int
    review_cents: int
    suppressed_cents: int
    batch_hash: str


def freeze_incumbent_snapshot(
    *,
    buyer_id: str,
    business_unit: str,
    population_hash: str,
    source_hash: str,
    matters: Iterable[IncumbentMatter],
) -> FrozenIncumbentSnapshot:
    buyer_id = _text("buyer_id", buyer_id)
    business_unit = _text("business_unit", business_unit)
    population_hash = _text("population_hash", population_hash)
    source_hash = _text("source_hash", source_hash)
    normalized = tuple(sorted(matters, key=lambda x: (x.economic_key, x.matter_id)))
    if len({m.matter_id for m in normalized}) != len(normalized):
        raise ValueError("duplicate incumbent matter_id")
    body = {
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "population_hash": population_hash,
        "source_hash": source_hash,
        "matters": [asdict(m) for m in normalized],
    }
    return FrozenIncumbentSnapshot(
        buyer_id=buyer_id,
        business_unit=business_unit,
        population_hash=population_hash,
        source_hash=source_hash,
        matters=normalized,
        snapshot_hash=canonical_hash(body),
    )


def challenge_incumbent(
    snapshot: FrozenIncumbentSnapshot,
    candidates: Iterable[ChallengeCandidate],
) -> ChallengeBatch:
    normalized = tuple(sorted(candidates, key=lambda x: x.candidate_id))
    if len({x.candidate_id for x in normalized}) != len(normalized):
        raise ValueError("duplicate candidate_id")

    incumbent_by_key: dict[str, list[IncumbentMatter]] = {}
    for matter in snapshot.matters:
        incumbent_by_key.setdefault(matter.economic_key, []).append(matter)

    candidate_counts: dict[str, int] = {}
    for candidate in normalized:
        candidate_counts[candidate.economic_key] = candidate_counts.get(candidate.economic_key, 0) + 1

    dispositions: list[ChallengeDisposition] = []
    for candidate in normalized:
        blockers = set(candidate.blocker_codes)
        matched = tuple(sorted(
            matter.matter_id for matter in incumbent_by_key.get(candidate.economic_key, [])
        ))
        variance = candidate.variance_cents

        if variance == 0:
            state = "SUPPRESSED"
            blockers.add("NO_POSITIVE_VARIANCE")
        elif candidate_counts[candidate.economic_key] > 1:
            state = "REVIEW"
            blockers.add("DUPLICATE_CHALLENGER_ECONOMIC_KEY")
        elif blockers:
            state = "REVIEW"
        elif matched:
            state = "INCUMBENT_KNOWN"
        else:
            state = "CHALLENGER_ONLY"

        net_new = variance if state == "CHALLENGER_ONLY" else 0
        blocker_tuple = tuple(sorted(blockers))
        body = {
            "schema": 1,
            "snapshot_hash": snapshot.snapshot_hash,
            "candidate_id": candidate.candidate_id,
            "economic_key": candidate.economic_key,
            "record_hash": candidate.record_hash,
            "category": candidate.category,
            "billed_cents": candidate.billed_cents,
            "expected_cents": candidate.expected_cents,
            "confidence_ppm": candidate.confidence_ppm,
            "evidence_hashes": candidate.evidence_hashes,
            "attribution_state": state,
            "candidate_variance_cents": variance,
            "net_new_candidate_cents": net_new,
            "matched_incumbent_matter_ids": matched,
            "blocker_codes": blocker_tuple,
        }
        dispositions.append(ChallengeDisposition(
            candidate_id=candidate.candidate_id,
            economic_key=candidate.economic_key,
            attribution_state=state,
            candidate_variance_cents=variance,
            net_new_candidate_cents=net_new,
            matched_incumbent_matter_ids=matched,
            blocker_codes=blocker_tuple,
            disposition_hash=canonical_hash(body),
        ))

    out = tuple(dispositions)
    sums = {state: 0 for state in ATTRIBUTION_STATES}
    for item in out:
        sums[item.attribution_state] += item.candidate_variance_cents
    batch_body = {
        "schema": 1,
        "incumbent_snapshot_hash": snapshot.snapshot_hash,
        "disposition_hashes": [item.disposition_hash for item in out],
        "challenger_only_cents": sums["CHALLENGER_ONLY"],
        "incumbent_known_cents": sums["INCUMBENT_KNOWN"],
        "review_cents": sums["REVIEW"],
        "suppressed_cents": sums["SUPPRESSED"],
    }
    return ChallengeBatch(
        incumbent_snapshot_hash=snapshot.snapshot_hash,
        dispositions=out,
        challenger_only_cents=sums["CHALLENGER_ONLY"],
        incumbent_known_cents=sums["INCUMBENT_KNOWN"],
        review_cents=sums["REVIEW"],
        suppressed_cents=sums["SUPPRESSED"],
        batch_hash=canonical_hash(batch_body),
    )
