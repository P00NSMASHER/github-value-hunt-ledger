"""Candidate-only source extractors for historical public-record MNPI research.

Step 7 parsers may propose candidate facts from already-retained public artifacts.
They do not create canonical cases, events, or transactions and cannot approve
their own output.

PDF handling is deliberately text-layer only: callers may supply page text from
a separately recorded parser, but this module does not OCR or pretend to verify
raw PDF visual content.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html.parser import HTMLParser
import csv
import hashlib
import io
import json
import re
import zipfile

from .raw_artifacts import SourceArtifactRef, SourceLocatorKind
from .source_registry import canonical_hash


class CandidateKind(str, Enum):
    TRANSACTION = "TRANSACTION"
    EVENT_BOUNDARY = "EVENT_BOUNDARY"
    PARTY = "PARTY"
    OTHER = "OTHER"


class CandidateFieldStatus(str, Enum):
    EXACT_TEXT_PARSE = "EXACT_TEXT_PARSE"
    AMBIGUOUS = "AMBIGUOUS"
    UNPARSED = "UNPARSED"


@dataclass(frozen=True)
class CandidateField:
    name: str
    raw_value: str
    parsed_value: str | None
    status: CandidateFieldStatus

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "name": self.name,
            "raw_value": self.raw_value,
            "parsed_value": self.parsed_value,
            "status": self.status.value,
        })


@dataclass(frozen=True)
class CandidateRecord:
    candidate_id: str
    extractor_id: str
    extractor_version: str
    kind: CandidateKind
    source_ref: SourceArtifactRef
    case_id: str | None
    fields: tuple[CandidateField, ...]
    raw_excerpt: str
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")
        if not self.extractor_id.strip() or not self.extractor_version.strip():
            raise ValueError("extractor identity/version are required")
        if not self.fields:
            raise ValueError("candidate requires fields")
        if not self.raw_excerpt:
            raise ValueError("candidate requires source excerpt")
        names = [item.name for item in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("candidate contains duplicate field names")

    @property
    def excerpt_sha256(self) -> str:
        return hashlib.sha256(self.raw_excerpt.encode("utf-8")).hexdigest()

    @property
    def proof_hash(self) -> str:
        return canonical_hash({
            "schema": 1,
            "candidate_id": self.candidate_id,
            "extractor_id": self.extractor_id,
            "extractor_version": self.extractor_version,
            "kind": self.kind.value,
            "source_ref_proof_hash": self.source_ref.proof_hash,
            "case_id": self.case_id,
            "field_hashes": [
                item.proof_hash for item in sorted(self.fields, key=lambda x: x.name)
            ],
            "excerpt_sha256": self.excerpt_sha256,
            "warnings": sorted(self.warnings),
        })


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


_DATE_QTY_PRICE_RE = re.compile(
    r"(?P<date>(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}))"
    r"[^\n]{0,80}?"
    r"(?P<quantity>\d[\d,]*)"
    r"[^\n]{0,40}?"
    r"\$?(?P<price>\d+(?:\.\d+)?)"
)


def _ref_at(base: SourceArtifactRef, kind: SourceLocatorKind, locator: str) -> SourceArtifactRef:
    return SourceArtifactRef(
        source_id=base.source_id,
        source_proof_hash=base.source_proof_hash,
        artifact_id=base.artifact_id,
        artifact_sha256=base.artifact_sha256,
        artifact_record_proof_hash=base.artifact_record_proof_hash,
        locator_kind=kind,
        locator=locator,
    )


def _trade_candidates_from_text(
    text: str,
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    extractor_id: str,
    extractor_version: str,
    locator_prefix: str,
    warnings: tuple[str, ...] = (),
) -> tuple[CandidateRecord, ...]:
    out = []
    for index, match in enumerate(_DATE_QTY_PRICE_RE.finditer(text), start=1):
        excerpt = match.group(0).strip()
        ref = _ref_at(
            base_ref,
            SourceLocatorKind.TEXT_RANGE,
            f"{locator_prefix};chars={match.start()}-{match.end()}",
        )
        out.append(CandidateRecord(
            candidate_id=canonical_hash({
                "source": ref.proof_hash,
                "index": index,
                "excerpt": excerpt,
                "extractor": extractor_id,
            }),
            extractor_id=extractor_id,
            extractor_version=extractor_version,
            kind=CandidateKind.TRANSACTION,
            source_ref=ref,
            case_id=case_id,
            fields=(
                CandidateField(
                    "trade_date",
                    match.group("date"),
                    match.group("date"),
                    CandidateFieldStatus.EXACT_TEXT_PARSE,
                ),
                CandidateField(
                    "quantity",
                    match.group("quantity"),
                    match.group("quantity").replace(",", ""),
                    CandidateFieldStatus.EXACT_TEXT_PARSE,
                ),
                CandidateField(
                    "execution_price",
                    match.group("price"),
                    match.group("price"),
                    CandidateFieldStatus.EXACT_TEXT_PARSE,
                ),
            ),
            raw_excerpt=excerpt,
            warnings=warnings,
        ))
    return tuple(out)


def extract_sec_html_candidates(
    raw_html: bytes,
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
) -> tuple[CandidateRecord, ...]:
    parser = _TextExtractor()
    parser.feed(raw_html.decode("utf-8", errors="replace"))
    return _trade_candidates_from_text(
        parser.text(),
        base_ref=base_ref,
        case_id=case_id,
        extractor_id="sec-html-trade-candidate",
        extractor_version="1",
        locator_prefix="html-text",
    )


def extract_sec_pdf_page_text_candidates(
    pages: dict[int, str],
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    parser_identity: str,
) -> tuple[CandidateRecord, ...]:
    if not parser_identity.strip():
        raise ValueError("parser_identity is required for PDF page text")
    out = []
    for page_number in sorted(pages):
        page_text = pages[page_number]
        page_ref = _ref_at(base_ref, SourceLocatorKind.PAGE, f"page={page_number}")
        out.extend(_trade_candidates_from_text(
            page_text,
            base_ref=page_ref,
            case_id=case_id,
            extractor_id="sec-pdf-page-text-trade-candidate",
            extractor_version="1",
            locator_prefix=f"page={page_number}",
            warnings=(
                "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION",
                "TEXT_PARSER=" + parser_identity,
            ),
        ))
    return tuple(out)


def extract_doj_or_court_page_text_candidates(
    pages: dict[int, str],
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    parser_identity: str,
) -> tuple[CandidateRecord, ...]:
    if not parser_identity.strip():
        raise ValueError("parser_identity is required")
    out = []
    for page_number in sorted(pages):
        page_ref = _ref_at(base_ref, SourceLocatorKind.PAGE, f"page={page_number}")
        out.extend(_trade_candidates_from_text(
            pages[page_number],
            base_ref=page_ref,
            case_id=case_id,
            extractor_id="court-doj-page-text-trade-candidate",
            extractor_version="1",
            locator_prefix=f"page={page_number}",
            warnings=(
                "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION",
                "TEXT_PARSER=" + parser_identity,
            ),
        ))
    return tuple(out)


def extract_academic_csv_candidates(
    raw_csv: bytes,
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    field_map: dict[str, str],
    kind: CandidateKind = CandidateKind.OTHER,
    extractor_id: str = "academic-csv-candidate",
) -> tuple[CandidateRecord, ...]:
    text = raw_csv.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV has no header")
    missing = sorted(set(field_map) - set(reader.fieldnames))
    if missing:
        raise ValueError("CSV missing required headers: " + ", ".join(missing))

    out = []
    for row_number, row in enumerate(reader, start=2):
        fields = []
        raw_parts = []
        for source_column, normalized_name in field_map.items():
            raw_value = (row.get(source_column) or "").strip()
            fields.append(CandidateField(
                normalized_name,
                raw_value,
                raw_value if raw_value else None,
                CandidateFieldStatus.EXACT_TEXT_PARSE if raw_value else CandidateFieldStatus.UNPARSED,
            ))
            raw_parts.append(f"{source_column}={raw_value}")
        ref = _ref_at(base_ref, SourceLocatorKind.CSV_ROW, f"row={row_number}")
        excerpt = "; ".join(raw_parts)
        out.append(CandidateRecord(
            candidate_id=canonical_hash({
                "source": ref.proof_hash,
                "row": row_number,
                "extractor": extractor_id,
            }),
            extractor_id=extractor_id,
            extractor_version="1",
            kind=kind,
            source_ref=ref,
            case_id=case_id,
            fields=tuple(fields),
            raw_excerpt=excerpt,
            warnings=("CANDIDATE_ONLY_REQUIRES_REVIEW",),
        ))
    return tuple(out)


def extract_academic_zip_csv_candidates(
    raw_zip: bytes,
    *,
    base_ref: SourceArtifactRef,
    member_name: str,
    case_id: str | None,
    field_map: dict[str, str],
    kind: CandidateKind = CandidateKind.OTHER,
) -> tuple[CandidateRecord, ...]:
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        if member_name not in archive.namelist():
            raise ValueError("archive member not found: " + member_name)
        member_bytes = archive.read(member_name)
    member_ref = _ref_at(
        base_ref,
        SourceLocatorKind.ARCHIVE_MEMBER,
        f"member={member_name}",
    )
    return extract_academic_csv_candidates(
        member_bytes,
        base_ref=member_ref,
        case_id=case_id,
        field_map=field_map,
        kind=kind,
        extractor_id="academic-zip-csv-candidate",
    )


def extract_hacked_earnings_first_trade_candidates(
    raw_csv: bytes,
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None = None,
) -> tuple[CandidateRecord, ...]:
    candidates = extract_academic_csv_candidates(
        raw_csv,
        base_ref=base_ref,
        case_id=case_id,
        field_map={
            "PERMNO": "permno",
            "SYMBOL": "ticker",
            "GVKEY": "gvkey",
            "TimeOfFirstTrade": "time_of_first_trade",
        },
        kind=CandidateKind.TRANSACTION,
        extractor_id="hacked-earnings-time-of-first-trade",
    )
    return tuple(
        CandidateRecord(
            candidate_id=item.candidate_id,
            extractor_id=item.extractor_id,
            extractor_version=item.extractor_version,
            kind=item.kind,
            source_ref=item.source_ref,
            case_id=item.case_id,
            fields=item.fields,
            raw_excerpt=item.raw_excerpt,
            warnings=tuple(sorted(set(item.warnings + (
                "ACADEMIC_RECONSTRUCTION",
                "TIMEZONE_NOT_ENCODED_IN_SOURCE_COLUMN",
                "FIRST_TRADE_TIME_IS_NOT_COMPLETE_TRADE_ECONOMICS",
            )))),
        )
        for item in candidates
    )


__all__ = [
    "CandidateField",
    "CandidateFieldStatus",
    "CandidateKind",
    "CandidateRecord",
    "extract_academic_csv_candidates",
    "extract_academic_zip_csv_candidates",
    "extract_doj_or_court_page_text_candidates",
    "extract_hacked_earnings_first_trade_candidates",
    "extract_sec_html_candidates",
    "extract_sec_pdf_page_text_candidates",
]
