"""Mission 19: independent synthetic tests of original Census AIES source guards.

Synthetic bytes are NEVER represented as original Census archives.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
from html import escape
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from freight.research_evidence_gate import canon_hash
from freight.research_ltl_revenue_bridge import RECORDS
from freight import research_aies_original_ftp as m19

TODAY = date(2026, 10, 11)
LABELS = {
    "484": "Truck transportation",
    "484121": "General freight trucking, long-distance, truckload",
    "484122": "General freight trucking, long-distance, less than truckload",
}


def sample(code: str) -> dict:
    return {
        "#GEOTYPE": "01", "ST": "00", "GEO_ID": "0100000US",
        "GEO_LABEL": "United States", "GEO_ID_F": "", "SECTOR": "48",
        "INDLEVEL": str(len(code)), "NAICS2017": code,
        "NAICS2017_LABEL": LABELS[code], "NAICS2017_F": "",
        "TYPOP": "00", "TYPOP_LABEL": "All establishments",
        "TAXSTAT": "00", "TAXSTAT_LABEL": "All establishments",
        "YEAR": "2024",
        "RCPT_TOT_VAL": str(RECORDS[code]["values"][2]),
        "RCPT_TOT_VAL_F": "",
        "RCPT_TOT_CV": ".9", "RCPT_TOT_CV_F": "",
    }


def samples() -> list[dict]:
    return [sample(x) for x in ("484", "484121", "484122")]


def values() -> dict[str, int]:
    return {code: meta["values"][2] for code, meta in RECORDS.items()}


def fabricated_original(rows: list[dict] | None = None,
                        *, bad_member: bool = False) -> tuple[bytes, bytes]:
    if rows is None:
        rows = samples()
    output = io.StringIO(newline="")
    columns = m19.SCHEMA.split("|")
    writer = csv.DictWriter(output, fieldnames=columns, delimiter="|",
                            extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    dat = output.getvalue().encode("utf-8")
    out = io.BytesIO()
    with ZipFile(out, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.writestr("../tampered.dat" if bad_member else m19.MEMBER_DAT, dat)
        bundle.writestr(m19.MEMBER_FIELDS, b"Field_Name|Label|Field_Type\n")
        bundle.writestr(m19.MEMBER_README, b"Test data only\n")
    return out.getvalue(), dat


def parse_fake_source(raw: bytes, dat: bytes):
    """Patch only synthetic unit-test fingerprints, never mission code on CI."""
    with patch.object(m19, "ZIP_SIZE_BYTES", len(raw)), \
         patch.object(m19, "ZIP_SHA256", sha256(raw).hexdigest()), \
         patch.object(m19, "DATA_SIZE_BYTES", len(dat)), \
         patch.object(m19, "DATA_ROW_COUNT", 3):
        return m19.verify_original_bytes(raw, as_of=TODAY)


class AiesOriginalSourceTests(unittest.TestCase):
    def test_original_source_fingerprint_is_fixed_and_specific(self):
        self.assertEqual(m19.SOURCE_URL,
                         "https://www2.census.gov/programs-surveys/aies/data/2024/AIES00BASIC.zip")
        self.assertEqual(len(m19.ZIP_SHA256), 64)
        self.assertEqual(m19.ZIP_SIZE_BYTES, 340551)
        self.assertEqual(m19.DATA_SIZE_BYTES, 1859064)
        self.assertEqual(m19.DATA_ROW_COUNT, 8802)
        self.assertEqual(len(m19.SCHEMA.split("|")), 35)

    def test_frozen_prior_revenue_lineage_and_three_naics_exact_values(self):
        reference, frozen = m19._base(as_of=TODAY)
        self.assertEqual(frozen, {
            "484": 402827246, "484121": 161329027, "484122": 65096292,
        })
        self.assertEqual(reference["ltl_2024_revenue_billion_usd"], "65.096")
        self.assertIsNone(reference["ltl_freight_audit_recoverable_tam_usd"])

    def test_exact_population_values_cv_and_all_three_members(self):
        result = m19.selected_revenue(samples(), expected=values())
        self.assertEqual([x["naics2017"] for x in result], ["484", "484121", "484122"])
        self.assertEqual([x["revenue_thousand_usd"] for x in result],
                         [402827246, 161329027, 65096292])
        self.assertTrue(all(x["published_flags_empty"] for x in result))
        self.assertTrue(all(x["published_source_cv_pct"] == "0.9" for x in result))

    def test_complete_synthetic_zip_replay_is_not_gov_fingerprint(self):
        raw, dat = fabricated_original()
        report = parse_fake_source(raw, dat)
        self.assertEqual(report["status"], m19.VERIFIED)
        self.assertEqual(report["matched_national_industry_source_rows"], 3)
        self.assertEqual(report["source_data_row_count"], 3)
        self.assertTrue(report["direct_original_census_ftp_replay_completed"])
        self.assertEqual(report["source_archive_sha256"], sha256(raw).hexdigest())
        self.assertEqual(report["source_dat_sha256"], sha256(dat).hexdigest())
        self.assertFalse(report["publisher_digitally_signed_archive_verified"])
        self.assertEqual(report["actual_paid_customer_ltl_invoices_observed"], 0)
        self.assertIsNone(report["retally_audit_recoverable_tam_usd"])
        self.assertEqual(report["receipt_sha256"], canon_hash({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_original_zip_wrong_size_does_not_get_promoted(self):
        with self.assertRaisesRegex(ValueError, "AIES_ORIGINAL_ZIP_SIZE_MISMATCH"):
            m19.verify_original_bytes(b"faked", as_of=TODAY)

    def test_original_zip_sha_drift_even_if_row_bytes_still_parse(self):
        raw, dat = fabricated_original()
        with patch.object(m19, "ZIP_SIZE_BYTES", len(raw)):
            with self.assertRaisesRegex(ValueError, "AIES_ORIGINAL_ZIP_SHA256_MISMATCH"):
                m19.verify_original_bytes(raw, as_of=TODAY)

    def test_archive_member_path_traversal_rejected_after_matching_synthetic_fingerprint(self):
        raw, dat = fabricated_original(bad_member=True)
        with self.assertRaisesRegex(ValueError, "UNSAFE_OR_DUPLICATE_ARCHIVE_MEMBER"):
            parse_fake_source(raw, dat)

    def test_forged_revenue_value_is_not_accepted_even_with_rehashed_test_zip(self):
        rows = samples()
        rows[2]["RCPT_TOT_VAL"] = "65096293"
        raw, dat = fabricated_original(rows)
        with self.assertRaisesRegex(ValueError, "AIES_ORIGINAL_FTP_DIFFERS_FROM_M18"):
            parse_fake_source(raw, dat)

    def test_one_missing_and_duplicate_revenue_category_rejected(self):
        with self.assertRaisesRegex(ValueError, "AIES_MISSING_NATIONAL_SOURCE_NAICS"):
            m19.selected_revenue(samples()[:2], expected=values())
        rows=samples()
        rows.append(deepcopy(rows[0]))
        with self.assertRaisesRegex(ValueError, "AIES_DUPLICATE_NATIONAL_NAICS_POPULATION"):
            m19.selected_revenue(rows, expected=values())

    def test_census_quality_suppressed_revenue_never_is_zero(self):
        for key in ("RCPT_TOT_VAL_F", "RCPT_TOT_CV_F",
                    "NAICS2017_F", "GEO_ID_F"):
            rows=samples()
            rows[2][key]="S"
            with self.assertRaisesRegex(ValueError, "AIES_SOURCE_FLAGGED_ESTIMATE"):
                m19.selected_revenue(rows, expected=values())

    def test_zero_placeholder_or_changed_revenue_unit_rejected(self):
        for val in ("0", ".", "65.096", "-1", "65096292000", "", None):
            rows=samples()
            rows[-1]["RCPT_TOT_VAL"]=val
            with self.assertRaises(ValueError, msg=str(val)):
                m19.selected_revenue(rows, expected=values())

    def test_unsourced_census_flags_do_not_establish_tiny_error_rate(self):
        for cv in ("", "S", "1000", "-0.1", ".", None, "nan"):
            rows=samples()
            rows[-1]["RCPT_TOT_CV"]=cv
            with self.assertRaises(ValueError, msg=str(cv)):
                m19.selected_revenue(rows, expected=values())

    def test_not_warehouse_and_not_broad_mode111_ltl(self):
        for field, val in (
            ("NAICS2017_LABEL", "All warehouses and freight"),
            ("SECTOR", "49"),
            ("INDLEVEL", "4"),
            ("TYPOP_LABEL", "Customers"),
            ("TAXSTAT_LABEL", "Tax-exempt only"),
        ):
            rows=samples()
            rows[-1][field]=val
            with self.assertRaises(ValueError, msg=field):
                m19.selected_revenue(rows, expected=values())

    def test_2024_national_all_employer_scope_cannot_be_swapped(self):
        for key,val in (
            ("#GEOTYPE", "02"), ("ST", "42"), ("GEO_ID", "0100000US-FAKE"),
            ("GEO_LABEL", "Pennsylvania"), ("YEAR", "2023"),
            ("TYPOP", "01"), ("TAXSTAT", "01"),
        ):
            rows=samples()
            rows[2][key]=val
            with self.assertRaisesRegex(ValueError, "AIES_MISSING_NATIONAL_SOURCE_NAICS"):
                m19.selected_revenue(rows, expected=values())

    def test_unknown_or_extra_prospect_column_fails_schema(self):
        rows=samples()
        rows[0].pop("SECTOR")
        with self.assertRaisesRegex(ValueError, "AIES_ROW_INVALID_SCHEMA"):
            m19.selected_revenue(rows, expected=values())

    def test_only_2024_is_publisher_authenticated_by_zip(self):
        report = m19.unavailable(as_of=TODAY)
        self.assertFalse(report["historical_2022_2023_original_ftp_replayed"])
        self.assertIsNone(report["reference_year_verified"])
        self.assertEqual(report["status"], m19.BLOCKED)
        self.assertFalse(report["direct_original_census_ftp_replay_completed"])
        self.assertEqual(report["source_estimates"], [])
        self.assertEqual(report["actual_paid_customer_ltl_invoices_observed"], 0)
        self.assertTrue(report["pilot_18_independent_human_requirements_still_unverified"])

    def test_no_source_result_can_claim_verified_ftp_or_recovery(self):
        report=m19.unavailable(as_of=TODAY)
        self.assertIsNone(report["source_archive_sha256"])
        self.assertIsNone(report["source_dat_sha256"])
        self.assertIsNone(report["actual_recovered_usd"])
        self.assertFalse(report["public_commercial_claims_authorized"])
        self.assertFalse(report["publisher_digitally_signed_archive_verified"])
        self.assertEqual(report["receipt_sha256"], canon_hash({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_network_timeout_returns_explicit_blocked_json_and_html(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv", ["verify", "--fetch-official",
                                    "--as-of-date", "2026-10-11",
                                    "--out", folder]):
                with patch.object(m19, "_download_original",
                                  side_effect=TimeoutError("test remote down")):
                    m19.main()
            report=json.loads((Path(folder)/"aies_primary_source.json").read_text())
            html=(Path(folder)/"aies_primary_source.html").read_text()
            self.assertEqual(report["status"], m19.BLOCKED)
            self.assertFalse(report["direct_original_census_ftp_replay_completed"])
            self.assertNotIn("2024 revenue CV", html)
            self.assertIn("Not verified", html)

    def test_data_change_is_not_swallowed_as_network_block(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv", ["verify", "--fetch-official",
                                    "--as-of-date", "2026-10-11",
                                    "--out", folder]):
                with patch.object(m19, "_download_original",
                                  return_value=b"changed publisher source"):
                    with self.assertRaisesRegex(ValueError,"AIES_ORIGINAL_ZIP_SIZE_MISMATCH"):
                        m19.main()

    def test_html_escapes_source_label_and_rejected_unsafe_content(self):
        raw, dat = fabricated_original()
        report = parse_fake_source(raw, dat)
        report["source_estimates"][0]["source_naics_label"]="<img src=x onerror=bad()>"
        html=m19.render_html(report)
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x", html)
        self.assertIn("not LTL customer-paid invoice", html)

    def test_old_asof_not_allowed_to_observe_future_archive(self):
        with self.assertRaisesRegex(ValueError, "M19_SOURCE_OBSERVATION_DATE_INVALID"):
            m19.unavailable(as_of=date(2026,9,10))


if __name__ == "__main__":
    unittest.main()
