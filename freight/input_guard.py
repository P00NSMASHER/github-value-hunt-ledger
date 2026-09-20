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
    allowed_extensions: tuple[str, ...] = (".pdf", ".csv", ".xml", ".edi", ".x12")

    def __post_init__(self):
        if self.max_file_bytes <= 0:
            raise ValueError("max_file_bytes must be positive")
        if self.max_text_line_chars <= 0:
            raise ValueError("max_text_line_chars must be positive")
        if self.max_edi_segment_chars <= 0:
            raise ValueError("max_edi_segment_chars must be positive")


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
                if any(len(line) > policy.max_text_line_chars for line in text.splitlines()):
                    reasons.append("text_line_too_long")
            elif ext == ".csv":
                text = _decode_text(data)
                if "\x00" in text:
                    reasons.append("nul_byte_rejected")
                if any(len(line) > policy.max_text_line_chars for line in text.splitlines()):
                    reasons.append("text_line_too_long")
                # Parse once to reject malformed UTF-8/CSV without executing formulas.
                list(csv.reader(io.StringIO(text)))
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
