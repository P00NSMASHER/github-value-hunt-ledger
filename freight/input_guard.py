"""Fail-closed pre-parser boundary for Freight Recovery buyer files.

This module is deliberately conservative. It is not a sandbox and does not
replace isolated parser execution, but it blocks obvious hostile/unsupported
inputs before they reach document parsers or spreadsheet exports.
"""
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class InputStatus(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


@dataclass(frozen=True)
class IngestPolicy:
    max_file_bytes: int = 25_000_000
    max_text_line_chars: int = 1_000_000
    max_edi_segment_chars: int = 5_000
    max_csv_field_chars: int = 65_536
    max_csv_rows: int = 250_000
    max_csv_cells_per_row: int = 2_000
    max_csv_total_cells: int = 5_000_000
    allowed_extensions: tuple[str, ...] = (".pdf", ".csv", ".xml", ".edi", ".x12")

    def __post_init__(self):
        positive_limits = {
            "max_file_bytes": self.max_file_bytes,
            "max_text_line_chars": self.max_text_line_chars,
            "max_edi_segment_chars": self.max_edi_segment_chars,
            "max_csv_field_chars": self.max_csv_field_chars,
            "max_csv_rows": self.max_csv_rows,
            "max_csv_cells_per_row": self.max_csv_cells_per_row,
            "max_csv_total_cells": self.max_csv_total_cells,
        }
        for name, value in positive_limits.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class InputInspection:
    filename: str
    detected_format: str | None
    size_bytes: int
    sha256: str
    status: InputStatus
    reasons: tuple[str, ...]


ARCHIVE_MAGIC = (
    b"PK\x03\x04",
    b"PK\x05\x06",
    b"PK\x07\x08",
    b"\x1f\x8b",
)
ARCHIVE_EXTENSIONS = {".zip", ".gz", ".tgz", ".tar", ".7z", ".rar"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_leaf_filename(filename: str) -> bool:
    if not filename or filename in {".", ".."}:
        return False
    p = Path(filename)
    return p.name == filename and not p.is_absolute() and ".." not in p.parts


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8-sig", errors="strict")


def _text_line_too_long(text: str, limit: int) -> bool:
    """Check physical text lines without materializing a split-lines list."""
    for line in io.StringIO(text):
        if len(line.rstrip("\r\n")) > limit:
            return True
    return False


def _inspect_csv(text: str, policy: IngestPolicy, reasons: list[str]) -> None:
    """Stream logical CSV rows and enforce explicit resource/shape bounds."""
    row_count = 0
    total_cells = 0
    try:
        reader = csv.reader(io.StringIO(text, newline=""))
        for row in reader:
            row_count += 1
            if row_count > policy.max_csv_rows:
                reasons.append("csv_row_limit_exceeded")
                return

            row_cells = len(row)
            if row_cells > policy.max_csv_cells_per_row:
                reasons.append("csv_cells_per_row_limit_exceeded")
                return

            total_cells += row_cells
            if total_cells > policy.max_csv_total_cells:
                reasons.append("csv_total_cells_limit_exceeded")
                return

            if any(len(cell) > policy.max_csv_field_chars for cell in row):
                reasons.append("csv_field_too_long")
                return
    except csv.Error:
        # Python's csv parser has implementation-level limits and can reject
        # malformed/oversized records before our per-field check runs. The
        # boundary must still emit a typed REJECT instead of throwing.
        reasons.append("csv_parse_error")


def inspect_input(
    filename: str,
    data: bytes,
    policy: IngestPolicy | None = None,
) -> InputInspection:
    policy = policy or IngestPolicy()
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    data = bytes(data)
    reasons: list[str] = []

    if not _safe_leaf_filename(filename):
        reasons.append("unsafe_filename")

    ext = Path(filename).suffix.lower()
    detected = ext.lstrip(".") if ext else None

    if ext in ARCHIVE_EXTENSIONS:
        reasons.append("archive_inputs_not_supported")
    if ext not in policy.allowed_extensions:
        reasons.append("extension_not_allowlisted")
    if any(data.startswith(magic) for magic in ARCHIVE_MAGIC):
        reasons.append("archive_magic_rejected")
    if len(data) == 0:
        reasons.append("empty_file")
    if len(data) > policy.max_file_bytes:
        reasons.append("file_too_large")

    if not reasons:
        try:
            if ext == ".pdf":
                if not data.startswith(b"%PDF-"):
                    reasons.append("pdf_magic_mismatch")
            elif ext == ".xml":
                text = _decode_text(data)
                upper = text.upper()
                if "<!DOCTYPE" in upper:
                    reasons.append("xml_doctype_rejected")
                if "<!ENTITY" in upper:
                    reasons.append("xml_entity_rejected")
                if "\x00" in text:
                    reasons.append("nul_byte_rejected")
                if _text_line_too_long(text, policy.max_text_line_chars):
                    reasons.append("text_line_too_long")
            elif ext == ".csv":
                text = _decode_text(data)
                if "\x00" in text:
                    reasons.append("nul_byte_rejected")
                if _text_line_too_long(text, policy.max_text_line_chars):
                    reasons.append("text_line_too_long")
                if not reasons:
                    _inspect_csv(text, policy, reasons)
            elif ext in {".edi", ".x12"}:
                text = _decode_text(data)
                if "\x00" in text:
                    reasons.append("nul_byte_rejected")
                stripped = text.lstrip()
                if not (stripped.startswith("ISA") or stripped.startswith("UNB")):
                    reasons.append("edi_header_unrecognized")
                # X12 usually uses ~, EDIFACT usually uses '. Newline-delimited
                # files are also accepted after the header check.
                chunks = []
                for sep in ("~", "'"):
                    if sep in text:
                        chunks.extend(x for x in text.split(sep) if x)
                if not chunks:
                    chunks = [x for x in text.splitlines() if x]
                if any(len(seg) > policy.max_edi_segment_chars for seg in chunks):
                    reasons.append("edi_segment_too_long")
        except UnicodeDecodeError:
            reasons.append("invalid_utf8_text")

    status = InputStatus.REJECT if reasons else InputStatus.ACCEPT
    return InputInspection(
        filename=filename,
        detected_format=detected,
        size_bytes=len(data),
        sha256=_sha256(data),
        status=status,
        reasons=tuple(sorted(set(reasons))),
    )


def assert_accepted(
    filename: str,
    data: bytes,
    policy: IngestPolicy | None = None,
) -> InputInspection:
    result = inspect_input(filename, data, policy)
    if result.status is not InputStatus.ACCEPT:
        raise ValueError("input rejected: " + ",".join(result.reasons))
    return result


def neutralize_spreadsheet_cell(value: object) -> object:
    """Neutralize formula-leading text for CSV/XLSX export surfaces.

    The original ingested source should remain immutable. Apply this only to
    derived spreadsheet exports.
    """
    if not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if stripped and stripped[0] in {"=", "+", "-", "@"}:
        return "'" + value
    return value
