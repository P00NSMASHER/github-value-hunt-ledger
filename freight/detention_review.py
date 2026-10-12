"""Evidence-linked detention/demurrage/layover candidate review.

Opt-in decision support for canonical freight records. A candidate is NEVER a
validated finding, settled credit, or billable recovery. Time rounding adapts
MIT-licensed code from cmiedema25-rgb/freight-audit; see the vendor notice.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone

from freight.canonical_schema import CanonicalFreightRecord, verify_record
from freight.contracts import canonical_hash
from freight.vendor_detention_rounding import rounded_minutes

_SHA = re.compile(r"^[0-9a-f]{64}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_MAX_CENTS = 2**63 - 1
_SUPPORTED_CHARGES = frozenset({"DETENTION", "DEMURRAGE", "LAYOVER"})
_PHYSICAL_EVIDENCE = frozenset({"GATE_EVENT", "ELD_EVENT", "TERMINAL_EVENT", "TRACKING_EVENT"})
_ROUNDING = frozenset({"CEILING_TO_INCREMENT", "FLOOR_TO_INCREMENT", "HALF_UP_TO_INCREMENT"})


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError(name + " must be nonempty text without control characters")
    return value.strip()


def _sha(name: str, value: object) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError(name + " must be lowercase SHA-256")
    return value


def _cents(name: str, value: object) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_CENTS:
        raise ValueError(name + " must be nonnegative integer cents")
    return value


def _days(name: str, value: object) -> str:
    raw = _text(name, value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ValueError(name + " must be YYYY-MM-DD")
    try:
        date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(name + " must be a valid date") from exc
    return raw


def _utc_time(name: str, value: str) -> datetime:
    raw = _text(name, value)
    try:
        dt = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
    except ValueError as exc:
        raise ValueError(name + " must be ISO-8601 with explicit UTC offset") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(name + " requires an explicit offset (DST-safe)")
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class DetentionPolicy:
    policy_id: str
    buyer_id: str
    business_unit: str
    customer_id: str
    carrier_id: str
    origin_postal: str
    destination_postal: str
    currency: str
    mode: str
    charge_code: str
    effective_from: str
    effective_to: str | None
    free_minutes: int
    grace_minutes: int
    billing_increment_minutes: int
    cents_per_increment: int
    rounding_mode: str
    source_sha256: str
    verified_controlling_authority: bool
    policy_hash: str


def compile_detention_policy(
    payload: dict, *, source_sha256: str, verified_controlling_authority: bool
) -> DetentionPolicy:
    """Compile a scoped rate rule. A caller's approval assertion is NOT a signature."""
    if not isinstance(payload, dict):
        raise ValueError("policy payload must be an object")
    if type(verified_controlling_authority) is not bool:
        raise ValueError("verified_controlling_authority must be boolean")
    values = {name: _text(name, payload.get(name)) for name in (
        "policy_id", "buyer_id", "business_unit", "customer_id", "carrier_id",
        "origin_postal", "destination_postal", "currency", "mode", "charge_code", "rounding_mode",
    )}
    if not _CURRENCY.fullmatch(values["currency"]):
        raise ValueError("currency must be ISO-4217 uppercase")
    if values["mode"] not in {"TL", "LTL", "INTERMODAL", "OCEAN"}:
        raise ValueError("unsupported detention transportation mode")
    if values["charge_code"] not in _SUPPORTED_CHARGES:
        raise ValueError("unsupported accessorial for temporal review")
    if values["rounding_mode"] not in _ROUNDING:
        raise ValueError("unsupported rounding mode")
    values["effective_from"] = _days("effective_from", payload.get("effective_from"))
    end = payload.get("effective_to")
    values["effective_to"] = _days("effective_to", end) if end is not None else None
    if values["effective_to"] and values["effective_to"] < values["effective_from"]:
        raise ValueError("effective_to precedes effective_from")
    for name in ("free_minutes", "grace_minutes", "billing_increment_minutes", "cents_per_increment"):
        values[name] = _cents(name, payload.get(name))
    if not 1 <= values["billing_increment_minutes"] <= 24 * 60:
        raise ValueError("billing_increment_minutes outside 1..1440")
    if values["free_minutes"] > 45 * 24 * 60 or values["grace_minutes"] > 45 * 24 * 60:
        raise ValueError("free/grace periods exceed 45-day audit boundary")
    values["source_sha256"] = _sha("source_sha256", source_sha256)
    values["verified_controlling_authority"] = verified_controlling_authority
    return DetentionPolicy(**values, policy_hash=canonical_hash({"schema": 1, **values}))


