"""Transport-agnostic, fail-closed ingestion receipts for RecoveryOS phase 0."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from freight.contracts import canonical_hash
from freight.input_guard import inspect_input, InputStatus

TRANSPORTS = {"API", "EMAIL", "SFTP", "PORTAL", "UPLOAD", "BATCH"}


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


@dataclass(frozen=True)
class IngressEnvelope:
    ingress_id: str
    buyer_id: str
    business_unit: str
    transport: str
    filename: str


@dataclass(frozen=True)
class IngressReceipt:
    ingress_id: str
    buyer_id: str
    business_unit: str
    transport: str
    filename: str
    file_sha256: str
    size_bytes: int
    detected_format: str
    status: str
    route: str
    reasons: tuple[str, ...]
    receipt_hash: str


def ingest_bytes(envelope: IngressEnvelope, data: bytes) -> IngressReceipt:
    ingress_id = _text("ingress_id", envelope.ingress_id)
    buyer_id = _text("buyer_id", envelope.buyer_id)
    business_unit = _text("business_unit", envelope.business_unit)
    transport = _text("transport", envelope.transport).upper()
    filename = _text("filename", envelope.filename)
    if transport not in TRANSPORTS:
        raise ValueError("unsupported ingress transport")
    if "/" in filename or "\\" in filename or ":" in filename:
        raise ValueError("filename must be a safe leaf name")
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("data must be bytes")
    data = bytes(data)

    inspected = inspect_input(filename, data)
    status = "ACCEPT" if inspected.status is InputStatus.ACCEPT else "REJECT"
    detected = (inspected.detected_format or "UNKNOWN").upper()
    route = "DOCUMENT_EXTRACTION_REQUIRED" if detected == "PDF" and status == "ACCEPT" else (
        "NORMALIZE" if status == "ACCEPT" else "NONE"
    )
    body = {
        "schema": 1,
        "ingress_id": ingress_id,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "transport": transport,
        "filename": filename,
        "file_sha256": inspected.sha256,
        "size_bytes": inspected.size_bytes,
        "detected_format": detected,
        "status": status,
        "route": route,
        "reasons": tuple(inspected.reasons),
    }
    return IngressReceipt(
        ingress_id=ingress_id,
        buyer_id=buyer_id,
        business_unit=business_unit,
        transport=transport,
        filename=filename,
        file_sha256=inspected.sha256,
        size_bytes=inspected.size_bytes,
        detected_format=detected,
        status=status,
        route=route,
        reasons=tuple(inspected.reasons),
        receipt_hash=canonical_hash(body),
    )
