"""Deterministic LTL and parcel rerating engine for RecoveryOS phase 0."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from freight.canonical_schema import CanonicalFreightRecord, PackageFacts, verify_record
from freight.contracts import canonical_hash
from freight.rate_authority import (
    AuthorityBook,
    CompiledAuthority,
    LTLTerms,
    ParcelTerms,
)

RATED = "RATED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"


def _ceil_div(numerator: int, denominator: int) -> int:
    if numerator < 0 or denominator <= 0:
        raise ValueError("invalid ceil division operands")
    return (numerator + denominator - 1) // denominator


def _basis_points(value: int, bps: int) -> int:
    return (value * bps + 5_000) // 10_000


@dataclass(frozen=True)
class RatedComponent:
    code: str
    expected_cents: int
    basis: str


@dataclass(frozen=True)
class RatingResult:
    record_hash: str
    mode: str
    status: str
    authority_id: str | None
    authority_hash: str | None
    authority_verified: bool
    billed_total_cents: int
    expected_total_cents: int | None
    variance_cents: int | None
    components: tuple[RatedComponent, ...]
    blockers: tuple[str, ...]
    rating_hash: str


def _finish(
    record: CanonicalFreightRecord,
    *,
    status: str,
    authority: CompiledAuthority | None,
    expected: int | None,
    components: tuple[RatedComponent, ...],
    blockers: tuple[str, ...],
) -> RatingResult:
    billed = record.billed_total_cents
    variance = None if expected is None else max(billed - expected, 0)
    body = {
        "schema": 1,
        "record_hash": record.record_hash,
        "mode": record.mode,
        "status": status,
        "authority_id": authority.authority_id if authority else None,
        "authority_hash": authority.authority_hash if authority else None,
        "authority_verified": authority.verified if authority else False,
        "billed_total_cents": billed,
        "expected_total_cents": expected,
        "variance_cents": variance,
        "components": [asdict(item) for item in components],
        "blockers": blockers,
    }
    return RatingResult(
        record_hash=record.record_hash,
        mode=record.mode,
        status=status,
        authority_id=body["authority_id"],
        authority_hash=body["authority_hash"],
        authority_verified=body["authority_verified"],
        billed_total_cents=billed,
        expected_total_cents=expected,
        variance_cents=variance,
        components=components,
        blockers=blockers,
        rating_hash=canonical_hash(body),
    )


def _accessorials(
    record: CanonicalFreightRecord,
    rules: tuple[tuple[str, str, int | None], ...],
    excluded_codes: set[str],
) -> tuple[list[RatedComponent], list[str]]:
    mapping = {code: (model, cents) for code, model, cents in rules}
    components: list[RatedComponent] = []
    blockers: list[str] = []
    for line in record.charges:
        code = line.charge_code.upper()
        if code in excluded_codes:
            continue
        spec = mapping.get(code)
        if spec is None:
            blockers.append("UNMAPPED_ACCESSORIAL:" + code)
            continue
        model, cents = spec
        if model == "INCLUDED":
            expected = 0
        elif model == "FIXED":
            assert cents is not None
            expected = cents
        elif model == "PER_UNIT":
            assert cents is not None
            expected = cents * line.quantity_units
        else:
            blockers.append("INVALID_ACCESSORIAL_MODEL:" + code)
            continue
        components.append(RatedComponent(code, expected, model))
    return components, blockers


def _rate_ltl(
    record: CanonicalFreightRecord,
    authority: CompiledAuthority,
) -> tuple[int | None, tuple[RatedComponent, ...], tuple[str, ...]]:
    terms: LTLTerms = authority.ltl_terms  # type: ignore[assignment]
    assert terms is not None
    blockers: list[str] = []
    cwt = _ceil_div(record.shipment.actual_weight_grams * 10, 453_592)

    class_bps = 10_000
    class_map = dict(terms.class_multipliers_bps)
    if class_map:
        freight_class = record.shipment.freight_class
        if not freight_class:
            blockers.append("MISSING_FREIGHT_CLASS")
        elif freight_class not in class_map:
            blockers.append("UNMAPPED_FREIGHT_CLASS:" + freight_class)
        else:
            class_bps = class_map[freight_class]

    linehaul = terms.per_cwt_cents * cwt
    linehaul = _basis_points(linehaul, class_bps)
    linehaul = _basis_points(linehaul, terms.lane_multiplier_bps)
    linehaul = _basis_points(linehaul, 10_000 - terms.discount_bps)
    linehaul = max(linehaul, terms.minimum_cents)
    fuel = _basis_points(linehaul, terms.fuel_bps)
    components = [
        RatedComponent("LINEHAUL", linehaul, f"{cwt} CWT"),
        RatedComponent("FUEL", fuel, f"{terms.fuel_bps} bps of linehaul"),
    ]
    extras, extra_blockers = _accessorials(
        record, terms.accessorials, {"LINEHAUL", "FUEL", "TRANSPORTATION"}
    )
    components.extend(extras)
    blockers.extend(extra_blockers)
    if blockers:
        return None, tuple(components), tuple(sorted(set(blockers)))
    return sum(item.expected_cents for item in components), tuple(components), ()


def _actual_lb(package: PackageFacts) -> int:
    return _ceil_div(package.weight_grams * 1_000, 453_592)


def _dim_lb(package: PackageFacts, divisor: int) -> int:
    if package.length_mm is None:
        return 0
    assert package.width_mm is not None and package.height_mm is not None
    cubic_mm = package.length_mm * package.width_mm * package.height_mm
    return _ceil_div(cubic_mm * 1_000, divisor * 16_387_064)


def _parcel_base(terms: ParcelTerms, billable_lb: int, zone: str) -> int | None:
    for band in terms.weight_bands:
        if billable_lb <= band.max_billable_lb:
            return dict(band.zone_rates_cents).get(zone)
    return None


def _rate_parcel(
    record: CanonicalFreightRecord,
    authority: CompiledAuthority,
) -> tuple[int | None, tuple[RatedComponent, ...], tuple[str, ...]]:
    terms: ParcelTerms = authority.parcel_terms  # type: ignore[assignment]
    assert terms is not None
    zone = record.shipment.zone
    if not zone:
        return None, (), ("MISSING_PARCEL_ZONE",)

    packages = record.shipment.packages
    if not packages:
        if record.shipment.package_count != 1:
            return None, (), ("MISSING_PACKAGE_DETAIL",)
        packages = (
            PackageFacts(
                package_id="synthetic:shipment",
                weight_grams=record.shipment.actual_weight_grams,
            ),
        )

    components: list[RatedComponent] = []
    blockers: list[str] = []
    transportation_total = 0
    for package in packages:
        actual_lb = _actual_lb(package)
        dim_lb = _dim_lb(package, terms.dimensional_divisor)
        billable_lb = max(actual_lb, dim_lb)
        base = _parcel_base(terms, billable_lb, zone)
        if base is None:
            blockers.append(f"NO_PARCEL_RATE:zone={zone}:weight={billable_lb}")
            continue
        amount = base * package.quantity
        transportation_total += amount
        components.append(RatedComponent(
            "TRANSPORTATION",
            amount,
            f"package={package.package_id}; billable_lb={billable_lb}; zone={zone}",
        ))

    fuel = _basis_points(transportation_total, terms.fuel_bps)
    components.append(RatedComponent("FUEL", fuel, f"{terms.fuel_bps} bps of transportation"))
    if record.shipment.residential:
        residential = terms.residential_cents * record.shipment.package_count
        components.append(RatedComponent("RESIDENTIAL", residential, "residential shipment"))

    extras, extra_blockers = _accessorials(
        record,
        terms.accessorials,
        {"TRANSPORTATION", "LINEHAUL", "FUEL", "RESIDENTIAL"},
    )
    components.extend(extras)
    blockers.extend(extra_blockers)
    if blockers:
        return None, tuple(components), tuple(sorted(set(blockers)))
    return sum(item.expected_cents for item in components), tuple(components), ()


def rate_record(record: CanonicalFreightRecord, authority_book: AuthorityBook) -> RatingResult:
    verify_record(record)
    resolution = authority_book.resolve(record)
    if resolution.status != "RESOLVED" or resolution.authority is None:
        return _finish(
            record,
            status=REVIEW_REQUIRED,
            authority=None,
            expected=None,
            components=(),
            blockers=(resolution.reason,),
        )

    authority = resolution.authority
    if record.mode == "LTL":
        expected, components, blockers = _rate_ltl(record, authority)
    elif record.mode == "PARCEL":
        expected, components, blockers = _rate_parcel(record, authority)
    else:
        return _finish(
            record,
            status=REVIEW_REQUIRED,
            authority=authority,
            expected=None,
            components=(),
            blockers=("MODE_NOT_SUPPORTED_IN_PHASE0:" + record.mode,),
        )

    if not authority.verified:
        blockers = tuple(sorted(set(blockers + ("AUTHORITY_NOT_HUMAN_VERIFIED",))))
    status = RATED if expected is not None and not blockers else REVIEW_REQUIRED
    return _finish(
        record,
        status=status,
        authority=authority,
        expected=expected,
        components=components,
        blockers=blockers,
    )