def verify_detention_policy(policy: DetentionPolicy) -> None:
    fields = asdict(policy)
    digest = fields.pop("policy_hash")
    if digest != canonical_hash({"schema": 1, **fields}):
        raise ValueError("detention policy hash mismatch")
    compile_detention_policy(fields, source_sha256=policy.source_sha256,
                             verified_controlling_authority=policy.verified_controlling_authority)


@dataclass(frozen=True)
class DetentionTimeline:
    start_at: str
    end_at: str
    start_source_sha256: str
    end_source_sha256: str
    prior_paid_cents: int = 0
    prior_payment_source_sha256: str | None = None


@dataclass(frozen=True)
class DetentionReview:
    case_id: str
    record_hash: str
    charge_id: str
    policy_hash: str
    timeline_hash: str
    billed_cents: int
    elapsed_minutes: int
    billable_minutes: int | None
    rounded_minutes: int | None
    supported_remaining_cents: int | None
    candidate_excess_cents: int | None
    status: str
    blocker_codes: tuple[str, ...]
    evidence_hashes: tuple[str, ...]
    proof_hash: str

    @property
    def validated_cents(self) -> int:
        return 0

    @property
    def recovered_cents(self) -> int:
        return 0

    @property
    def fee_eligible_cents(self) -> int:
        return 0


