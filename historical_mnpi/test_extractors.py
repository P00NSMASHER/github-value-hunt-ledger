import hashlib
import io
import tempfile
import unittest
import zipfile

from historical_mnpi.extractors import (
    CandidateFieldStatus,
    CandidateKind,
    extract_academic_csv_candidates,
    extract_academic_zip_csv_candidates,
    extract_doj_or_court_page_text_candidates,
    extract_hacked_earnings_first_trade_candidates,
    extract_sec_html_candidates,
    extract_sec_pdf_page_text_candidates,
)
from historical_mnpi.raw_artifacts import (
    LocalContentAddressedArtifactStore,
    SourceArtifactRef,
    SourceLocatorKind,
    freeze_raw_artifact_manifest,
)
from historical_mnpi.source_registry import (
    SourceAdmissibility,
    SourceRecord,
    SourceRegistry,
    SourceType,
)


def H(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def retained(
    raw: bytes,
    *,
    source_type: SourceType,
    admissibility: SourceAdmissibility,
    media_type: str,
    source_id: str = "SRC:EXTRACT:001",
):
    source = SourceRecord(
        source_id=source_id,
        source_type=source_type,
        admissibility=admissibility,
        publisher="Public publisher",
        title="Historical public source",
        url="https://example.org/historical-source",
        publication_date="2015-08-11",
        sha256=H(raw),
        retrieved_at="2026-09-24T12:30:00Z",
        public_release_confirmed=True,
        case_id="CASE-1",
    )
    registry = SourceRegistry()
    registry.register(source)

    with tempfile.TemporaryDirectory() as root:
        store = LocalContentAddressedArtifactStore(root)
        artifact = store.retain(
            registry,
            source,
            raw,
            media_type=media_type,
            acquired_at="2026-09-24T12:30:00Z",
            stored_at="2026-09-24T12:31:00Z",
        )
        manifest = freeze_raw_artifact_manifest(
            registry,
            (artifact,),
            created_at="2026-09-24T12:32:00Z",
            created_by="test",
        )

    ref = SourceArtifactRef(
        source_id=source.source_id,
        source_proof_hash=source.proof_hash,
        artifact_id=artifact.artifact_id,
        artifact_sha256=artifact.sha256,
        artifact_record_proof_hash=artifact.proof_hash,
        locator_kind=SourceLocatorKind.OTHER,
        locator="document-root",
    )
    return source, registry, manifest, ref


class ExtractorTests(unittest.TestCase):
    def test_sec_html_emits_candidate_not_canonical_transaction(self):
        raw = (
            b"<table><tr><td>08/10/2015 | 2,500 shares | $30.375</td>"
            b"</tr></table>"
        )
        source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.SEC_COMPLAINT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            media_type="text/html",
        )
        rows = extract_sec_html_candidates(
            raw,
            base_ref=ref,
            case_id="CASE-1",
            source_registry=registry,
            artifact_manifest=manifest,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kind, CandidateKind.TRANSACTION)
        values = {item.name: item.parsed_value for item in rows[0].fields}
        self.assertEqual(values["quantity"], "2500")
        self.assertEqual(values["execution_price"], "30.375")
        self.assertEqual(len(rows[0].proof_hash), 64)

    def test_sec_html_rejects_bytes_not_matching_retained_artifact(self):
        raw = b"<p>08/10/2015 | 100 shares | $1.25</p>"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.SEC_COMPLAINT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            media_type="text/html",
        )
        with self.assertRaisesRegex(ValueError, "do not match retained artifact"):
            extract_sec_html_candidates(
                raw + b"tamper",
                base_ref=ref,
                case_id="CASE-1",
                source_registry=registry,
                artifact_manifest=manifest,
            )

    def test_sec_extractor_rejects_wrong_source_family(self):
        raw = b"<p>08/10/2015 | 100 shares | $1.25</p>"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.ACADEMIC_REPLICATION,
            admissibility=SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
            media_type="text/html",
        )
        with self.assertRaisesRegex(ValueError, "source type mismatch"):
            extract_sec_html_candidates(
                raw,
                base_ref=ref,
                case_id="CASE-1",
                source_registry=registry,
                artifact_manifest=manifest,
            )

    def test_pdf_page_text_keeps_parser_and_human_review_warning(self):
        raw = b"%PDF-1.7 historical public fixture"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.SEC_COMPLAINT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            media_type="application/pdf",
        )
        rows = extract_sec_pdf_page_text_candidates(
            raw,
            {17: "2015-08-10 purchased 164 calls at $0.35"},
            base_ref=ref,
            case_id="CASE-1",
            parser_identity="pypdf-test-v1",
            source_registry=registry,
            artifact_manifest=manifest,
        )
        self.assertEqual(len(rows), 1)
        self.assertTrue(all(
            field.status is CandidateFieldStatus.AMBIGUOUS
            for field in rows[0].fields
        ))
        self.assertIn(
            "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION",
            rows[0].warnings,
        )
        self.assertIn("TEXT_PARSER=pypdf-test-v1", rows[0].warnings)

    def test_doj_court_adapter_requires_doj_or_court_source(self):
        raw = b"%PDF-1.7 historical court fixture"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.COURT_EXHIBIT,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            media_type="application/pdf",
        )
        args = dict(
            raw_pdf=raw,
            pages={3: "2015-08-10 bought 5,000 shares at $12.50"},
            base_ref=ref,
            case_id="CASE-2",
            parser_identity="court-text-v1",
            source_registry=registry,
            artifact_manifest=manifest,
        )
        left = extract_doj_or_court_page_text_candidates(**args)
        right = extract_doj_or_court_page_text_candidates(**args)
        self.assertEqual(left[0].proof_hash, right[0].proof_hash)

    def test_status_language_is_candidate_only(self):
        raw = b"<p>The defendant was convicted after trial.</p>"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.SEC_LITIGATION_RELEASE,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            media_type="text/html",
        )
        rows = extract_sec_html_candidates(
            raw,
            base_ref=ref,
            case_id="CASE-1",
            source_registry=registry,
            artifact_manifest=manifest,
        )
        status = [item for item in rows if item.kind is CandidateKind.STATUS]
        self.assertEqual(len(status), 1)
        self.assertIn(
            "LEGAL_STATUS_REQUIRES_HUMAN_CONFIRMATION",
            status[0].warnings,
        )

    def test_public_release_language_is_event_candidate_only(self):
        raw = b"<p>Publicly announced on 08/10/2015 at 4:03 p.m.</p>"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.SEC_LITIGATION_RELEASE,
            admissibility=SourceAdmissibility.PRIMARY_PUBLIC_RECORD,
            media_type="text/html",
        )
        rows = extract_sec_html_candidates(
            raw,
            base_ref=ref,
            case_id="CASE-1",
            source_registry=registry,
            artifact_manifest=manifest,
        )
        boundaries = [
            item for item in rows
            if item.kind is CandidateKind.EVENT_BOUNDARY
        ]
        self.assertEqual(len(boundaries), 1)
        self.assertIn(
            "PUBLIC_RELEASE_BOUNDARY_REQUIRES_HUMAN_CONFIRMATION",
            boundaries[0].warnings,
        )

    def test_academic_csv_requires_declared_headers_and_registered_bytes(self):
        raw = b"A,B\n1,2\n"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.ACADEMIC_REPLICATION,
            admissibility=SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
            media_type="text/csv",
        )
        with self.assertRaisesRegex(ValueError, "missing required headers"):
            extract_academic_csv_candidates(
                raw,
                base_ref=ref,
                case_id=None,
                field_map={"C": "field_c"},
                source_registry=registry,
                artifact_manifest=manifest,
            )

    def test_academic_zip_binds_member_locator_and_rejects_traversal(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("data/trades.csv", "Date,Qty\n2015-08-10,100\n")
        raw = buf.getvalue()
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.ACADEMIC_REPLICATION,
            admissibility=SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
            media_type="application/zip",
        )
        rows = extract_academic_zip_csv_candidates(
            raw,
            base_ref=ref,
            member_name="data/trades.csv",
            case_id=None,
            field_map={"Date": "trade_date", "Qty": "quantity"},
            source_registry=registry,
            artifact_manifest=manifest,
            kind=CandidateKind.TRANSACTION,
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("member=data/trades.csv", rows[0].source_ref.locator)

        with self.assertRaisesRegex(ValueError, "path traversal"):
            extract_academic_zip_csv_candidates(
                raw,
                base_ref=ref,
                member_name="../data/trades.csv",
                case_id=None,
                field_map={"Date": "trade_date", "Qty": "quantity"},
                source_registry=registry,
                artifact_manifest=manifest,
                kind=CandidateKind.TRANSACTION,
            )

    def test_hacked_earnings_adapter_matches_real_public_headers(self):
        raw = (
            b"PERMNO,SYMBOL,GVKEY,TimeOfFirstTrade\n"
            b"10145,HON,1300,2012-01-26 15:53:00\n"
        )
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.ACADEMIC_REPLICATION,
            admissibility=SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
            media_type="text/csv",
        )
        rows = extract_hacked_earnings_first_trade_candidates(
            raw,
            base_ref=ref,
            source_registry=registry,
            artifact_manifest=manifest,
        )
        self.assertEqual(len(rows), 1)
        values = {item.name: item.parsed_value for item in rows[0].fields}
        self.assertEqual(values["permno"], "10145")
        self.assertEqual(values["ticker"], "HON")
        self.assertEqual(values["gvkey"], "1300")
        self.assertEqual(values["time_of_first_trade"], "2012-01-26 15:53:00")
        self.assertIn("ACADEMIC_RECONSTRUCTION", rows[0].warnings)
        self.assertIn("TIMEZONE_NOT_ENCODED_IN_SOURCE_COLUMN", rows[0].warnings)
        self.assertIn(
            "FIRST_TRADE_TIME_IS_NOT_COMPLETE_TRADE_ECONOMICS",
            rows[0].warnings,
        )

    def test_blank_academic_field_remains_unparsed(self):
        raw = b"Date,Qty\n2015-08-10,\n"
        _source, registry, manifest, ref = retained(
            raw,
            source_type=SourceType.ACADEMIC_REPLICATION,
            admissibility=SourceAdmissibility.PUBLISHED_RESEARCH_RECONSTRUCTION,
            media_type="text/csv",
        )
        rows = extract_academic_csv_candidates(
            raw,
            base_ref=ref,
            case_id=None,
            field_map={"Date": "trade_date", "Qty": "quantity"},
            source_registry=registry,
            artifact_manifest=manifest,
            kind=CandidateKind.TRANSACTION,
        )
        fields = {item.name: item for item in rows[0].fields}
        self.assertEqual(fields["quantity"].status, CandidateFieldStatus.UNPARSED)
        self.assertIsNone(fields["quantity"].parsed_value)


if __name__ == "__main__":
    unittest.main()
