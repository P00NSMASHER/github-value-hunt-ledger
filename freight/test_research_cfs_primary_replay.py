"""Mission 17 adversarial, offline-only validation; never accesses Census network."""
from __future__ import annotations

from copy import deepcopy
import csv
from datetime import date
from hashlib import sha256
from html import escape
import io
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from freight.research_cfs_mode_hierarchy import TABLES, _git_blob_sha1
from freight.research_cfs_industry_quality import OFFICIAL_PROFILES
from freight.research_cfs_primary_replay import (
    COMMON_NATIONAL, SCOPE, SELECTED_FIELDS, TABLE_AXIS, _frozen_book,
    _official_download, _selected_rows, _verify_archive, render_html, replay,
)

AS_OF = date(2026, 10, 11)


def fixture(table: str):
    book = _frozen_book(AS_OF)
    rows = []
    for item in book["selected_source_rows"]:
        if item["table_id"] != table:
            continue
        row = dict(COMMON_NATIONAL)
        row["GEO_ID_F"] = ""
        row["DMODE_F"] = ""
        row["DMODE_LABEL"] = "For-hire truck"
        row["NAICS2017"] = item["naics2017"]
        row[TABLE_AXIS[table]] = item["stratum_code"]
        row[TABLE_AXIS[table] + "_LABEL"] = item["stratum_label"]
        for source, frozen in SELECTED_FIELDS:
            row[source] = str(item[frozen]) if type(item[frozen]) is int else item[frozen]
        rows.append(row)
    return book, rows