def review_detention_charge(
    record: CanonicalFreightRecord,
    charge_id: str,
    policy: DetentionPolicy,
    timeline: DetentionTimeline,
) -> DetentionReview:
    """Derive an immutable review candidate; this NEVER approves an overcharge."""
    verify_record(record)
    verify_detention_policy(policy)
    charge_id = _text("charge_id", charge_id)
    matches = [line for line in record.charges if line.charge_id == charge_id]
    if len(matches) != 1:
        raise ValueError("charge_id must identify exactly one canonical charge")
    line = matches[0]
    if line.charge_code not in _SUPPORTED_CHARGES:
        raise ValueError("charge is not a supported time-based accessorial")
    _cents("billed_cents", line.billed_cents)
    _cents("prior_paid_cents", timeline.prior_paid_cents)
    start_hash = _sha("start_source_sha256", timeline.start_source_sha256)
    end_hash = _sha("end_source_sha256", timeline.end_source_sha256)
    paid_hash = (_sha("prior_payment_source_sha256", timeline.prior_payment_source_sha256)
                 if timeline.prior_payment_source_sha256 is not None else None)
    start = _utc_time("start_at", timeline.start_at)
    end = _utc_time("end_at", timeline.end_at)
    if end < start:
        raise ValueError("end_at precedes start_at")
    duration = end - start
    micros = (duration.days * 86400 + duration.seconds) * 1_000_000 + duration.microseconds
    minutes = (micros + 60_000_000 - 1) // 60_000_000
    timeline_hash = canonical_hash({
        "schema": 1, "start_utc": start.isoformat(), "end_utc": end.isoformat(),
        "start_source_sha256": start_hash, "end_source_sha256": end_hash,
        "prior_paid_cents": timeline.prior_paid_cents,
        "prior_payment_source_sha256": paid_hash,
    })
    blockers: list[str] = []
    if minutes > 45 * 24 * 60:
        blockers.append("TIME_WINDOW_EXCEEDS_45_DAYS")
    if not policy.verified_controlling_authority:
        blockers.append("CONTRACT_NOT_HUMAN_VERIFIED")
    if (record.buyer_id != policy.buyer_id or record.business_unit != policy.business_unit
        or record.customer_id != policy.customer_id or record.shipment.carrier_id != policy.carrier_id
        or record.currency != policy.currency or record.mode != policy.mode
        or record.shipment.origin_postal != policy.origin_postal
        or record.shipment.destination_postal != policy.destination_postal
        or line.charge_code != policy.charge_code):
        blockers.append("CONTRACT_SCOPE_MISMATCH")
    if (record.shipment.service_date < policy.effective_from
        or (policy.effective_to is not None and record.shipment.service_date > policy.effective_to)):
        blockers.append("CONTRACT_NOT_EFFECTIVE_ON_SERVICE_DATE")
    sources: dict[str, set[str]] = {}
    for item in record.sources:
        sources.setdefault(item.sha256, set()).add(item.kind)
    if (not sources.get(policy.source_sha256)
        or not sources[policy.source_sha256] <= {"CONTRACT", "RATE_AGREEMENT", "CONTRACT_ADDENDUM"}):
        blockers.append("CONTRACT_SOURCE_NOT_IN_RECORD")
    for key in (start_hash, end_hash):
        if not sources.get(key) or not sources[key] <= _PHYSICAL_EVIDENCE:
            blockers.append("MISSING_INDEPENDENT_TIME_EVENT")
            break
    if timeline.prior_paid_cents and (
        paid_hash is None or not sources.get(paid_hash)
        or not sources[paid_hash] <= {"PAYMENT_CONFIRMATION", "CREDIT_MEMO"}
    ):
        blockers.append("MISSING_PRIOR_PAYMENT_EVIDENCE")
    if len([other for other in record.charges if other.charge_code == line.charge_code]) > 1:
        blockers.append("MULTIPLE_SAME_TYPE_CHARGES_REQUIRE_ALLOCATION")

    billable = rounded_count = remaining = candidate = None
    if not blockers:
        billable = max(minutes - policy.free_minutes - policy.grace_minutes, 0)
        rounded_count = rounded_minutes(billable, policy.billing_increment_minutes, policy.rounding_mode)
        if rounded_count is None:
            raise ValueError("unsupported rounding mode")
        gross = (rounded_count // policy.billing_increment_minutes) * policy.cents_per_increment
        if gross > _MAX_CENTS:
            raise ValueError("computed temporal invoice amount exceeds integer cents")
        if timeline.prior_paid_cents > gross:
            blockers.append("PRIOR_PAID_EXCEEDS_SUPPORTED_GROSS")
            billable = rounded_count = None
        else:
            remaining = gross - timeline.prior_paid_cents
            candidate = max(line.billed_cents - remaining, 0)
    blocker_codes = tuple(sorted(set(blockers)))
    body = {
        "schema": 1, "record_hash": record.record_hash, "charge_id": charge_id,
        "policy_hash": policy.policy_hash, "timeline_hash": timeline_hash,
        "billed_cents": line.billed_cents, "elapsed_minutes": minutes,
        "billable_minutes": billable, "rounded_minutes": rounded_count,
        "supported_remaining_cents": remaining, "candidate_excess_cents": candidate,
        "status": "NEED_EVIDENCE" if blocker_codes else "REVIEW",
        "blocker_codes": blocker_codes,
        "evidence_hashes": tuple(sorted({policy.source_sha256, start_hash, end_hash, *(
            (paid_hash,) if paid_hash else ()
        )})),
    }
    digest = canonical_hash(body)
    return DetentionReview(
        case_id="time:" + digest,
        record_hash=record.record_hash, charge_id=charge_id,
        policy_hash=policy.policy_hash, timeline_hash=timeline_hash,
        billed_cents=line.billed_cents, elapsed_minutes=minutes,
        billable_minutes=billable, rounded_minutes=rounded_count,
        supported_remaining_cents=remaining, candidate_excess_cents=candidate,
        status=body["status"], blocker_codes=blocker_codes,
        evidence_hashes=body["evidence_hashes"], proof_hash=digest,
    )


def verify_detention_review(candidate: DetentionReview) -> None:
    """Reject post-derivation edits before presenting money to a reviewer."""
    body = asdict(candidate)
    digest = body.pop("proof_hash")
    case_id = body.pop("case_id")
    expected = canonical_hash({"schema": 1, **body})
    if digest != expected or case_id != "time:" + expected:
        raise ValueError("temporal review candidate hash mismatch")


def detention_to_review_case(candidate: DetentionReview):
    """Add a proven candidate to the EXISTING human reviewer cockpit, never findings."""
    verify_detention_review(candidate)
    if candidate.status != "REVIEW" or not candidate.candidate_excess_cents:
        return None
    from freight.reviewer_cockpit import make_case
    return make_case(
        case_id=candidate.case_id,
        record_hash=candidate.record_hash,
        amount_cents=candidate.candidate_excess_cents,
        confidence_ppm=0, novelty_ppm=0, downstream_risk_ppm=1_000_000,
        blocker_codes=("HUMAN_REVIEW_REQUIRED", "NO_SETTLEMENT_PROOF"),
        evidence_hashes=(*candidate.evidence_hashes, candidate.proof_hash),
    )
