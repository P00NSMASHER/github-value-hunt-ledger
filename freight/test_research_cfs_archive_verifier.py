"""Mission 13 Census ZIP byte/parser hardening; ALL CSV fixtures synthetic."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZipInfo

from freight.research_cfs_archive_verifier import (
    OFFICIAL_URL, TABLE_ID, MAPPING_SCOPE, AUDIT,
    build_readiness, digest_bytes, inspect_local_archive,
    match_original_excerpt, render_html, _read_archive,
)
from freight.research_evidence_gate import canon_hash

TODAY = date(2026, 10, 11)
MEMBER = "CF2200A01_SYNTHETIC_FOR_TESTS_ONLY.csv"


def fake_mapping():
    original = json.loads(AUDIT.read_text(encoding="utf-8"))
    return {
        "schema_version": 1, "scope": MAPPING_SCOPE,
        "source_url": OFFICIAL_URL, "table_id": TABLE_ID,
        "member": MEMBER,
        "claims_of_external_approval": False,
        "columns": {
            "geography": "geography", "mode": "mode",
            "year": "year", "value_million_usd": "value_million_usd",
            "weight_thousand_tons": "weight_thousand_tons",
        },
        "selectors": [
            {"row_id": r["id"], "geography": r["geo"],
             "mode": r["mode_code"], "year": "2022"}
            for r in original["table_rows"]
        ],
    }


def sample_csv(*, mutate=None, append=None, headers=None):
    original = json.loads(AUDIT.read_text(encoding="utf-8"))
    h = headers or [
        "geography", "mode", "year", "value_million_usd",
        "weight_thousand_tons",
    ]
    data = [
        {h[0]: r["geo"], h[1]: r["mode_code"], h[2]: "2022",
         h[3]: str(r["value_million_usd"]), h[4]: str(r["weight_thousand_tons"])}
        for r in original["table_rows"]
    ]
    if mutate:
        mutate(data)
    if append:
        data.append(append)
    return (",".join(h) + "\n" +
            "\n".join(",".join(str(r.get(col, "")) for col in h)
                      for r in data) + "\n").encode("utf-8")


def synthetic_zip(csv_bytes=None, member=MEMBER, extras=None):
    out = io.BytesIO()
    with ZipFile(out, "w") as z:
        z.writestr(member, sample_csv() if csv_bytes is None else csv_bytes)
        for name, data in extras or []:
            z.writestr(name, data)
    return out.getvalue()


class SourceByteVerifierTests(unittest.TestCase):
    def test_default_readiness_does_not_claim_original_zip_was_downloaded(self):
        r = build_readiness(as_of=TODAY)
        self.assertEqual(r["scope"], "CFS_A01_ORIGINAL_SOURCE_BYTE_REVIEW_NOT_YET_PERFORMED")
        self.assertFalse(r["original_archive_bytes_inspected_in_this_run"])
        self.assertFalse(r["publisher_signature_verified"])
        self.assertFalse(r["automatic_source_fetch_or_schedule"])
        self.assertIsNone(r["actual_official_zip_sha256"])
        self.assertEqual(r["independent_original_rows_reproduced"], 0)
        self.assertEqual(r["expected_row_count"], 6)
        self.assertFalse(r["south_press_discrepancy_cleared"])
        self.assertFalse(r["any_ltl_recovery_market_claim_permitted"])
        self.assertEqual(r["receipt_sha256"], canon_hash({
            k:v for k,v in r.items() if k != "receipt_sha256"
        }))

    def test_real_parser_logic_is_rehearsed_only_on_explicit_synthetic_bytes(self):
        archive = synthetic_zip()
        m = fake_mapping()
        r = match_original_excerpt(raw=archive, mapping=m, as_of=TODAY,
                                   simulated_test_bytes=True)
        self.assertEqual(r["scope"], "SYNTHETIC_ARCHIVE_PARSER_TEST_NO_ORIGINAL_SOURCE")
        self.assertEqual(r["original_zip_sha256_if_local_bytes"], digest_bytes(archive))
        self.assertEqual(r["six_excerpt_rows_matched"], 6)
        self.assertEqual(r["csv_row_count"], 6)
        self.assertEqual(r["member_count"], 1)
        self.assertTrue(all(row["matches_frozen_mission12_excerpt"] for row in r["matched"]))
        self.assertFalse(r["original_publisher_authenticated"])
        self.assertIsNone(r["real_invoice_spend_usd"])
        self.assertIsNone(r["actual_ltl_invoice_error_rate"])
        self.assertFalse(r["market_tam_verified"])
        self.assertFalse(r["public_accuracy_claims_authorized"])
        self.assertFalse(r["mission12_press_discrepancy_auto_corrected"])
        self.assertFalse(r["new_lab_created"])

    def test_byte_hash_changes_when_archive_bytes_are_changed(self):
        a=synthetic_zip()
        b=synthetic_zip(extras=[("notes.txt", "ALL SYNTHETIC")])
        ra=inspect_local_archive(a,as_of=TODAY)
        rb=inspect_local_archive(b,as_of=TODAY)
        self.assertNotEqual(ra["local_archive_sha256"],rb["local_archive_sha256"])
        self.assertEqual(ra["local_archive_sha256"],digest_bytes(a))
        self.assertFalse(ra["official_source_identity_proven"])
        self.assertEqual(ra["actual_ltl_carrier_invoice_rows"],0)

    def test_inspection_reports_only_header_metadata_not_csv_body(self):
        r=inspect_local_archive(synthetic_zip(),as_of=TODAY)
        self.assertEqual(r["members"][0]["member"],MEMBER)
        self.assertEqual(r["members"][0]["row_count"],6)
        self.assertEqual(r["members"][0]["columns"][3],"value_million_usd")
        self.assertNotIn("8,062,541",json.dumps(r))
        self.assertFalse(r["independent_full_cfs_dataset_replication"])

    def test_duplicate_source_row_even_if_correct_is_fatal(self):
        extra={
            "geography":"United States","mode":"111","year":"2022",
            "value_million_usd":8062541,"weight_thousand_tons":3909476
        }
        with self.assertRaisesRegex(ValueError,"DUPLICATE_CENSUS_SOURCE_ROW"):
            match_original_excerpt(raw=synthetic_zip(sample_csv(append=extra)),
                                   mapping=fake_mapping(),as_of=TODAY,simulated_test_bytes=True)

    def test_missing_source_row_is_not_inferred_from_previous_snapshot(self):
        def f(rows):rows.pop()
        with self.assertRaisesRegex(ValueError,"MISSING_CENSUS_SOURCE_ROWS"):
            match_original_excerpt(raw=synthetic_zip(sample_csv(mutate=f)),
                                   mapping=fake_mapping(),as_of=TODAY,simulated_test_bytes=True)

    def test_wrong_original_amount_cannot_be_replaced_by_frozen_summary(self):
        def f(rows):rows[2]["value_million_usd"]="8062540"
        with self.assertRaisesRegex(ValueError,"SOURCE_FILE_DIFFERS_FROM_PREVIOUSLY_RECORDED"):
            match_original_excerpt(raw=synthetic_zip(sample_csv(mutate=f)),
                                   mapping=fake_mapping(),as_of=TODAY,simulated_test_bytes=True)

    def test_suppression_markers_are_not_zeros(self):
        for wrong in ("D","S","-","*","N","-", "1.2"):
            def f(rows):rows[2]["weight_thousand_tons"]=wrong
            with self.assertRaisesRegex(ValueError,"SUPPRESSED_NON_NUMERIC"):
                match_original_excerpt(raw=synthetic_zip(sample_csv(mutate=f)),
                                       mapping=fake_mapping(),as_of=TODAY,simulated_test_bytes=True)

    def test_thousand_million_scaling_errors_are_rejected(self):
        def f(rows):rows[0]["value_million_usd"]=17996782000
        with self.assertRaisesRegex(ValueError,"SOURCE_FILE_DIFFERS"):
            match_original_excerpt(raw=synthetic_zip(sample_csv(mutate=f)),
                                   mapping=fake_mapping(),as_of=TODAY,simulated_test_bytes=True)

    def test_unsafe_traversal_names_and_backslashes_rejected(self):
        for member in ("../secret.csv","/absolute.csv","sub\\secret.csv","dir/../source.csv",
                       "C:\\windows\\invoice.csv"):
            with self.assertRaisesRegex(ValueError,"UNSAFE_OR_DUPLICATE_ARCHIVE_MEMBER"):
                inspect_local_archive(synthetic_zip(member=member),as_of=TODAY)

    def test_zip_bomb_suspect_denied_even_when_small_compressed(self):
        content = b"x"*(3*1024*1024)
        with self.assertRaisesRegex(ValueError,"ZIP_BOMB_SUSPECTED"):
            inspect_local_archive(synthetic_zip(csv_bytes=content),as_of=TODAY)

    def test_duplicate_zip_filename_denied(self):
        out=io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore",UserWarning)
            with ZipFile(out,"w") as z:
                z.writestr(MEMBER,sample_csv())
                z.writestr(MEMBER,sample_csv())
        with self.assertRaisesRegex(ValueError,"UNSAFE_OR_DUPLICATE_ARCHIVE_MEMBER"):
            inspect_local_archive(out.getvalue(),as_of=TODAY)

    def test_empty_fake_or_non_zip_archive_rejected(self):
        with self.assertRaisesRegex(ValueError,"INVALID_ARCHIVE"):
            inspect_local_archive(b"not zip",as_of=TODAY)
        with self.assertRaisesRegex(ValueError,"ORIGINAL_ARCHIVE_HAS_NO_CSV"):
            inspect_local_archive(synthetic_zip(member="readme.txt"),as_of=TODAY)

    def test_mapping_cannot_invent_new_source_or_version(self):
        for key,val in (("source_url","https://attacker.example/cfs.zip"),
                        ("table_id","CF2200A18"),("scope","CERTIFIED"),
                        ("claims_of_external_approval",True)):
            m=fake_mapping()
            m[key]=val
            with self.assertRaisesRegex(ValueError,"MAPPING_CANNOT_ASSERT"):
                match_original_excerpt(raw=synthetic_zip(),mapping=m,as_of=TODAY,
                                       simulated_test_bytes=True)

    def test_mapping_cannot_drop_or_duplicate_a_original_row(self):
        m=fake_mapping()
        m["selectors"].pop()
        with self.assertRaisesRegex(ValueError,"ALL_SIX_PUBLIC_TABLE_ROWS"):
            match_original_excerpt(raw=synthetic_zip(),mapping=m,as_of=TODAY,
                                   simulated_test_bytes=True)
        m=fake_mapping()
        m["selectors"][1]["row_id"]=m["selectors"][0]["row_id"]
        with self.assertRaisesRegex(ValueError,"UNRECOGNIZED_OR_DUPLICATE_SOURCE_ROW"):
            match_original_excerpt(raw=synthetic_zip(),mapping=m,as_of=TODAY,
                                   simulated_test_bytes=True)

    def test_mapping_cannot_mislabel_mode_or_year(self):
        for key,val in (("mode","112"),("year","2017")):
            m=fake_mapping()
            m["selectors"][2][key]=val
            with self.assertRaisesRegex(ValueError,"SOURCE_ROW_CODE_VINTAGE"):
                match_original_excerpt(raw=synthetic_zip(),mapping=m,as_of=TODAY,
                                       simulated_test_bytes=True)

    def test_invalid_header_names_or_unavailable_member_are_held(self):
        m=fake_mapping()
        m["columns"]["value_million_usd"]="fake_fee_total"
        with self.assertRaisesRegex(ValueError,"MAPPING_COLUMN_NOT_IN_SOURCE"):
            match_original_excerpt(raw=synthetic_zip(),mapping=m,as_of=TODAY,
                                   simulated_test_bytes=True)
        m=fake_mapping()
        m["member"]="not_in_archive.csv"
        with self.assertRaisesRegex(ValueError,"UNRECOGNIZED_MAPPED_SOURCE_MEMBER"):
            match_original_excerpt(raw=synthetic_zip(),mapping=m,as_of=TODAY,
                                   simulated_test_bytes=True)

    def test_duplicate_csv_headers_are_rejected(self):
        hdr=["geography","mode","year","value_million_usd","value_million_usd"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE_MISSING_OR_UNBOUNDED_HEADERS"):
            inspect_local_archive(synthetic_zip(sample_csv(headers=hdr)),as_of=TODAY)

    def test_utf8_failure_in_source_is_not_silently_decoded(self):
        with self.assertRaisesRegex(ValueError,"CSV_UNREADABLE_OR_CORRUPT"):
            inspect_local_archive(synthetic_zip(b"\xff\xfe\xfd"),as_of=TODAY)

    def test_local_file_rejects_symlink_and_wrong_magic(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fake.zip";p.write_bytes(b"not a zip")
            with self.assertRaisesRegex(ValueError,"ARCHIVE_NOT_ZIP_LOCAL_HEADER"):
                _read_archive(p)
            target=Path(d)/"target.zip";target.write_bytes(synthetic_zip())
            symlink=Path(d)/"link.zip";symlink.symlink_to(target)
            with self.assertRaisesRegex(ValueError,"LOCAL_ARCHIVE_MISSING_SYMLINK"):
                _read_archive(symlink)

    def test_readiness_html_is_escaped_and_refuses_verification_claim(self):
        r=build_readiness(as_of=TODAY)
        html=render_html(r)
        self.assertIn("Inspection Still Required",html)
        self.assertIn("has not been examined",html)
        self.assertNotIn("official source authenticated: yes",html.lower())
        bad=deepcopy(r)
        bad["scope"]='<script>alert("x")</script>'
        html=render_html(bad)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)

    def test_source_review_replay_is_deterministic_and_no_live_activity(self):
        a=build_readiness(as_of=TODAY)
        b=build_readiness(as_of=TODAY)
        self.assertEqual(a,b)
        self.assertFalse(a["automatic_source_fetch_or_schedule"])
        future=build_readiness(as_of=date(2027,2,1))
        self.assertFalse(future["independent_original_rows_reproduced"])
        self.assertEqual(future["real_invoice_records_ingested"],0)


if __name__=="__main__":
    unittest.main()
