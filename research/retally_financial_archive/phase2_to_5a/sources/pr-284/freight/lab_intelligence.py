"""Read-only, independently sourced laboratory decision and financial proof helpers.

Not a production accounting engine or external source-authentication service.
Neither a passing result nor this module closes historical audit findings.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Mapping, Sequence

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TYPES = frozenset({
    "INTAKE", "CREDIT_APPLIED", "CREDIT_REVERSED", "FEE_ACCRUED",
    "FEE_REVERSED", "FEE_COLLECTED", "FEE_REFUNDED",
})
_MONEY_FIELDS = (
    "net_recovered_cents", "net_earned_fee_cents",
    "net_collected_fee_cents", "open_fee_receivable_cents",
)


class ProofRejected(ValueError):
    """Semantic financial proof failure, safe to report without source contents."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _name(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ProofRejected("INVALID_" + field.upper())
    if any(ord(ch) < 32 for ch in value):
        raise ProofRejected("INVALID_" + field.upper())
    return value


def _cents(value: int, field: str, *, allow_zero: bool = True) -> int:
    if type(value) is not int or value < (0 if allow_zero else 1) or value > 2**63 - 1:
        raise ProofRejected("INVALID_" + field.upper())
    return value


def _digest(value: str, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ProofRejected("INVALID_" + field.upper())
    return value


def _canonical_digest(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceAuthority:
    """Caller-supplied, separately frozen authority; authenticity is NOT inferred.

    The external receipt manifest must be obtained and protected outside the
    tested lab. credit_caps bounds exact allocations by provider receipt ID.
    """

    tenant_id: str
    invoice_id: str
    currency: str
    source_sha256: str
    credit_caps: Mapping[str, int]
    fee_bps: int | None = None
    signed_terms_sha256: str | None = None

    def __post_init__(self) -> None:
        _name(self.tenant_id, "tenant_id")
        _name(self.invoice_id, "invoice_id")
        if not isinstance(self.currency, str) or re.fullmatch(r"[A-Z]{3}", self.currency) is None:
            raise ProofRejected("INVALID_CURRENCY")
        _digest(self.source_sha256, "source_sha256")
        if not isinstance(self.credit_caps, Mapping):
            raise ProofRejected("INVALID_CREDIT_CAPS")
        caps = {}
        for key, value in self.credit_caps.items():
            caps[_name(key, "receipt_reference")] = _cents(value, "credit_cap", allow_zero=False)
        object.__setattr__(self, "credit_caps", tuple(sorted(caps.items())))
        if self.fee_bps is None:
            if self.signed_terms_sha256 is not None:
                raise ProofRejected("FEE_TERMS_INCOMPLETE")
        else:
            if type(self.fee_bps) is not int or not 0 <= self.fee_bps <= 10_000:
                raise ProofRejected("INVALID_FEE_BPS")
            _digest(self.signed_terms_sha256, "signed_terms_sha256")


@dataclass(frozen=True)
class LabEvent:
    event_id: str
    sequence: int
    kind: str
    amount_cents: int
    reference: str = ""


@dataclass(frozen=True)
class LabCase:
    case_id: str
    tenant_id: str
    invoice_id: str
    issue_id: str
    currency: str
    source_sha256: str
    events: tuple[LabEvent, ...]
    reported: Mapping[str, int]


@dataclass(frozen=True)
class ProofReceipt:
    status: str
    independent_input_required: bool
    scope: str
    case_count: int
    totals: Mapping[str, int]
    receipt_sha256: str


def verify_population(authorities: Sequence[SourceAuthority], cases: Sequence[LabCase]) -> ProofReceipt:
    """Replay monetary events and compare claims to caller-held source authority.

    Deliberately independent of the labs' event hashes and database summaries.
    This is synthetic semantic consistency, NOT verified provider/bank evidence.
    """
    anchors = {}
    for authority in authorities:
        key = (authority.tenant_id, authority.invoice_id)
        if key in anchors:
            raise ProofRejected("DUPLICATE_SOURCE_AUTHORITY")
        anchors[key] = authority
    if not anchors or not cases:
        raise ProofRejected("MISSING_POPULATION")

    credit_allocated: dict[tuple[str, str, str], int] = {}
    seen_cases: set[str] = set()
    seen_issues: set[tuple[str, str, str]] = set()
    seen_events: set[tuple[str, str]] = set()
    totals = dict.fromkeys(_MONEY_FIELDS, 0)
    for case in cases:
        _name(case.case_id, "case_id")
        _name(case.issue_id, "issue_id")
        if case.case_id in seen_cases:
            raise ProofRejected("DUPLICATE_CASE")
        seen_cases.add(case.case_id)
        key = (case.tenant_id, case.invoice_id)
        authority = anchors.get(key)
        if authority is None:
            raise ProofRejected("SOURCE_OWNERSHIP_UNKNOWN")
        if (case.currency, case.source_sha256) != (authority.currency, authority.source_sha256):
            raise ProofRejected("SOURCE_BINDING_MISMATCH")
        issue_key = (*key, case.issue_id)
        if issue_key in seen_issues:
            raise ProofRejected("DUPLICATE_ECONOMIC_ISSUE")
        seen_issues.add(issue_key)
        if not case.events or case.events[0].kind != "INTAKE":
            raise ProofRejected("MISSING_INTAKE")
        caps = dict(authority.credit_caps)
        applied_by_ref: dict[str, int] = {}
        reversed_by_ref: dict[str, int] = {}
        accrued = reduced = collected = refunded = 0
        for seq, event in enumerate(case.events, start=1):
            _name(event.event_id, "event_id")
            if type(event.sequence) is not int or event.sequence != seq:
                raise ProofRejected("EVENT_SEQUENCE_INVALID")
            event_key = (case.tenant_id, event.event_id)
            if event_key in seen_events:
                raise ProofRejected("DUPLICATE_EVENT_ID")
            seen_events.add(event_key)
            if event.kind not in _TYPES:
                raise ProofRejected("EVENT_KIND_UNKNOWN")
            _cents(event.amount_cents, "event_amount", allow_zero=event.kind == "INTAKE")
            if event.kind == "INTAKE":
                if seq != 1 or event.amount_cents != 0 or event.reference:
                    raise ProofRejected("INTAKE_CANNOT_POST_MONEY")
            elif event.kind in {"CREDIT_APPLIED", "CREDIT_REVERSED"}:
                ref = _name(event.reference, "receipt_reference")
                if ref not in caps:
                    raise ProofRejected("RECEIPT_NOT_IN_INDEPENDENT_MANIFEST")
                if event.kind == "CREDIT_APPLIED":
                    pool_key = (*key, ref)
                    credit_allocated[pool_key] = credit_allocated.get(pool_key, 0) + event.amount_cents
                    if credit_allocated[pool_key] > caps[ref]:
                        raise ProofRejected("DUPLICATE_OR_EXCESS_CREDIT")
                    applied_by_ref[ref] = applied_by_ref.get(ref, 0) + event.amount_cents
                else:
                    reversed_by_ref[ref] = reversed_by_ref.get(ref, 0) + event.amount_cents
                    if reversed_by_ref[ref] > applied_by_ref.get(ref, 0):
                        raise ProofRejected("REVERSAL_WITHOUT_ORIGINAL_CREDIT")
            else:
                if event.reference:
                    raise ProofRejected("UNEXPECTED_FINANCIAL_REFERENCE")
                if authority.fee_bps is None or authority.signed_terms_sha256 is None:
                    raise ProofRejected("FEE_TERMS_NOT_AUTHORIZED")
                if event.kind == "FEE_ACCRUED":
                    accrued += event.amount_cents
                elif event.kind == "FEE_REVERSED":
                    reduced += event.amount_cents
                elif event.kind == "FEE_COLLECTED":
                    collected += event.amount_cents
                elif event.kind == "FEE_REFUNDED":
                    refunded += event.amount_cents

        net_recovered = sum(applied_by_ref.values()) - sum(reversed_by_ref.values())
        net_earned = accrued - reduced
        net_cash = collected - refunded
        max_earned = net_recovered * (authority.fee_bps or 0) // 10_000
        if not 0 <= net_earned <= max_earned:
            raise ProofRejected("FEE_NOT_SUPPORTED_BY_REALIZED_CREDIT")
        if not 0 <= net_cash <= net_earned:
            raise ProofRejected("FEE_CASH_NOT_SUPPORTED_BY_ACCRUAL")
        computed = {
            "net_recovered_cents": net_recovered,
            "net_earned_fee_cents": net_earned,
            "net_collected_fee_cents": net_cash,
            "open_fee_receivable_cents": net_earned - net_cash,
        }
        if not isinstance(case.reported, Mapping) or set(case.reported) != set(computed):
            raise ProofRejected("SUMMARY_SCHEMA_MISMATCH")
        for field, actual in computed.items():
            if type(case.reported[field]) is not int or case.reported[field] != actual:
                raise ProofRejected("SUMMARY_MISMATCH_" + field.upper())
            totals[field] += actual

    body = {"schema": 1, "scope": "SYNTHETIC_SEMANTIC_CONSISTENCY_ONLY",
            "cases": len(cases), "totals": totals,
            "source_manifest_digests": sorted(a.source_sha256 for a in anchors.values()),
            "case_ids": sorted(seen_cases)}
    return ProofReceipt("PASS_SYNTHETIC_ONLY", True, body["scope"],
                        len(cases), totals, _canonical_digest(body))


@dataclass(frozen=True)
class ExperimentCandidate:
    finding_id: str
    severity: str
    evidence: str
    affected_labs: tuple[int, ...]
    effort_hours: int
    reproduction_available: bool


def prioritize_experiments(candidates: Sequence[ExperimentCandidate]) -> list[tuple[str, int]]:
    """Transparent engineering triage heuristic, not predicted financial ROI."""
    severity_weight = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 2, "LOW": 1}
    evidence_weight = {"REPRODUCED_OFFLINE": 4, "INSPECTED": 2, "HYPOTHESIS": 0}
    ids: set[str] = set()
    ranks = []
    for item in candidates:
        _name(item.finding_id, "finding_id")
        if item.finding_id in ids:
            raise ValueError("finding IDs must be unique")
        ids.add(item.finding_id)
        if item.severity not in severity_weight or item.evidence not in evidence_weight:
            raise ValueError("unrecognized severity or evidence")
        if type(item.effort_hours) is not int or item.effort_hours < 1:
            raise ValueError("effort_hours must be positive integer")
        if type(item.reproduction_available) is not bool:
            raise ValueError("reproduction_available must be boolean")
        if not item.affected_labs or any(type(x) is not int or not 1 <= x <= 14 for x in item.affected_labs):
            raise ValueError("affected_labs must identify laboratories 1-14")
        score = (severity_weight[item.severity] * 100
                 + evidence_weight[item.evidence] * 20
                 + 30 * item.reproduction_available
                 + 5 * len(set(item.affected_labs))
                 - min(item.effort_hours, 200))
        ranks.append((item.finding_id, score))
    return sorted(ranks, key=lambda x: (-x[1], x[0]))


def modeled_offer_value(*, fixed_fee_cents: int, collection_probability_bps: int,
                        analyst_minutes: int, loaded_hourly_cost_cents: int,
                        other_cost_cents: int) -> Mapping[str, int | str]:
    """Assumption-only expected fixed-fee margin; NOT measured revenue."""
    for field, v in {"fixed_fee_cents": fixed_fee_cents,
                     "analyst_minutes": analyst_minutes,
                     "loaded_hourly_cost_cents": loaded_hourly_cost_cents,
                     "other_cost_cents": other_cost_cents}.items():
        _cents(v, field)
    if type(collection_probability_bps) is not int or not 0 <= collection_probability_bps <= 10_000:
        raise ValueError("collection_probability_bps must be integer in [0, 10000]")
    expected_fee = fixed_fee_cents * collection_probability_bps // 10_000
    estimated_cost = (analyst_minutes * loaded_hourly_cost_cents + 59) // 60 + other_cost_cents
    return {"scope": "MODELED_ASSUMPTIONS_ONLY", "expected_fee_cents": expected_fee,
            "estimated_cost_cents": estimated_cost,
            "expected_net_cents": expected_fee - estimated_cost}
