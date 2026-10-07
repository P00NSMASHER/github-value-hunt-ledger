"""Deterministic contract/rate authority compiler for RecoveryOS phase 0.

The compiler consumes normalized, human-reviewed commercial terms. It never
claims that OCR/model output is controlling authority on its own. Verification
state is supplied by trusted review context and is included in the authority
hash so a later approval creates a different immutable authority object.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable

from freight.canonical_schema import CanonicalFreightRecord, MODES
from freight.contracts import canonical_hash

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
ACCESSORIAL_MODELS = {"INCLUDED", "FIXED", "PER_UNIT"}


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _integer(name: str, value: object, *, minimum: int = 0, maximum: int = 2**63 - 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def _iso_date(name: str, value: object) -> str:
    text = _text(name, value)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc
    return text


def _bp(name: str, value: object, *, maximum: int = 100000) -> int:
    return _integer(name, value, minimum=0, maximum=maximum)


def _normalize_accessorials(raw: object) -> tuple[tuple[str, str, int | None], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise ValueError("accessorials must be an object")
    out: list[tuple[str, str, int | None]] = []
    for raw_code, spec in raw.items():
        code = _text("accessorial code", raw_code).upper()
        if not isinstance(spec, dict):
            raise ValueError(f"accessorial {code} must be an object")
        model = _text(f"accessorial {code}.model", spec.get("model")).upper()
        if model not in ACCESSORIAL_MODELS:
            raise ValueError(f"unsupported accessorial model for {code}")
        cents = spec.get("cents")
        if model == "INCLUDED":
            if cents is not None:
                raise ValueError(f"INCLUDED accessorial {code} cannot define cents")
            normalized_cents = None
        else:
            normalized_cents = _integer(f"accessorial {code}.cents", cents, minimum=0)
        out.append((code, model, normalized_cents))
    if len({x[0] for x in out}) != len(out):
        raise ValueError("duplicate accessorial code")
    return tuple(sorted(out))


@dataclass(frozen=True)
class LTLTerms:
    per_cwt_cents: int
    minimum_cents: int
    discount_bps: int
    fuel_bps: int
    lane_multiplier_bps: int
    class_multipliers_bps: tuple[tuple[str, int], ...]
    accessorials: tuple[tuple[str, str, int | None], ...]


@dataclass(frozen=True)
class ParcelWeightBand:
    max_billable_lb: int
    zone_rates_cents: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class ParcelTerms:
    dimensional_divisor: int
    fuel_bps: int
    residential_cents: int
    weight_bands: tuple[ParcelWeightBand, ...]
    accessorials: tuple[tuple[str, str, int | None], ...]


@dataclass(frozen=True)
class CompiledAuthority:
    authority_id: str
    buyer_id: str
    business_unit: str
    customer_id: str
    carrier_id: str
    currency: str
    mode: str
    effective_from: str
    effective_to: str | None
    priority: int
    source_sha256: str
    verified_controlling_authority: bool
    ltl_terms: LTLTerms | None
    parcel_terms: ParcelTerms | None
    compiler_version: int
    authority_hash: str

    @property
    def verified(self) -> bool:
        return self.verified_controlling_authority


@dataclass(frozen=True)
class AuthorityResolution:
    status: str
    authority: CompiledAuthority | None
    candidate_hashes: tuple[str, ...]
    reason: str
    resolution_hash: str


def _compile_ltl(terms: object) -> LTLTerms:
    if not isinstance(terms, dict):
        raise ValueError("LTL terms must be an object")
    classes_raw = terms.get("class_multipliers_bps") or {}
    if not isinstance(classes_raw, dict):
        raise ValueError("class_multipliers_bps must be an object")
    classes: list[tuple[str, int]] = []
    for key, value in classes_raw.items():
        classes.append((_text("freight class", key), _bp("class multiplier", value, maximum=100000)))
    return LTLTerms(
        per_cwt_cents=_integer("per_cwt_cents", terms.get("per_cwt_cents"), minimum=0),
        minimum_cents=_integer("minimum_cents", terms.get("minimum_cents", 0), minimum=0),
        discount_bps=_bp("discount_bps", terms.get("discount_bps", 0), maximum=10000),
        fuel_bps=_bp("fuel_bps", terms.get("fuel_bps", 0), maximum=100000),
        lane_multiplier_bps=_bp("lane_multiplier_bps", terms.get("lane_multiplier_bps", 10000), maximum=100000),
        class_multipliers_bps=tuple(sorted(classes)),
        accessorials=_normalize_accessorials(terms.get("accessorials")),
    )


def _compile_parcel(terms: object) -> ParcelTerms:
    if not isinstance(terms, dict):
        raise ValueError("PARCEL terms must be an object")
    raw_bands = terms.get("weight_bands")
    if not isinstance(raw_bands, list) or not raw_bands:
        raise ValueError("parcel weight_bands must be a non-empty list")
    bands: list[ParcelWeightBand] = []
    prior = 0
    for index, raw in enumerate(raw_bands, 1):
        if not isinstance(raw, dict):
            raise ValueError("parcel weight band must be an object")
        maximum = _integer(f"weight_bands[{index}].max_billable_lb", raw.get("max_billable_lb"), minimum=1)
        if maximum <= prior:
            raise ValueError("parcel weight bands must be strictly ascending")
        prior = maximum
        zones_raw = raw.get("zone_rates_cents")
        if not isinstance(zones_raw, dict) or not zones_raw:
            raise ValueError("parcel weight band requires zone_rates_cents")
        zones = tuple(sorted(
            (_text("zone", zone), _integer("zone rate cents", cents, minimum=0))
            for zone, cents in zones_raw.items()
        ))
        bands.append(ParcelWeightBand(maximum, zones))
    return ParcelTerms(
        dimensional_divisor=_integer("dimensional_divisor", terms.get("dimensional_divisor", 139), minimum=1),
        fuel_bps=_bp("fuel_bps", terms.get("fuel_bps", 0), maximum=100000),
        residential_cents=_integer("residential_cents", terms.get("residential_cents", 0), minimum=0),
        weight_bands=tuple(bands),
        accessorials=_normalize_accessorials(terms.get("accessorials")),
    )


def _authority_body(authority: CompiledAuthority) -> dict:
    body = asdict(authority)
    body.pop("authority_hash", None)
    return body


def compile_authority(
    payload: dict,
    *,
    source_sha256: str,
    verified_controlling_authority: bool,
) -> CompiledAuthority:
    if not isinstance(payload, dict):
        raise ValueError("authority payload must be an object")
    if not isinstance(source_sha256, str) or not SHA256_RE.fullmatch(source_sha256):
        raise ValueError("source_sha256 must be lowercase SHA-256")
    if type(verified_controlling_authority) is not bool:
        raise ValueError("verified_controlling_authority must be boolean")

    authority_id = _text("authority_id", payload.get("authority_id"))
    buyer_id = _text("buyer_id", payload.get("buyer_id"))
    business_unit = _text("business_unit", payload.get("business_unit"))
    customer_id = _text("customer_id", payload.get("customer_id"))
    carrier_id = _text("carrier_id", payload.get("carrier_id"))
    currency = _text("currency", payload.get("currency")).upper()
    if not CURRENCY_RE.fullmatch(currency):
        raise ValueError("currency must be a three-letter code")
    mode = _text("mode", payload.get("mode")).upper()
    if mode not in MODES:
        raise ValueError("unsupported freight mode")
    if mode not in {"LTL", "PARCEL"}:
        raise ValueError("phase-0 authority compiler currently rates LTL and PARCEL")
    effective_from = _iso_date("effective_from", payload.get("effective_from"))
    effective_to_raw = payload.get("effective_to")
    effective_to = _iso_date("effective_to", effective_to_raw) if effective_to_raw not in (None, "") else None
    if effective_to is not None and effective_to < effective_from:
        raise ValueError("effective_to cannot precede effective_from")
    priority = _integer("priority", payload.get("priority", 0), minimum=0, maximum=1_000_000)
    terms = payload.get("terms")
    ltl_terms = _compile_ltl(terms) if mode == "LTL" else None
    parcel_terms = _compile_parcel(terms) if mode == "PARCEL" else None

    partial = CompiledAuthority(
        authority_id=authority_id,
        buyer_id=buyer_id,
        business_unit=business_unit,
        customer_id=customer_id,
        carrier_id=carrier_id,
        currency=currency,
        mode=mode,
        effective_from=effective_from,
        effective_to=effective_to,
        priority=priority,
        source_sha256=source_sha256,
        verified_controlling_authority=verified_controlling_authority,
        ltl_terms=ltl_terms,
        parcel_terms=parcel_terms,
        compiler_version=1,
        authority_hash="",
    )
    digest = canonical_hash(_authority_body(partial))
    return CompiledAuthority(
        authority_id=authority_id,
        buyer_id=buyer_id,
        business_unit=business_unit,
        customer_id=customer_id,
        carrier_id=carrier_id,
        currency=currency,
        mode=mode,
        effective_from=effective_from,
        effective_to=effective_to,
        priority=priority,
        source_sha256=source_sha256,
        verified_controlling_authority=verified_controlling_authority,
        ltl_terms=ltl_terms,
        parcel_terms=parcel_terms,
        compiler_version=1,
        authority_hash=digest,
    )


def verify_compiled_authority(authority: CompiledAuthority) -> None:
    if canonical_hash(_authority_body(authority)) != authority.authority_hash:
        raise ValueError("authority hash mismatch")


class AuthorityBook:
    def __init__(self, authorities: Iterable[CompiledAuthority]):
        normalized = tuple(authorities)
        if len({a.authority_hash for a in normalized}) != len(normalized):
            raise ValueError("duplicate authority")
        for authority in normalized:
            verify_compiled_authority(authority)
        self.authorities = normalized

    def resolve(self, record: CanonicalFreightRecord) -> AuthorityResolution:
        service_date = record.shipment.service_date
        matches = [a for a in self.authorities if (
            a.buyer_id == record.buyer_id
            and a.business_unit == record.business_unit
            and a.customer_id == record.customer_id
            and a.carrier_id == record.shipment.carrier_id
            and a.currency == record.currency
            and a.mode == record.shipment.mode
            and a.effective_from <= service_date
            and (a.effective_to is None or service_date <= a.effective_to)
        )]
        if not matches:
            body = {"schema": 1, "record_hash": record.record_hash, "status": "MISSING", "candidate_hashes": []}
            return AuthorityResolution("MISSING", None, (), "NO_APPLICABLE_AUTHORITY", canonical_hash(body))
        matches.sort(key=lambda a: (a.priority, a.effective_from, a.authority_hash), reverse=True)
        winner = matches[0]
        tied = [a for a in matches if (a.priority, a.effective_from) == (winner.priority, winner.effective_from)]
        hashes = tuple(sorted(a.authority_hash for a in tied))
        if len(tied) != 1:
            body = {"schema": 1, "record_hash": record.record_hash, "status": "AMBIGUOUS", "candidate_hashes": hashes}
            return AuthorityResolution("AMBIGUOUS", None, hashes, "AMBIGUOUS_CONTROLLING_AUTHORITY", canonical_hash(body))
        body = {"schema": 1, "record_hash": record.record_hash, "status": "RESOLVED", "candidate_hashes": hashes, "authority_hash": winner.authority_hash}
        return AuthorityResolution("RESOLVED", winner, hashes, "RESOLVED_BY_SCOPE_DATE_PRIORITY", canonical_hash(body))
