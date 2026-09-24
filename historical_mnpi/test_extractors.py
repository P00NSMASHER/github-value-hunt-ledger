import hashlib
import io
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
from historical_mnpi.raw_artifacts import SourceArtifactRef, SourceLocatorKind


def H(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def ref() -> SourceArtifactRef:
    artifact = H(b"artifact")
    return SourceArtifactRef(
        source_id="SEC:EXTRACT:001",
        source_proof_hash=H(b"source-proof"),
        artifact_id="sha256:" + artifact,
        artifact_sha256=artifact,
        artifact_record_proof_hash=H(b"artifact-proof"),
        locator_kind=SourceLocatorKind.PAGE,
        locator="page=1",
    )


class ExtractorTests(unittest.TestCase):
    def test_sec_html_emits_candidate_not_canonical_transaction(self):
        html = b"<table><tr><td>08/10/2015</td><td>2,500 shares</td><td>$30.375</td></tr></table>"
        rows = extract_sec_html_candidates(
            html,
            base_ref=ref(),
            case_id="CASE-1",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kind, CandidateKind.TRANSACTION)
        values = {item.name: item.parsed_value for item in rows[0].fields}
        self.assertEqual(values["quantity"], "2500")
        self.assertEqual(values["execution_price"], "30.375")
        self.assertEqual(len(rows[0].proof_hash), 64)

    def test_pdf_page_text_keeps_parser_warning(self):
        rows = extract_sec_pdf_page_text_candidates(
            {17: "2015-08-10 purchased 164 calls at $0.35"},
            base_ref=ref(),
            case_id="CASE-1",
            parser_identity="pypdf-test-v1",
        )
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION",
            rows[0].warnings,
        )
        self.assertIn("TEXT_PARSER=pypdf-test-v1", rows[0].warnings)

    def test_doj_court_adapter_is_deterministic(self):
        args = dict(
            pages={3: "2015-08-10 bought 5,000 shares at $12.50"},
            base_ref=ref(),
            case_id="CASE-2",
            parser_identity="court-text-v1",
        )
        left = extract_doj_or_court_page_text_candidates(**args)
        right = extract_doj_or_court_page_text_candidates(**args)
        self.assertEqual(left[0].proof_hash, right[0].proof_hash)

    def test_academic_csv_requires_declared_headers(self):
        with self.assertRaisesRegex(ValueError, "missing required headers"):
            extract_academic_csv_candidates(
                b"A,B\n1,2\n",
                base_ref=ref(),
                case_id=None,
                field_map={"C": "field_c"},
            )

    def test_academic_zip_binds_member_locator(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("data/trades.csv", "Date,Qty\n2015-08-10,100\n")
        rows = extract_academic_zip_csv_candidates(
            buf.getvalue(),
            base_ref=ref(),
            member_name="data/trades.csv",
            case_id=None,
            field_map={"Date": "trade_date", "Qty": "quantity"},
            kind=CandidateKind.TRANSACTION,
        )
        self.assertEqual(len(rows), 1)
        self.assertIn("member=data/trades.csv", rows[0].source_ref.locator)

    def test_hacked_earnings_adapter_matches_real_public_headers(self):
        raw = (
            b"PERMNO,SYMBOL,GVKEY,TimeOfFirstTrade\n"
            b"10145,HON,1300,2012-01-26 15:53:00\n"
        )
        rows = extract_hacked_earnings_first_trade_candidates(
            raw,
            base_ref=ref(),
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
        rows = extract_academic_csv_candidates(
            b"Date,Qty\n2015-08-10,\n",
            base_ref=ref(),
            case_id=None,
            field_map={"Date": "trade_date", "Qty": "quantity"},
            kind=CandidateKind.TRANSACTION,
        )
        fields = {item.name: item for item in rows[0].fields}
        self.assertEqual(fields["quantity"].status, CandidateFieldStatus.UNPARSED)
        self.assertIsNone(fields["quantity"].parsed_value)


if __name__ == "__main__":
    unittest.main()
