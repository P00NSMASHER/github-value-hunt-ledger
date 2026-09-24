"""Candidate-only source extractors for historical public-record MNPI research.

Step 7 may propose candidate facts from already-retained public artifacts.
Nothing emitted here is a canonical case, event, transaction, or legal finding.

Every extractor re-verifies:
- the Step-1 registered source proof;
- the Step-2 retained-artifact proof;
- the exact raw-byte SHA-256;
- the source family expected by that extractor.

PDF handling is intentionally conservative. Raw PDFs are not OCRed here.
Callers may supply page text from a separately identified parser, and every
result from that path remains HUMAN_REQUIRED for Step-8 review.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html.parser import HTMLParser
import csv
import hashlib
import io
import re
import zipfile

from .raw_artifacts import (
    RawArtifactManifest,
    RawArtifactRecord,
    SourceArtifactRef,
    SourceLocatorKind,
)
from .source_registry import SourceRegistry, SourceType, canonical_hash


_MAX_EXCERPT_CHARS = 500
_MAX_FIELD_CHARS = 10_000
_MAX_TEXT_CHARS = 5_000_000
_MAX_CSV_ROWS = 100_000
_MAX_ZIP_MEMBER_BYTES = 50_000_000

_SEC_TYPES = frozenset({
    SourceType.SEC_COMPLAINT,
    SourceType.SEC_LITIGATION_RELEASE,
    SourceType.SEC_ADMIN_ORDER,
    SourceType.PUBLIC_FILING,
})
_DOJ_COURT_TYPES = frozenset({
    SourceType.DOJ_INDICTMENT,
    SourceType.DOJ_PLEA_OR_STATEMENT,
    SourceType.COURT_JUDGMENT,
    SourceType.COURT_EXHIBIT,
    SourceType.FOIA_PUBLIC_RELEASE,
})


class CandidateKind(str, Enum):
    TRANSACTION = "TRANSACTION"
    EVENT_BOUNDARY = "EVENT_BOUNDARY"
    STATUS = "STATUS"
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

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("candidate field name is required")
        if len(self.raw_value) > _MAX_FIELD_CHARS:
            raise ValueError("candidate raw_value exceeds limit")
        if self.parsed_value is not None and len(self.parsed_value) > _MAX_FIELD_CHARS:
            raise ValueError("candidate parsed_value exceeds limit")

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
        if len(self.raw_excerpt) > _MAX_EXCERPT_CHARS:
            raise ValueError("candidate source excerpt exceeds review limit")
        names = [item.name for item in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("candidate contains duplicate field names")
        if len(set(self.warnings)) != len(self.warnings):
            raise ValueError("candidate contains duplicate warnings")

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


def _verify_input(
    raw_bytes: bytes,
    *,
    base_ref: SourceArtifactRef,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
    allowed_source_types: frozenset[SourceType],
) -> tuple[object, RawArtifactRecord]:
    if not isinstance(raw_bytes, bytes):
        raise TypeError("raw source input must be bytes")
    if artifact_manifest.source_registry_hash != source_registry.registry_hash:
        raise ValueError("artifact manifest/source registry mismatch")

    source = source_registry.get(base_ref.source_id)
    if source.source_type not in allowed_source_types:
        raise ValueError(
            "extractor source type mismatch: " + source.source_type.value
        )
    if source.proof_hash != base_ref.source_proof_hash:
        raise ValueError("extractor source proof mismatch")

    artifact = artifact_manifest.resolve_ref(base_ref)
    if artifact.proof_hash != base_ref.artifact_record_proof_hash:
        raise ValueError("extractor artifact proof mismatch")
    if hashlib.sha256(raw_bytes).hexdigest() != artifact.sha256:
        raise ValueError("extractor bytes do not match retained artifact")
    return source, artifact


def _ref_at(
    base: SourceArtifactRef,
    kind: SourceLocatorKind,
    locator: str,
    *,
    excerpt: str,
) -> SourceArtifactRef:
    combined_locator = (
        f"{base.locator};{locator}"
        if base.locator and base.locator != locator
        else locator
    )
    return SourceArtifactRef(
        source_id=base.source_id,
        source_proof_hash=base.source_proof_hash,
        artifact_id=base.artifact_id,
        artifact_sha256=base.artifact_sha256,
        artifact_record_proof_hash=base.artifact_record_proof_hash,
        locator_kind=kind,
        locator=combined_locator,
        excerpt_sha256=hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
    )


_DATE = r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})"
_TABLE_TRADE_RE = re.compile(
    rf"^\s*(?P<date>{_DATE})\s*[,|\t]\s*"
    r"(?P<quantity>[0-9][0-9,]*)\s*(?:shares?|calls?|puts?|contracts?)?\s*"
    r"[,|\t]\s*\$?(?P<price>[0-9]+(?:\.[0-9]+)?)\s*$",
    re.IGNORECASE,
)
_NARRATIVE_TRADE_RE = re.compile(
    rf"(?P<date>{_DATE}).{{0,100}}?"
    r"(?P<quantity>[0-9][0-9,]*)\s+"
    r"(?P<instrument>shares?|calls?|puts?|contracts?)"
    r".{0,60}?\bat\s+\$?(?P<price>[0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
_STATUS_PATTERNS = (
    ("pleaded guilty", "GUILTY_PLEA_LANGUAGE"),
    ("was convicted", "CONVICTION_LANGUAGE"),
    ("found liable", "LIABILITY_LANGUAGE"),
    ("final judgment", "FINAL_JUDGMENT_LANGUAGE"),
    ("without admitting or denying", "NO_ADMISSION_SETTLEMENT_LANGUAGE"),
)
_PUBLIC_RELEASE_RE = re.compile(
    rf"(?P<label>public(?:ly)?\s+(?:released|announced)|public\s+release)"
    rf".{{0,80}}?(?P<date>{_DATE})"
    r"(?:.{0,30}?(?P<time>\d{1,2}:\d{2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?))?",
    re.IGNORECASE,
)


def _candidate(
    *,
    kind: CandidateKind,
    extractor_id: str,
    source_ref: SourceArtifactRef,
    case_id: str | None,
    fields: tuple[CandidateField, ...],
    excerpt: str,
    warnings: tuple[str, ...],
    identity_extra: object,
) -> CandidateRecord:
    excerpt = excerpt.strip()[:_MAX_EXCERPT_CHARS]
    return CandidateRecord(
        candidate_id=canonical_hash({
            "schema": 1,
            "source_ref": source_ref.proof_hash,
            "extractor": extractor_id,
            "fields": [field.proof_hash for field in fields],
            "extra": identity_extra,
        }),
        extractor_id=extractor_id,
        extractor_version="2",
        kind=kind,
        source_ref=source_ref,
        case_id=case_id,
        fields=fields,
        raw_excerpt=excerpt,
        warnings=warnings,
    )


def _candidates_from_lines(
    lines: list[tuple[str, SourceArtifactRef, bool]],
    *,
    case_id: str | None,
    extractor_id: str,
) -> tuple[CandidateRecord, ...]:
    out: list[CandidateRecord] = []
    for index, (line, ref, human_required) in enumerate(lines, start=1):
        excerpt = line.strip()[:_MAX_EXCERPT_CHARS]
        if not excerpt:
            continue

        match = _TABLE_TRADE_RE.match(line)
        status = (
            CandidateFieldStatus.AMBIGUOUS
            if human_required
            else CandidateFieldStatus.EXACT_TEXT_PARSE
        )
        warnings: tuple[str, ...] = (
            ("HUMAN_SEMANTIC_CONFIRMATION_REQUIRED",)
            if human_required else ()
        )
        if match is not None:
            fields = (
                CandidateField("trade_date", match.group("date"), match.group("date"), status),
                CandidateField(
                    "quantity",
                    match.group("quantity"),
                    match.group("quantity").replace(",", ""),
                    status,
                ),
                CandidateField("execution_price", match.group("price"), match.group("price"), status),
            )
            out.append(_candidate(
                kind=CandidateKind.TRANSACTION,
                extractor_id=extractor_id,
                source_ref=ref,
                case_id=case_id,
                fields=fields,
                excerpt=excerpt,
                warnings=warnings,
                identity_extra=index,
            ))
        else:
            narrative = _NARRATIVE_TRADE_RE.search(line)
            if narrative is not None:
                fields = (
                    CandidateField(
                        "trade_date",
                        narrative.group("date"),
                        narrative.group("date"),
                        CandidateFieldStatus.AMBIGUOUS,
                    ),
                    CandidateField(
                        "quantity",
                        narrative.group("quantity"),
                        narrative.group("quantity").replace(",", ""),
                        CandidateFieldStatus.AMBIGUOUS,
                    ),
                    CandidateField(
                        "instrument_text",
                        narrative.group("instrument"),
                        narrative.group("instrument").lower(),
                        CandidateFieldStatus.AMBIGUOUS,
                    ),
                    CandidateField(
                        "execution_price",
                        narrative.group("price"),
                        narrative.group("price"),
                        CandidateFieldStatus.AMBIGUOUS,
                    ),
                )
                out.append(_candidate(
                    kind=CandidateKind.TRANSACTION,
                    extractor_id=extractor_id,
                    source_ref=ref,
                    case_id=case_id,
                    fields=fields,
                    excerpt=excerpt,
                    warnings=("NARRATIVE_PATTERN_REQUIRES_HUMAN_CONFIRMATION",),
                    identity_extra=("narrative", index),
                ))

        lowered = line.casefold()
        for phrase, label in _STATUS_PATTERNS:
            if phrase in lowered:
                fields = (
                    CandidateField(
                        "status_phrase",
                        phrase,
                        label,
                        CandidateFieldStatus.AMBIGUOUS,
                    ),
                )
                out.append(_candidate(
                    kind=CandidateKind.STATUS,
                    extractor_id=extractor_id,
                    source_ref=ref,
                    case_id=case_id,
                    fields=fields,
                    excerpt=excerpt,
                    warnings=("LEGAL_STATUS_REQUIRES_HUMAN_CONFIRMATION",),
                    identity_extra=("status", index, label),
                ))

        public = _PUBLIC_RELEASE_RE.search(line)
        if public is not None:
            fields = [
                CandidateField(
                    "public_release_date",
                    public.group("date"),
                    public.group("date"),
                    CandidateFieldStatus.AMBIGUOUS,
                )
            ]
            if public.group("time"):
                fields.append(CandidateField(
                    "public_release_time",
                    public.group("time"),
                    public.group("time"),
                    CandidateFieldStatus.AMBIGUOUS,
                ))
            out.append(_candidate(
                kind=CandidateKind.EVENT_BOUNDARY,
                extractor_id=extractor_id,
                source_ref=ref,
                case_id=case_id,
                fields=tuple(fields),
                excerpt=excerpt,
                warnings=("PUBLIC_RELEASE_BOUNDARY_REQUIRES_HUMAN_CONFIRMATION",),
                identity_extra=("public-release", index),
            ))

    return tuple(out)


def extract_sec_html_candidates(
    raw_html: bytes,
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> tuple[CandidateRecord, ...]:
    _source, artifact = _verify_input(
        raw_html,
        base_ref=base_ref,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
        allowed_source_types=_SEC_TYPES,
    )
    if artifact.media_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
        raise ValueError("SEC HTML extractor requires retained HTML/text artifact")
    parser = _TextExtractor()
    parser.feed(raw_html.decode("utf-8", errors="strict"))
    text = parser.text()
    if len(text) > _MAX_TEXT_CHARS:
        raise ValueError("SEC text exceeds extractor limit")
    lines = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        excerpt = line.strip()[:_MAX_EXCERPT_CHARS]
        ref = _ref_at(
            base_ref,
            SourceLocatorKind.TEXT_RANGE,
            f"line={line_no}",
            excerpt=excerpt,
        )
        lines.append((line, ref, False))
    return _candidates_from_lines(
        lines,
        case_id=case_id,
        extractor_id="sec-html-candidate",
    )


def extract_sec_pdf_page_text_candidates(
    raw_pdf: bytes,
    pages: dict[int, str],
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    parser_identity: str,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> tuple[CandidateRecord, ...]:
    _source, artifact = _verify_input(
        raw_pdf,
        base_ref=base_ref,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
        allowed_source_types=_SEC_TYPES,
    )
    if artifact.media_type != "application/pdf":
        raise ValueError("SEC PDF extractor requires retained application/pdf artifact")
    if not parser_identity.strip():
        raise ValueError("parser_identity is required for PDF page text")
    lines = []
    for page_number in sorted(pages):
        if type(page_number) is not int or page_number < 1:
            raise ValueError("PDF page numbers must be positive integers")
        page_text = pages[page_number]
        if not isinstance(page_text, str):
            raise TypeError("PDF page text must be string")
        for line_no, line in enumerate(page_text.splitlines(), start=1):
            excerpt = line.strip()[:_MAX_EXCERPT_CHARS]
            ref = _ref_at(
                base_ref,
                SourceLocatorKind.PAGE,
                f"page={page_number};line={line_no}",
                excerpt=excerpt,
            )
            lines.append((line, ref, True))
    candidates = _candidates_from_lines(
        lines,
        case_id=case_id,
        extractor_id="sec-pdf-page-text-candidate",
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
                "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION",
                "TEXT_PARSER=" + parser_identity,
            )))),
        )
        for item in candidates
    )


def extract_doj_or_court_page_text_candidates(
    raw_pdf: bytes,
    pages: dict[int, str],
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    parser_identity: str,
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
) -> tuple[CandidateRecord, ...]:
    _source, artifact = _verify_input(
        raw_pdf,
        base_ref=base_ref,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
        allowed_source_types=_DOJ_COURT_TYPES,
    )
    if artifact.media_type != "application/pdf":
        raise ValueError("DOJ/court PDF extractor requires application/pdf artifact")
    if not parser_identity.strip():
        raise ValueError("parser_identity is required")
    lines = []
    for page_number in sorted(pages):
        if type(page_number) is not int or page_number < 1:
            raise ValueError("page numbers must be positive integers")
        page_text = pages[page_number]
        for line_no, line in enumerate(page_text.splitlines(), start=1):
            excerpt = line.strip()[:_MAX_EXCERPT_CHARS]
            ref = _ref_at(
                base_ref,
                SourceLocatorKind.PAGE,
                f"page={page_number};line={line_no}",
                excerpt=excerpt,
            )
            lines.append((line, ref, True))
    candidates = _candidates_from_lines(
        lines,
        case_id=case_id,
        extractor_id="court-doj-page-text-candidate",
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
                "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION",
                "TEXT_PARSER=" + parser_identity,
            )))),
        )
        for item in candidates
    )


def _academic_csv_candidates_unverified_member(
    raw_csv: bytes,
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    field_map: dict[str, str],
    kind: CandidateKind,
    extractor_id: str,
) -> tuple[CandidateRecord, ...]:
    try:
        text = raw_csv.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("academic CSV must be UTF-8/UTF-8-SIG") from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV has no header")
    missing = sorted(set(field_map) - set(reader.fieldnames))
    if missing:
        raise ValueError("CSV missing required headers: " + ", ".join(missing))

    out = []
    for row_number, row in enumerate(reader, start=2):
        if row_number - 1 > _MAX_CSV_ROWS:
            raise ValueError("academic CSV exceeds row limit")
        fields = []
        raw_parts = []
        for source_column, normalized_name in field_map.items():
            raw_value = (row.get(source_column) or "").strip()
            if len(raw_value) > _MAX_FIELD_CHARS:
                raise ValueError("academic CSV field exceeds size limit")
            fields.append(CandidateField(
                normalized_name,
                raw_value,
                raw_value if raw_value else None,
                CandidateFieldStatus.EXACT_TEXT_PARSE
                if raw_value else CandidateFieldStatus.UNPARSED,
            ))
            raw_parts.append(f"{source_column}={raw_value}")
        excerpt = "; ".join(raw_parts)[:_MAX_EXCERPT_CHARS]
        ref = _ref_at(
            base_ref,
            SourceLocatorKind.CSV_ROW,
            f"row={row_number}",
            excerpt=excerpt,
        )
        out.append(_candidate(
            kind=kind,
            extractor_id=extractor_id,
            source_ref=ref,
            case_id=case_id,
            fields=tuple(fields),
            excerpt=excerpt,
            warnings=("CANDIDATE_ONLY_REQUIRES_REVIEW",),
            identity_extra=row_number,
        ))
    return tuple(out)


def extract_academic_csv_candidates(
    raw_csv: bytes,
    *,
    base_ref: SourceArtifactRef,
    case_id: str | None,
    field_map: dict[str, str],
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
    kind: CandidateKind = CandidateKind.OTHER,
    extractor_id: str = "academic-csv-candidate",
) -> tuple[CandidateRecord, ...]:
    _source, artifact = _verify_input(
        raw_csv,
        base_ref=base_ref,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
        allowed_source_types=frozenset({SourceType.ACADEMIC_REPLICATION}),
    )
    if artifact.media_type not in {"text/csv", "application/csv", "text/plain"}:
        raise ValueError("academic CSV extractor requires retained CSV/text artifact")
    return _academic_csv_candidates_unverified_member(
        raw_csv,
        base_ref=base_ref,
        case_id=case_id,
        field_map=field_map,
        kind=kind,
        extractor_id=extractor_id,
    )


def extract_academic_zip_csv_candidates(
    raw_zip: bytes,
    *,
    base_ref: SourceArtifactRef,
    member_name: str,
    case_id: str | None,
    field_map: dict[str, str],
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
    kind: CandidateKind = CandidateKind.OTHER,
) -> tuple[CandidateRecord, ...]:
    _source, artifact = _verify_input(
        raw_zip,
        base_ref=base_ref,
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
        allowed_source_types=frozenset({SourceType.ACADEMIC_REPLICATION}),
    )
    if artifact.media_type not in {"application/zip", "application/x-zip-compressed"}:
        raise ValueError("academic ZIP extractor requires retained ZIP artifact")
    normalized = member_name.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if normalized.startswith("/") or ".." in parts:
        raise ValueError("archive member path traversal is not allowed")

    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        try:
            info = archive.getinfo(member_name)
        except KeyError as exc:
            raise ValueError("archive member not found: " + member_name) from exc
        if info.flag_bits & 0x1:
            raise ValueError("encrypted archive members are not accepted")
        if info.file_size > _MAX_ZIP_MEMBER_BYTES:
            raise ValueError("archive member exceeds extraction size limit")
        member_bytes = archive.read(info)

    excerpt = normalized[:_MAX_EXCERPT_CHARS]
    member_ref = _ref_at(
        base_ref,
        SourceLocatorKind.ARCHIVE_MEMBER,
        f"member={normalized}",
        excerpt=excerpt,
    )
    return _academic_csv_candidates_unverified_member(
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
    source_registry: SourceRegistry,
    artifact_manifest: RawArtifactManifest,
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
        source_registry=source_registry,
        artifact_manifest=artifact_manifest,
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