class PrimarySourceReplayTests(unittest.TestCase):
    def test_frozen_snapshotted_mirror_has_all_60_rows(self):
        b = _frozen_book(AS_OF)
        self.assertEqual(len(b["selected_source_rows"]), 60)
        self.assertEqual(set(TABLES), {"CF2200A18", "CF2200A19"})

    def test_all_sixty_exact_cells_can_be_compared_at_original_source_grain(self):
        for t in TABLES:
            book, rows = fixture(t)
            result = _selected_rows(t, rows, book)
            self.assertEqual(result["selected_rows_matched"], 30)
            self.assertEqual(result["mismatched_cells"], 0)
            self.assertTrue(result["suppressed_cells_preserved"])

    def test_tampered_goods_value_rejected(self):
        b, rows = fixture("CF2200A18")
        rows[0]["VAL"] = str(int(rows[0]["VAL"]) + 1)
        with self.assertRaisesRegex(ValueError, "SOURCE_CELL_DIFFERS"):
            _selected_rows("CF2200A18", rows, b)

    def test_tampered_tonnage_rejected(self):
        b, rows = fixture("CF2200A19")
        rows[0]["TON"] = str(int(rows[0]["TON"]) + 1)
        with self.assertRaisesRegex(ValueError, "SOURCE_CELL_DIFFERS"):
            _selected_rows("CF2200A19", rows, b)

    def test_cv_quality_suppression_flag_changes_fail(self):
        for table, naics, bucket, field in [
            ("CF2200A18", "4931", "09", "TON_F"),
            ("CF2200A19", "4931", "10", "VAL_F"),
            ("CF2200A19", "4931", "10", "TON_F"),
            ("CF2200A19", "4931", "10", "TON_S_F"),
        ]:
            b, rows = fixture(table)
            r = next(x for x in rows if x["NAICS2017"] == naics
                     and x[TABLE_AXIS[table]] == bucket)
            self.assertEqual(r[field], "S")
            r[field] = ""
            with self.assertRaisesRegex(ValueError, "SOURCE_CELL_DIFFERS"):
                _selected_rows(table, rows, b)

    def test_changed_cv_rejected(self):
        b, rows = fixture("CF2200A18")
        rows[0]["VAL_S"] = "99.9"
        with self.assertRaisesRegex(ValueError, "SOURCE_CELL_DIFFERS"):
            _selected_rows("CF2200A18", rows, b)

    def test_duplicate_source_key_rejected(self):
        b, rows = fixture("CF2200A19")
        rows.append(deepcopy(rows[0]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_SOURCE_KEY"):
            _selected_rows("CF2200A19", rows, b)

    def test_missing_source_key_rejected(self):
        b, rows = fixture("CF2200A18")
        rows.pop()
        with self.assertRaisesRegex(ValueError, "MISSING_SOURCE_KEYS"):
            _selected_rows("CF2200A18", rows, b)

    def test_wrong_mode_or_year_is_not_credited(self):
        for k, v in [("DMODE", "110"), ("YEAR", "2017"),
                     ("GEO_ID", "fake"), ("#GEOTYPE", "02")]:
            b, rows = fixture("CF2200A19")
            rows[0][k] = v
            with self.assertRaisesRegex(ValueError, "MISSING_SOURCE_KEYS"):
                _selected_rows("CF2200A19", rows, b)

    def test_wrong_bucket_and_forhire_labels_rejected(self):
        for field, value, expected in [
            ("SHIPDIST_LABEL", "500+ miles", "SOURCE_BUCKET_LABEL_DIFFERS"),
            ("DMODE_LABEL", "Rail", "SOURCE_MODE_LABEL_NOT_FOR_HIRE"),
            ("GEO_ID_F", "S", "SOURCE_GEOGRAPHY_OR_MODE_FLAGGED"),
        ]:
            b, rows = fixture("CF2200A18")
            rows[0][field] = value
            with self.assertRaisesRegex(ValueError, expected):
                _selected_rows("CF2200A18", rows, b)

    def test_wrong_source_table_and_empty_rows_rejected(self):
        b, rows = fixture("CF2200A19")
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCE"):
            _selected_rows("CF2200A20", rows, b)
        with self.assertRaisesRegex(ValueError, "INVALID_SOURCE"):
            _selected_rows("CF2200A19", [], b)

    def test_fake_zip_cannot_pass_fixed_archive_sha_and_size(self):
        b, _ = fixture("CF2200A18")
        for data in [b"PK\x03\x04garbage", b"", b"not a census archive"]:
            with self.assertRaises(ValueError):
                _verify_archive("CF2200A18", data, b)

    def test_complete_dat_blob_identity_gate_even_when_all_selected_cells_match(self):
        table = "CF2200A18"
        book, rows = fixture(table)
        header = OFFICIAL_PROFILES[table]["header"].split("|")
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=header, delimiter="|",
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        dat = buf.getvalue().encode("utf-8")
        zipped = io.BytesIO()
        with ZipFile(zipped, "w", compression=ZIP_DEFLATED) as z:
            z.writestr(table + ".dat", dat)
        raw_zip = zipped.getvalue()
        fake_source_profile = {
            "original_zip_size_bytes": len(raw_zip),
            "original_zip_sha256": sha256(raw_zip).hexdigest(),
            "mirror_file_bytes": len(dat),
            "mirror_file_row_count": len(rows),
            "mirror_git_blob_sha1": _git_blob_sha1(dat),
        }
        with patch.dict(TABLES[table], fake_source_profile):
            valid = _verify_archive(table, raw_zip, book)
            self.assertTrue(valid["whole_dat_file_identical_to_git_mirror_proven"])
            self.assertEqual(valid["selected_rows_matched"], 30)
            # Even an otherwise valid original source cannot be promoted if the
            # pinned full mirror Git blob disagrees with the original DAT.
            TABLES[table]["mirror_git_blob_sha1"] = "0" * 40
            with self.assertRaisesRegex(ValueError,
                                        "FULL_ORIGINAL_DAT_DIFFERS_FROM_PINNED_GITHUB_MIRROR"):
                _verify_archive(table, raw_zip, book)

    def test_replay_requires_both_verified_tables(self):
        with self.assertRaisesRegex(ValueError, "EXACTLY_TWO_ARCHIVES"):
            replay(as_of=AS_OF, zip_bytes={"CF2200A18": b"fake"})
        with self.assertRaisesRegex(ValueError, "EXACTLY_TWO_ARCHIVES"):
            replay(as_of=AS_OF, zip_bytes={}, acquisition="FAKE_OFFICIAL_SOURCE")

    def test_unapproved_external_url_is_not_queried(self):
        with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_DOWNLOAD_TABLE"):
            _official_download("https://attacker.example/evil.zip")

    def test_evidence_report_escapes_untrusted_content(self):
        safe = render_html({
            "status": "<img src=x onerror=evil()>",
            "tables": [{"table_id": "<script>", "selected_rows_matched": 30,
                        "official_archive_sha256": "<svg>"}],
            "caveat": "<b>not validated</b>",
            "acquisition": "<style>",
        })
        self.assertNotIn("<script>", safe)
        self.assertNotIn("<img src=x", safe)
        self.assertIn("&lt;svg&gt;", safe)

    def test_no_publisher_signature_or_commercial_claims_in_scope(self):
        self.assertEqual(SCOPE, "LAB14_CFS_OFFICIAL_BYTES_60_ROW_REPLAY_NOT_LTL_BILLING")
        self.assertEqual(len(TABLES), 2)


if __name__ == "__main__":
    unittest.main()
