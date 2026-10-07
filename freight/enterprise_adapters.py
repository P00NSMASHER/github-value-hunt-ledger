"""Enterprise ingress adapters for RecoveryOS phase 1.

These adapters normalize API payloads, verify SFTP delivery manifests, and parse
X12 envelopes without letting transport metadata grant commercial authority.
Customer-specific X12 semantics are explicit mapping profiles rather than hidden
guesses.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from freight.canonical_schema import (
    CanonicalFreightRecord,
    ChargeLine,
    PackageFacts,
    ShipmentFacts,
    SourceArtifact,
    build_record,
)
from freight.contracts import canonical_hash
from freight.ingestion_gateway import IngressReceipt


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def _int(name: str, value: object, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum or value > 2**63 - 1:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def canonical_record_from_api(payload: dict) -> CanonicalFreightRecord:
    if not isinstance(payload, dict):
        raise ValueError("API record payload must be an object")
    shipment_raw = payload.get("shipment")
    if not isinstance(shipment_raw, dict):
        raise ValueError("shipment must be an object")
    packages_raw = shipment_raw.get("packages") or []
    if not isinstance(packages_raw, list):
        raise ValueError("shipment.packages must be a list")
    packages = tuple(
        PackageFacts(
            package_id=_text("package_id", item.get("package_id")),
            weight_grams=_int("weight_grams", item.get("weight_grams"), minimum=1),
            length_mm=item.get("length_mm"),
            width_mm=item.get("width_mm"),
            height_mm=item.get("height_mm"),
            quantity=_int("quantity", item.get("quantity", 1), minimum=1),
        )
        for item in packages_raw
        if isinstance(item, dict)
    )
    if len(packages) != len(packages_raw):
        raise ValueError("each package must be an object")

    shipment = ShipmentFacts(
        shipment_id=_text("shipment_id", shipment_raw.get("shipment_id")),
        carrier_id=_text("carrier_id", shipment_raw.get("carrier_id")),
        mode=_text("mode", shipment_raw.get("mode")).upper(),
        service_date=_text("service_date", shipment_raw.get("service_date")),
        origin_postal=_text("origin_postal", shipment_raw.get("origin_postal")),
        destination_postal=_text("destination_postal", shipment_raw.get("destination_postal")),
        actual_weight_grams=_int("actual_weight_grams", shipment_raw.get("actual_weight_grams"), minimum=1),
        package_count=_int("package_count", shipment_raw.get("package_count"), minimum=1),
        packages=packages,
        freight_class=shipment_raw.get("freight_class"),
        zone=shipment_raw.get("zone"),
        service_level=shipment_raw.get("service_level"),
        residential=shipment_raw.get("residential", False),
        miles=shipment_raw.get("miles"),
    )

    charges_raw = payload.get("charges")
    if not isinstance(charges_raw, list) or not charges_raw:
        raise ValueError("charges must be a non-empty list")
    charges = tuple(
        ChargeLine(
            charge_id=_text("charge_id", item.get("charge_id")),
            charge_code=_text("charge_code", item.get("charge_code")).upper(),
            billed_cents=_int("billed_cents", item.get("billed_cents")),
            quantity_units=_int("quantity_units", item.get("quantity_units", 1), minimum=1),
            description=item.get("description"),
        )
        for item in charges_raw
        if isinstance(item, dict)
    )
    if len(charges) != len(charges_raw):
        raise ValueError("each charge must be an object")

    sources_raw = payload.get("sources")
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ValueError("sources must be a non-empty list")
    sources = tuple(
        SourceArtifact(
            source_id=_text("source_id", item.get("source_id")),
            kind=_text("kind", item.get("kind")),
            sha256=_text("sha256", item.get("sha256")),
            observed_at=_text("observed_at", item.get("observed_at")),
            transport=_text("transport", item.get("transport")).upper(),
            filename=item.get("filename"),
        )
        for item in sources_raw
        if isinstance(item, dict)
    )
    if len(sources) != len(sources_raw):
        raise ValueError("each source must be an object")

    return build_record(
        buyer_id=_text("buyer_id", payload.get("buyer_id")),
        business_unit=_text("business_unit", payload.get("business_unit")),
        invoice_id=_text("invoice_id", payload.get("invoice_id")),
        invoice_date=_text("invoice_date", payload.get("invoice_date")),
        customer_id=_text("customer_id", payload.get("customer_id")),
        currency=_text("currency", payload.get("currency")).upper(),
        shipment=shipment,
        charges=charges,
        sources=sources,
        account_id=payload.get("account_id"),
    )


@dataclass(frozen=True)
class SFTPManifestEntry:
    filename: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        _text("filename", self.filename)
        _text("sha256", self.sha256)
        _int("size_bytes", self.size_bytes)


@dataclass(frozen=True)
class SFTPManifestVerification:
    status: str
    entry_count: int
    accepted_count: int
    missing_filenames: tuple[str, ...]
    mismatched_filenames: tuple[str, ...]
    rejected_filenames: tuple[str, ...]
    manifest_hash: str
    verification_hash: str


def verify_sftp_manifest(
    entries: Iterable[SFTPManifestEntry],
    receipts: Iterable[IngressReceipt],
) -> SFTPManifestVerification:
    normalized = tuple(sorted(entries, key=lambda x: x.filename))
    if not normalized:
        raise ValueError("SFTP manifest must contain at least one entry")
    if len({x.filename for x in normalized}) != len(normalized):
        raise ValueError("duplicate SFTP manifest filename")

    manifest_hash = canonical_hash({
        "schema": 1,
        "entries": [asdict(x) for x in normalized],
    })
    receipt_index = {receipt.filename: receipt for receipt in receipts}
    missing: list[str] = []
    mismatched: list[str] = []
    rejected: list[str] = []
    accepted = 0

    for entry in normalized:
        receipt = receipt_index.get(entry.filename)
        if receipt is None or receipt.transport != "SFTP":
            missing.append(entry.filename)
            continue
        if receipt.file_sha256 != entry.sha256 or receipt.size_bytes != entry.size_bytes:
            mismatched.append(entry.filename)
            continue
        if receipt.status != "ACCEPT":
            rejected.append(entry.filename)
            continue
        accepted += 1

    status = "VERIFIED" if accepted == len(normalized) else "REVIEW_REQUIRED"
    body = {
        "schema": 1,
        "manifest_hash": manifest_hash,
        "status": status,
        "accepted_count": accepted,
        "missing_filenames": sorted(missing),
        "mismatched_filenames": sorted(mismatched),
        "rejected_filenames": sorted(rejected),
    }
    return SFTPManifestVerification(
        status=status,
        entry_count=len(normalized),
        accepted_count=accepted,
        missing_filenames=tuple(sorted(missing)),
        mismatched_filenames=tuple(sorted(mismatched)),
        rejected_filenames=tuple(sorted(rejected)),
        manifest_hash=manifest_hash,
        verification_hash=canonical_hash(body),
    )


@dataclass(frozen=True)
class X12Segment:
    tag: str
    elements: tuple[str, ...]


@dataclass(frozen=True)
class X12Document:
    transaction_set: str
    segments: tuple[X12Segment, ...]
    document_hash: str


def parse_x12(
    text: str,
    *,
    expected_transaction_set: str = "210",
    segment_terminator: str = "~",
    element_separator: str = "*",
    max_segments: int = 100_000,
    max_elements_per_segment: int = 256,
) -> X12Document:
    text = _text("x12 text", text)
    if len(segment_terminator) != 1 or len(element_separator) != 1:
        raise ValueError("X12 separators must be one character")
    raw_segments = [x.strip() for x in text.split(segment_terminator) if x.strip()]
    if not raw_segments or len(raw_segments) > max_segments:
        raise ValueError("invalid X12 segment count")
    segments: list[X12Segment] = []
    for raw in raw_segments:
        parts = raw.split(element_separator)
        if not parts or len(parts) > max_elements_per_segment:
            raise ValueError("invalid X12 element count")
        tag = _text("segment tag", parts[0]).upper()
        if len(tag) > 8:
            raise ValueError("X12 segment tag too long")
        segments.append(X12Segment(tag=tag, elements=tuple(parts[1:])))

    st = next((segment for segment in segments if segment.tag == "ST"), None)
    if st is None or not st.elements:
        raise ValueError("X12 ST segment missing")
    transaction_set = st.elements[0]
    if transaction_set != expected_transaction_set:
        raise ValueError(
            f"unexpected X12 transaction set {transaction_set}; expected {expected_transaction_set}"
        )
    body = {
        "schema": 1,
        "transaction_set": transaction_set,
        "segments": [asdict(segment) for segment in segments],
    }
    return X12Document(
        transaction_set=transaction_set,
        segments=tuple(segments),
        document_hash=canonical_hash(body),
    )


@dataclass(frozen=True)
class X12FieldRef:
    segment_tag: str
    occurrence: int
    element_index: int

    def __post_init__(self) -> None:
        _text("segment_tag", self.segment_tag)
        _int("occurrence", self.occurrence, minimum=1)
        _int("element_index", self.element_index, minimum=1)


@dataclass(frozen=True)
class X12InvoiceProfile:
    invoice_id: X12FieldRef
    shipment_id: X12FieldRef
    invoice_date: X12FieldRef
    net_amount: X12FieldRef
    carrier_id: X12FieldRef
    amount_decimal_places: int = 2


@dataclass(frozen=True)
class X12InvoiceProjection:
    invoice_id: str
    shipment_id: str
    invoice_date: str
    net_amount_cents: int
    carrier_id: str
    source_document_hash: str
    projection_hash: str


def _field(document: X12Document, ref: X12FieldRef) -> str:
    matches = [segment for segment in document.segments if segment.tag == ref.segment_tag.upper()]
    if len(matches) < ref.occurrence:
        raise ValueError(f"missing X12 segment occurrence: {ref.segment_tag}[{ref.occurrence}]")
    segment = matches[ref.occurrence - 1]
    if len(segment.elements) < ref.element_index:
        raise ValueError(
            f"missing X12 element: {ref.segment_tag}[{ref.occurrence}].{ref.element_index}"
        )
    return _text("X12 mapped field", segment.elements[ref.element_index - 1])


def project_x12_invoice(
    document: X12Document,
    profile: X12InvoiceProfile,
) -> X12InvoiceProjection:
    invoice_id = _field(document, profile.invoice_id)
    shipment_id = _field(document, profile.shipment_id)
    invoice_date = _field(document, profile.invoice_date)
    carrier_id = _field(document, profile.carrier_id)
    raw_amount = _field(document, profile.net_amount)
    if profile.amount_decimal_places not in {0, 2}:
        raise ValueError("amount_decimal_places must be 0 or 2")
    if profile.amount_decimal_places == 0:
        if not raw_amount.isdigit():
            raise ValueError("X12 net amount must be unsigned integer cents")
        cents = int(raw_amount)
    else:
        pieces = raw_amount.split(".")
        if len(pieces) == 1 and pieces[0].isdigit():
            cents = int(pieces[0]) * 100
        elif (
            len(pieces) == 2
            and pieces[0].isdigit()
            and pieces[1].isdigit()
            and len(pieces[1]) <= 2
        ):
            cents = int(pieces[0]) * 100 + int(pieces[1].ljust(2, "0"))
        else:
            raise ValueError("X12 net amount must be an unsigned decimal")
    _int("net_amount_cents", cents)
    body = {
        "schema": 1,
        "document_hash": document.document_hash,
        "profile": asdict(profile),
        "invoice_id": invoice_id,
        "shipment_id": shipment_id,
        "invoice_date": invoice_date,
        "net_amount_cents": cents,
        "carrier_id": carrier_id,
    }
    return X12InvoiceProjection(
        invoice_id=invoice_id,
        shipment_id=shipment_id,
        invoice_date=invoice_date,
        net_amount_cents=cents,
        carrier_id=carrier_id,
        source_document_hash=document.document_hash,
        projection_hash=canonical_hash(body),
    )
