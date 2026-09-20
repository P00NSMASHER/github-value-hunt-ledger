"""Fail-closed pre-parser boundary for Freight Recovery buyer files.

This module is deliberately conservative. It is not a sandbox and does not
replace isolated parser execution, but it blocks obvious unsupported inputs
before they reach document parsers or spreadsheet exports.
"""
from __future__ import annotations

import csv
import hashlib
import io
import xml.parsers.expat as expat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath


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
    max_xml_depth: int = 128
    max_xml_elements: int = 250_000
    max_xml_attributes_per_element: int = 256
    allowed_extensions: tuple[str, ...] = (".pdf", ".csv", ".xml", ".edi", ".x12")

    def __post_init__(self):
        limits = (
            ("max_file_bytes", self.max_file_bytes),
            ("max_text_line_chars", self.max_text_line_chars),
            ("max_edi_segment_chars", self.max_edi_segment_chars),
            ("max_csv_field_chars", self.max_csv_field_chars),
            ("max_csv_rows", self.max_csv_rows),
            ("max_csv_cells_per_row", self.max_csv_cells_per_row),
            ("max_csv_total_cells", self.max_csv_total_cells),
            ("max_xml_depth", self.max_xml_depth),
            ("max_xml_elements", self.max_xml_elements),
            ("max_xml_attributes_per_element", self.max_xml_attributes_per_element),
        )
        for name, value in limits:
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


ARCHIVE_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"\x1f\x8b")
ARCHIVE_EXTENSIONS = {".zip", ".gz", ".tgz", ".tar", ".7z", ".rar"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_leaf_filename(filename: str) -> bool:
    if not filename or filename in {".", ".."}:
        return False
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in filename):
        return False
    if "/" in filename or "\\" in filename or ":" in filename:
        return False

    for path_cls in (PurePosixPath, PureWindowsPath):
        path = path_cls(filename)
        if (
            path.is_absolute()
            or path.drive
            or path.root
            or path.name != filename
            or ".." in path.parts
        ):
            return False
    return True


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8-sig", errors="strict")


def _text_line_too_long(text: str, limit: int) -> bool:
    count = 0
    for ch in text:
        if ch in {"\r", "\n"}:
            count = 0
        else:
            count += 1
            if count > limit:
                return True
    return False


def _csv_shape_preflight(text: str, policy: IngestPolicy, reasons: list[str]) -> bool:
    rows = 0
    cells_in_row = 1
    total_cells = 0
    field_chars = 0
    in_quotes = False
    at_field_start = True
    row_has_data = False
    i = 0

    while i < len(text):
        ch = text[i]
        if in_quotes:
            if ch == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    field_chars += 1
                    i += 2
                else:
                    in_quotes = False
                    i += 1
            else:
                field_chars += 1
                i += 1
            if field_chars > policy.max_csv_field_chars:
                reasons.append("csv_field_too_long")
                return False
            row_has_data = True
            continue

        if ch == '"' and at_field_start:
            in_quotes = True
            at_field_start = False
            row_has_data = True
            i += 1
            continue

        if ch == ",":
            cells_in_row += 1
            if cells_in_row > policy.max_csv_cells_per_row:
                reasons.append("csv_cells_per_row_limit_exceeded")
                return False
            field_chars = 0
            at_field_start = True
            row_has_data = True
            i += 1
            continue

        if ch in {"\r", "\n"}:
            if ch == "\r" and i + 1 < len(text) and text[i + 1] == "\n":
                i += 1
            rows += 1
            if rows > policy.max_csv_rows:
                reasons.append("csv_row_limit_exceeded")
                return False
            total_cells += cells_in_row if row_has_data else 0
            if total_cells > policy.max_csv_total_cells:
                reasons.append("csv_total_cells_limit_exceeded")
                return False
            cells_in_row = 1
            field_chars = 0
            at_field_start = True
            row_has_data = False
            i += 1
            continue

        at_field_start = False
        row_has_data = True
        field_chars += 1
        if field_chars > policy.max_csv_field_chars:
            reasons.append("csv_field_too_long")
            return False
        i += 1

    if in_quotes:
        reasons.append("csv_parse_error")
        return False

    if row_has_data:
        rows += 1
        if rows > policy.max_csv_rows:
            reasons.append("csv_row_limit_exceeded")
            return False
        total_cells += cells_in_row
        if total_cells > policy.max_csv_total_cells:
            reasons.append("csv_total_cells_limit_exceeded")
            return False

    return True


def _inspect_csv(text: str, policy: IngestPolicy, reasons: list[str]) -> None:
    if not _csv_shape_preflight(text, policy, reasons):
        return
    try:
        for _ in csv.reader(io.StringIO(text, newline=""), strict=True):
            pass
    except csv.Error:
        reasons.append("csv_parse_error")


class _XMLLimitExceeded(Exception):
    pass


def _inspect_xml(text: str, policy: IngestPolicy, reasons: list[str]) -> None:
    depth = 0
    elements = 0
    limit_reason: str | None = None
    parser = expat.ParserCreate()

    def start_element(_name: str, attributes: dict[str, str]) -> None:
        nonlocal depth, elements, limit_reason
        depth += 1
        elements += 1
        if depth > policy.max_xml_depth:
            limit_reason = "xml_depth_limit_exceeded"
            raise _XMLLimitExceeded
        if elements > policy.max_xml_elements:
            limit_reason = "xml_element_limit_exceeded"
            raise _XMLLimitExceeded
        if len(attributes) > policy.max_xml_attributes_per_element:
            limit_reason = "xml_attribute_limit_exceeded"
            raise _XMLLimitExceeded

    def end_element(_name: str) -> None:
        nonlocal depth
        depth -= 1

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    try:
        parser.Parse(text, True)
    except _XMLLimitExceeded:
        if limit_reason is not None:
            reasons.append(limit_reason)
    except expat.ExpatError:
        reasons.append("xml_parse_error")


def _edi_segment_too_long(text: str, limit: int) -> bool:
    segment_chars = 0
    for ch in text:
        if ch in {"~", "'", "\r", "\n"}:
            segment_chars = 0
            continue
        segment_chars += 1
        if segment_chars > limit:
            return True
    return False


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
                if not reasons:
                    _inspect_xml(text, policy, reasons)
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
                if _edi_segment_too_long(text, policy.max_edi_segment_chars):
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
    """Neutralize formula-leading text for CSV/XLSX export surfaces."""
    if not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if stripped and stripped[0] in {"=", "+", "-", "@"}:
        return "'" + value
    return value
