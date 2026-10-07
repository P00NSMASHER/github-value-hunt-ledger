"""Canonical, proof-bound freight record schema used by RecoveryOS phase 0.

The schema intentionally stores money in integer cents and physical measures in
integer SI units.  Records are immutable and carry a deterministic content hash.
No parser or model is allowed to promote a source document directly into a
validated recovery claim; this module only normalizes shipment/invoice facts.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Iterable

from freight.contracts import canonical_hash

SCHEMA_VERSION = 1
MODES = {"PARCEL", "LTL", "TL", "INTERMODAL", "AIR", "OCEAN"}
TRANSPORTS = {"API", "EMAIL", "SFTP", "PORTAL", "UPLOAD", "BATCH"}
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    value = value.strip()
    if any(ord(ch) < 32 for ch in value):
        raise ValueError(f"{name} contains control characters")
    return value


def _iso_date(name: str, value: str) -> str:
    value = _text(name, value)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc
    return value


def _timestamp(name: str, value: str) -> str:
    value = _text(name, value)
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware ISO-8601")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _int(name: str, value: int, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > 2**63 - 1:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class SourceArtifact:
    source_id: str
    kind: str
    sha256: str
    observed_at: str
    transport: str
    filename: str | None = None

    def __post_init__(self) -> None:
        _text("source_id", self.source_id)
        _text("kind", self.kind)
        if not SHA256_RE.fullmatch(self.sha256):
            raise ValueError("sha256 must be lowercase SHA-256")
        canonical = _timestamp("observed_at", self.observed_at)
        if canonical != self.observed_at:
            raise ValueError("observed_at must be canonical UTC")
        if self.transport not in TRANSPORTS:
            raise ValueError("unsupported transport")
        if self.filename is not None:
            _text("filename", self.filename)

    @property
    def artifact_hash(self) -> str:
        return canonical_hash({"schema": SCHEMA_VERSION, **asdict(self)})


@dataclass(frozen=True)
class PackageFacts:
    package_id: str
    weight_grams: int
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    quantity: int = 1

    def __post_init__(self) -> None:
        _text("package_id", self.package_id)
        _int("weight_grams", self.weight_grams, minimum=1)
        _int("quantity", self.quantity, minimum=1)
        dims = (self.length_mm, self.width_mm, self.height_mm)
        if any(value is not None for value in dims):
            if not all(value is not None for value in dims):
                raise ValueError("package dimensions must be all present or all absent")
            for name, value in zip(("length_mm", "width_mm", "height_mm"), dims):
                assert value is not None
                _int(name, value, minimum=1)


@dataclass(frozen=True)
class ShipmentFacts:
    shipment_id: str
    carrier_id: str
    mode: str
    service_date: str
    origin_postal: str
    destination_postal: str
    actual_weight_grams: int
    package_count: int
    packages: tuple[PackageFacts, ...] = ()
    freight_class: str | None = None
    zone: str | None = None
    service_level: str | None = None
    residential: bool = False
    miles: int | None = None

    def __post_init__(self) -> None:
        _text("shipment_id", self.shipment_id)
        _text("carrier_id", self.carrier_id)
        if self.mode not in MODES:
            raise ValueError("unsupported freight mode")
        _iso_date("service_date", self.service_date)
        _text("origin_postal", self.origin_postal)
        _text("destination_postal", self.destination_postal)
        _int("actual_weight_grams", self.actual_weight_grams, minimum=1)
        _int("package_count", self.package_count, minimum=1)
        if type(self.residential) is not bool:
            raise ValueError("residential must be boolean")
        if self.miles is not None:
            _int("miles", self.miles, minimum=0)
        for value, name in ((self.freight_class, "freight_class"), (self.zone, "zone"), (self.service_level, "service_level")):
            if value is not None:
                _text(name, value)
        if self.packages:
            if len({p.package_id for p in self.packages}) != len(self.packages):
                raise ValueError("duplicate package_id")
            represented = sum(p.quantity for p in self.packages)
            if represented != self.package_count:
                raise ValueError("package_count must equal represented package quantity")


@dataclass(frozen=True)
class ChargeLine:
    charge_id: str
    charge_code: str
    billed_cents: int
    quantity_units: int = 1
    description: str | None = None

    def __post_init__(self) -> None:
        _text("charge_id", self.charge_id)
        _text("charge_code", self.charge_code)
        if self.charge_code != self.charge_code.upper():
            raise ValueError("charge_code must be uppercase canonical form")
        _int("billed_cents", self.billed_cents)
        _int("quantity_units", self.quantity_units, minimum=1)
        if self.description is not None:
            _text("description", self.description)


@dataclass(frozen=True)
class CanonicalFreightRecord:
    schema_version: int
    buyer_id: str
    business_unit: str
    invoice_id: str
    invoice_date: str
    customer_id: str
    currency: str
    shipment: ShipmentFacts
    charges: tuple[ChargeLine, ...]
    sources: tuple[SourceArtifact, ...]
    account_id: str | None
    record_hash: str

    @property
    def billed_total_cents(self) -> int:
        return sum(line.billed_cents for line in self.charges)

    @property
    def mode(self) -> str:
        return self.shipment.mode


def _record_body(
    *, buyer_id: str, business_unit: str, invoice_id: str, invoice_date: str,
    customer_id: str, currency: str, shipment: ShipmentFacts,
    charges: tuple[ChargeLine, ...], sources: tuple[SourceArtifact, ...],
    account_id: str | None,
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "invoice_id": invoice_id,
        "invoice_date": invoice_date,
        "customer_id": customer_id,
        "currency": currency,
        "shipment": asdict(shipment),
        "charges": [asdict(x) for x in charges],
        "sources": [asdict(x) for x in sources],
        "account_id": account_id,
    }


def build_record(
    *, buyer_id: str, business_unit: str, invoice_id: str, invoice_date: str,
    customer_id: str, currency: str, shipment: ShipmentFacts,
    charges: Iterable[ChargeLine], sources: Iterable[SourceArtifact],
    account_id: str | None = None,
) -> CanonicalFreightRecord:
    buyer_id = _text("buyer_id", buyer_id)
    business_unit = _text("business_unit", business_unit)
    invoice_id = _text("invoice_id", invoice_id)
    invoice_date = _iso_date("invoice_date", invoice_date)
    customer_id = _text("customer_id", customer_id)
    currency = _text("currency", currency).upper()
    if not CURRENCY_RE.fullmatch(currency):
        raise ValueError("currency must be a three-letter code")
    if account_id is not None:
        account_id = _text("account_id", account_id)
    normalized_charges = tuple(charges)
    normalized_sources = tuple(sources)
    if not normalized_charges:
        raise ValueError("record requires at least one charge")
    if not normalized_sources:
        raise ValueError("record requires at least one source artifact")
    if len({x.charge_id for x in normalized_charges}) != len(normalized_charges):
        raise ValueError("duplicate charge_id")
    if len({x.source_id for x in normalized_sources}) != len(normalized_sources):
        raise ValueError("duplicate source_id")
    body = _record_body(
        buyer_id=buyer_id, business_unit=business_unit, invoice_id=invoice_id,
        invoice_date=invoice_date, customer_id=customer_id, currency=currency,
        shipment=shipment, charges=normalized_charges, sources=normalized_sources,
        account_id=account_id,
    )
    return CanonicalFreightRecord(
        schema_version=SCHEMA_VERSION,
        buyer_id=buyer_id,
        business_unit=business_unit,
        invoice_id=invoice_id,
        invoice_date=invoice_date,
        customer_id=customer_id,
        currency=currency,
        shipment=shipment,
        charges=normalized_charges,
        sources=normalized_sources,
        account_id=account_id,
        record_hash=canonical_hash(body),
    )


def verify_record(record: CanonicalFreightRecord) -> None:
    if record.schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported canonical schema version")
    rebuilt = build_record(
        buyer_id=record.buyer_id,
        business_unit=record.business_unit,
        invoice_id=record.invoice_id,
        invoice_date=record.invoice_date,
        customer_id=record.customer_id,
        currency=record.currency,
        shipment=record.shipment,
        charges=record.charges,
        sources=record.sources,
        account_id=record.account_id,
    )
    if rebuilt.record_hash != record.record_hash:
        raise ValueError("canonical freight record hash mismatch")


def record_payload(record: CanonicalFreightRecord) -> dict:
    verify_record(record)
    return {**_record_body(
        buyer_id=record.buyer_id, business_unit=record.business_unit,
        invoice_id=record.invoice_id, invoice_date=record.invoice_date,
        customer_id=record.customer_id, currency=record.currency,
        shipment=record.shipment, charges=record.charges, sources=record.sources,
        account_id=record.account_id,
    ), "record_hash": record.record_hash}
