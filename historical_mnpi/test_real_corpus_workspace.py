import csv
import hashlib
import json
import unittest
from pathlib import Path

from historical_mnpi.real_corpus_import import (
    import_real_corpus_metadata,
)


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


class RealCorpusWorkspaceTests(unittest.TestCase):
    def test_event_backbone_matches_frozen_manifest(self):
        events_path = CORPUS_DIR / "events.csv"
        manifest_path = CORPUS_DIR / "manifest.json"

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload = events_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            manifest["derived_backbone_sha256"],
        )

        with events_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 174)
        self.assertEqual(
            len({row["event_id"] for row in rows}),
            174,
        )
        self.assertEqual(
            len({row["historical_symbol"] for row in rows}),
            146,
        )
        self.assertEqual(
            len({row["first_trade_date"] for row in rows}),
            72,
        )
        self.assertEqual(
            min(row["first_trade_date"] for row in rows),
            "2011-04-19",
        )
        self.assertEqual(
            max(row["first_trade_date"] for row in rows),
            "2015-05-20",
        )

    def test_event_ids_reproduce_prior_prototype_identity_scheme(self):
        events_path = CORPUS_DIR / "events.csv"
        with events_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        for row in rows:
            raw = (
                f"{int(row['permno'])}|"
                f"{int(row['gvkey'])}|"
                f"{row['historical_symbol'].strip().upper()}|"
                f"{row['first_documented_illicit_trade_ts'].strip()}"
            ).encode("utf-8")
            expected = (
                "HEJFE-"
                + hashlib.sha256(raw).hexdigest()[:16].upper()
            )
            self.assertEqual(row["event_id"], expected)

    def test_workspace_metadata_files_import_current_verified_rows(self):
        import_dir = CORPUS_DIR / "import"
        names = (
            "announcement_metadata.csv",
            "listing_metadata.csv",
            "shares_metadata.csv",
            "control_metadata.csv",
            "market_source_dates.csv",
        )
        files = {
            name: (import_dir / name).read_text(encoding="utf-8")
            for name in names
        }
        imported = import_real_corpus_metadata(files)
        self.assertEqual(
            imported.counts(),
            {
                "announcement_rows": 27,
                "listing_rows": 2904,
                "shares_rows": 0,
                "control_rows": 0,
                "market_source_date_rows": 0,
                "import_hash": imported.proof_hash,
                "live_use_allowed": False,
            },
        )

        self.assertEqual(len(imported.announcements), 27)
        by_event = {
            item.event_id: item
            for item in imported.announcements
        }
        self.assertEqual(
            by_event["HEJFE-A413A5AC6E515E3C"].timestamp,
            "2011-04-28T07:00:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-F170013A9B3F85E2"].timestamp,
            "2015-04-22T16:01:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-C4D39B22234902F2"].timestamp,
            "2015-02-03T16:07:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-D4E8CD312A2AA576"].timestamp,
            "2012-01-25T16:10:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-95933AA0B84D2F60"].timestamp,
            "2012-01-26T07:30:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-A9D220DE2F7E7FC3"].timestamp,
            "2015-02-20T07:00:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-7ED8DBD4804E4330"].timestamp,
            "2015-02-19T13:05:00-08:00",
        )
        self.assertEqual(
            by_event["HEJFE-76DCF0FCA248E814"].timestamp,
            "2012-01-26T16:03:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-D9C52E6CC595C380"].timestamp,
            "2015-02-17T16:05:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-09EB83905864C50A"].timestamp,
            "2015-05-19T16:00:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-824BABBAD988A068"].timestamp,
            "2012-01-25T16:18:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-99CCB9D9BECE4E72"].timestamp,
            "2012-01-27T07:00:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-76B03970FA6BDB42"].timestamp,
            "2013-02-20T04:05:00-08:00",
        )
        self.assertEqual(
            by_event["HEJFE-E8C5063581BE7EB7"].timestamp,
            "2015-01-29T07:00:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-704E64D64C11C119"].timestamp,
            "2012-01-24T09:15:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-7E8FA3E5E417B5E7"].timestamp,
            "2012-01-24T06:30:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-D1D8268651584B6A"].timestamp,
            "2013-04-02T06:30:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-89844B5980EB5339"].timestamp,
            "2012-01-25T16:30:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-56483839E5F0E88F"].timestamp,
            "2012-01-26T08:50:00-05:00",
        )
        self.assertEqual(
            by_event["HEJFE-2558DC6865781793"].timestamp,
            "2013-04-23T16:05:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-2C887DA6F617936F"].timestamp,
            "2013-09-19T16:05:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-ED329F780A1085DA"].timestamp,
            "2013-04-23T16:01:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-830337A8564B826E"].timestamp,
            "2013-10-17T16:00:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-3BBEC23702C1A375"].timestamp,
            "2013-07-23T16:01:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-E342F6A93B35E012"].timestamp,
            "2015-02-11T11:00:00+00:00",
        )
        self.assertEqual(
            by_event["HEJFE-DC002D2C6C767277"].timestamp,
            "2011-10-20T17:09:00-04:00",
        )
        self.assertEqual(
            by_event["HEJFE-51F3066EAC9B8138"].timestamp,
            "2012-01-26T16:05:00-05:00",
        )
        self.assertTrue(all(
            item.proves_first_public_release
            for item in imported.announcements
        ))

    def test_manifest_tracks_current_real_readiness(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["announcement_exact_resolved"], 27)
        self.assertEqual(manifest["listing_metadata_resolved"], 2904)
        self.assertEqual(manifest["shares_metadata_resolved"], 0)
        self.assertEqual(manifest["control_dates_resolved"], 0)
        self.assertFalse(manifest["live_use_allowed"])
        self.assertIn("research/compliance", manifest["purpose"])


    def test_announcement_batch_one_reviews_exactly_30_unresolved_events(self):
        review_path = CORPUS_DIR / "announcement_review_log.csv"
        with review_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        batch = [
            row for row in rows
            if row["batch_id"] == "G1-BATCH-001"
        ]
        self.assertEqual(len(batch), 30)
        self.assertEqual(
            [int(row["batch_position"]) for row in batch],
            list(range(1, 31)),
        )
        self.assertEqual(
            len({row["event_id"] for row in batch}),
            30,
        )

        resolved = [
            row for row in batch
            if row["review_status"] == "RESOLVED_EXACT_PUBLIC_TIME"
        ]
        unresolved = [
            row for row in batch
            if row["review_status"] == "UNRESOLVED_AFTER_REVIEW"
        ]
        self.assertEqual(len(resolved), 2)
        self.assertEqual(len(unresolved), 28)
        self.assertEqual(
            {row["event_id"] for row in resolved},
            {
                "HEJFE-95933AA0B84D2F60",
                "HEJFE-A9D220DE2F7E7FC3",
            },
        )
        self.assertTrue(all(
            row["reason"]
            for row in batch
        ))

    def test_manifest_tracks_batch_one_review_progress(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            manifest["announcement_review_batches_completed"],
            6,
        )
        self.assertEqual(
            manifest["announcement_events_reviewed_in_batch_sequence"],
            170,
        )
        self.assertEqual(
            manifest["announcement_unresolved_after_batch_review"],
            147,
        )


    def test_announcement_batch_two_reviews_exactly_next_30_events(self):
        review_path = CORPUS_DIR / "announcement_review_log.csv"
        with review_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        batch = [
            row for row in rows
            if row["batch_id"] == "G1-BATCH-002"
        ]
        self.assertEqual(len(batch), 30)
        self.assertEqual(
            [int(row["batch_position"]) for row in batch],
            list(range(1, 31)),
        )
        self.assertEqual(
            len({row["event_id"] for row in batch}),
            30,
        )

        resolved = [
            row for row in batch
            if row["review_status"] == "RESOLVED_EXACT_PUBLIC_TIME"
        ]
        unresolved = [
            row for row in batch
            if row["review_status"] == "UNRESOLVED_AFTER_REVIEW"
        ]
        self.assertEqual(len(resolved), 5)
        self.assertEqual(len(unresolved), 25)
        self.assertEqual(
            {row["event_id"] for row in resolved},
            {
                "HEJFE-76B03970FA6BDB42",
                "HEJFE-E8C5063581BE7EB7",
                "HEJFE-704E64D64C11C119",
                "HEJFE-7E8FA3E5E417B5E7",
                "HEJFE-D1D8268651584B6A",
            },
        )
        self.assertTrue(all(row["reason"] for row in batch))

    def test_first_two_announcement_batches_do_not_overlap(self):
        review_path = CORPUS_DIR / "announcement_review_log.csv"
        with review_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        first_two = [
            row for row in rows
            if row["batch_id"] in {
                "G1-BATCH-001",
                "G1-BATCH-002",
            }
        ]
        self.assertEqual(len(first_two), 60)
        self.assertEqual(
            len({row["event_id"] for row in first_two}),
            60,
        )


    def test_announcement_batch_three_reviews_exactly_30_events(self):
        review_path = CORPUS_DIR / "announcement_review_log.csv"
        with review_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        batch = [
            row for row in rows
            if row["batch_id"] == "G1-BATCH-003"
        ]
        self.assertEqual(len(batch), 30)
        self.assertEqual(
            [int(row["batch_position"]) for row in batch],
            list(range(1, 31)),
        )
        self.assertEqual(len({row["event_id"] for row in batch}), 30)

        resolved = [
            row for row in batch
            if row["review_status"] == "RESOLVED_EXACT_PUBLIC_TIME"
        ]
        unresolved = [
            row for row in batch
            if row["review_status"] == "UNRESOLVED_AFTER_REVIEW"
        ]
        self.assertEqual(len(resolved), 6)
        self.assertEqual(len(unresolved), 24)
        self.assertEqual(
            {row["event_id"] for row in resolved},
            {
                "HEJFE-7ED8DBD4804E4330",
                "HEJFE-76DCF0FCA248E814",
                "HEJFE-D9C52E6CC595C380",
                "HEJFE-09EB83905864C50A",
                "HEJFE-824BABBAD988A068",
                "HEJFE-99CCB9D9BECE4E72",
            },
        )
        self.assertTrue(all(row["reason"] for row in batch))


    def test_announcement_batch_four_reviews_exactly_30_events(self):
        review_path = CORPUS_DIR / "announcement_review_log.csv"
        with review_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        batch = [
            row for row in rows
            if row["batch_id"] == "G1-BATCH-004"
        ]
        self.assertEqual(len(batch), 30)
        self.assertEqual(
            [int(row["batch_position"]) for row in batch],
            list(range(1, 31)),
        )
        self.assertEqual(len({row["event_id"] for row in batch}), 30)

        resolved = [
            row for row in batch
            if row["review_status"] == "RESOLVED_EXACT_PUBLIC_TIME"
        ]
        unresolved = [
            row for row in batch
            if row["review_status"] == "UNRESOLVED_AFTER_REVIEW"
        ]
        self.assertEqual(len(resolved), 3)
        self.assertEqual(len(unresolved), 27)
        self.assertEqual(
            {row["event_id"] for row in resolved},
            {
                "HEJFE-89844B5980EB5339",
                "HEJFE-56483839E5F0E88F",
                "HEJFE-2558DC6865781793",
            },
        )
        self.assertTrue(all(row["reason"] for row in batch))


    def test_announcement_batch_five_reviews_exactly_30_events(self):
        review_path = CORPUS_DIR / "announcement_review_log.csv"
        with review_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        batch = [
            row for row in rows
            if row["batch_id"] == "G1-BATCH-005"
        ]
        self.assertEqual(len(batch), 30)
        self.assertEqual(
            [int(row["batch_position"]) for row in batch],
            list(range(1, 31)),
        )
        self.assertEqual(len({row["event_id"] for row in batch}), 30)

        resolved = [
            row for row in batch
            if row["review_status"] == "RESOLVED_EXACT_PUBLIC_TIME"
        ]
        unresolved = [
            row for row in batch
            if row["review_status"] == "UNRESOLVED_AFTER_REVIEW"
        ]
        self.assertEqual(len(resolved), 3)
        self.assertEqual(len(unresolved), 27)
        self.assertEqual(
            {row["event_id"] for row in resolved},
            {
                "HEJFE-2C887DA6F617936F",
                "HEJFE-ED329F780A1085DA",
                "HEJFE-830337A8564B826E",
            },
        )
        self.assertTrue(all(row["reason"] for row in batch))


    def test_announcement_batch_six_reviews_final_20_events(self):
        review_path = CORPUS_DIR / "announcement_review_log.csv"
        with review_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        batch = [
            row for row in rows
            if row["batch_id"] == "G1-BATCH-006"
        ]
        self.assertEqual(len(batch), 20)
        self.assertEqual(
            [int(row["batch_position"]) for row in batch],
            list(range(1, 21)),
        )
        self.assertEqual(len({row["event_id"] for row in batch}), 20)

        resolved = [
            row for row in batch
            if row["review_status"] == "RESOLVED_EXACT_PUBLIC_TIME"
        ]
        unresolved = [
            row for row in batch
            if row["review_status"] == "UNRESOLVED_AFTER_REVIEW"
        ]
        self.assertEqual(len(resolved), 4)
        self.assertEqual(len(unresolved), 16)
        self.assertEqual(
            {row["event_id"] for row in resolved},
            {
                "HEJFE-3BBEC23702C1A375",
                "HEJFE-E342F6A93B35E012",
                "HEJFE-DC002D2C6C767277",
                "HEJFE-51F3066EAC9B8138",
            },
        )
        self.assertTrue(all(row["reason"] for row in batch))

    def test_all_174_events_are_accounted_for_after_final_batch(self):
        with (CORPUS_DIR / "events.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            events = list(csv.DictReader(handle))
        with (CORPUS_DIR / "announcement_review_log.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            reviews = list(csv.DictReader(handle))

        import_dir = CORPUS_DIR / "import"
        files = {
            name: (import_dir / name).read_text(encoding="utf-8")
            for name in (
                "announcement_metadata.csv",
                "listing_metadata.csv",
                "shares_metadata.csv",
                "control_metadata.csv",
                "market_source_dates.csv",
            )
        }
        imported = import_real_corpus_metadata(files)

        corpus_ids = {row["event_id"] for row in events}
        reviewed_ids = {row["event_id"] for row in reviews}
        resolved_ids = {
            item.event_id for item in imported.announcements
        }

        self.assertEqual(len(corpus_ids), 174)
        self.assertEqual(len(reviewed_ids), 170)
        self.assertEqual(len(resolved_ids), 27)
        self.assertEqual(corpus_ids, reviewed_ids | resolved_ids)
        self.assertEqual(len(corpus_ids - reviewed_ids - resolved_ids), 0)

        unresolved_reviewed = {
            row["event_id"]
            for row in reviews
            if row["review_status"] == "UNRESOLVED_AFTER_REVIEW"
        }
        self.assertEqual(len(unresolved_reviewed), 147)
        self.assertEqual(
            unresolved_reviewed,
            corpus_ids - resolved_ids,
        )


    def test_g2_current_batches_resolve_2904_listing_observations(self):
        import_dir = CORPUS_DIR / "import"
        files = {
            name: (import_dir / name).read_text(encoding="utf-8")
            for name in (
                "announcement_metadata.csv",
                "listing_metadata.csv",
                "shares_metadata.csv",
                "control_metadata.csv",
                "market_source_dates.csv",
            )
        }
        imported = import_real_corpus_metadata(files)
        self.assertEqual(len(imported.listings), 2904)

        by_symbol = {}
        for item in imported.listings:
            by_symbol.setdefault(item.symbol, []).append(item)

        self.assertEqual(len(by_symbol), 106)
        expected = {
            "MFRM": ("NASDAQ", 22),
            "MSCC": ("NASDAQ", 22),
            "MXIM": ("NASDAQ", 22),
            "NDSN": ("NASDAQ", 22),
            "NOW": ("NYSE", 44),
            "MCRL": ("NASDAQ", 22),
            "NATI": ("NASDAQ", 44),
            "CAT": ("NYSE", 22),
            "CNMD": ("NASDAQ", 22),
            "GILD": ("NASDAQ", 22),
            "NUAN": ("NASDAQ", 22),
            "OSK": ("NYSE", 22),
            "P": ("NYSE", 22),
            "PAY": ("NYSE", 44),
            "PBI": ("NYSE", 22),
            "PFPT": ("NASDAQ", 22),
        }
        for symbol, (exchange, count) in expected.items():
            self.assertEqual(len(by_symbol[symbol]), count)
            self.assertEqual(
                {row.primary_exchange for row in by_symbol[symbol]},
                {exchange},
            )

    def test_g2_batch_one_requirement_file_is_exactly_66_dates(self):
        path = CORPUS_DIR / "listing_requirement_batch_001.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        for row in rows:
            dates = row["required_dates"].split("|")
            self.assertEqual(len(dates), 22)
            self.assertEqual(dates[0], row["first_date"])
            self.assertEqual(dates[-1], row["last_date"])


    def test_g2_batch_two_requirement_file_is_exactly_66_dates(self):
        path = CORPUS_DIR / "listing_requirement_batch_002.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            {row["historical_symbol"] for row in rows},
            {"F", "NKE", "SBUX"},
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        for row in rows:
            dates = row["required_dates"].split("|")
            self.assertEqual(len(dates), 22)
            self.assertEqual(dates[0], row["first_date"])
            self.assertEqual(dates[-1], row["last_date"])


    def test_g2_batch_three_requirement_file_is_exactly_66_dates(self):
        path = CORPUS_DIR / "listing_requirement_batch_003.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            {row["historical_symbol"] for row in rows},
            {"BA", "DE", "HON"},
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        for row in rows:
            dates = row["required_dates"].split("|")
            self.assertEqual(len(dates), 22)
            self.assertEqual(dates[0], row["first_date"])
            self.assertEqual(dates[-1], row["last_date"])


    def test_g2_batch_four_requirement_file_is_exactly_198_dates(self):
        path = CORPUS_DIR / "listing_requirement_batch_004.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            {row["historical_symbol"] for row in rows},
            {"ADI", "JNPR", "VMW"},
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            198,
        )
        self.assertEqual(
            {row["historical_symbol"]: int(row["requirement_count"]) for row in rows},
            {"ADI": 44, "JNPR": 88, "VMW": 66},
        )


    def test_g2_batch_five_requirement_file_is_exactly_198_dates(self):
        path = CORPUS_DIR / "listing_requirement_batch_005.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            {row["historical_symbol"] for row in rows},
            {"CA", "DGI", "PNRA"},
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            198,
        )
        self.assertEqual(
            {row["historical_symbol"]: int(row["requirement_count"]) for row in rows},
            {"CA": 44, "DGI": 66, "PNRA": 88},
        )


    def test_g2_batch_six_requirement_file_is_exactly_132_dates(self):
        path = CORPUS_DIR / "listing_requirement_batch_006.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            {row["historical_symbol"] for row in rows},
            {"CGNX", "ILMN", "MDU"},
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            132,
        )


    def test_g2_batch_seven_requirement_file_is_exactly_176_dates(self):
        path = CORPUS_DIR / "listing_requirement_batch_007.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            {row["historical_symbol"] for row in rows},
            {"COLM", "CREE", "EHTH", "IDTI"},
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            176,
        )
        self.assertEqual(
            {
                row["historical_symbol"]: int(row["requirement_count"])
                for row in rows
            },
            {
                "COLM": 44,
                "CREE": 44,
                "EHTH": 44,
                "IDTI": 44,
            },
        )

    def test_g2_manifest_is_transparent_about_full_compact_index(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["listing_metadata_resolved"], 2904)
        self.assertEqual(manifest["listing_requirement_total"], 3828)
        self.assertEqual(manifest["listing_intervals_verified"], 106)
        self.assertEqual(manifest["listing_symbols_resolved"], 106)
        self.assertEqual(manifest["listing_batches_completed"], 27)
        self.assertTrue(manifest["listing_full_compact_index_loaded"])
        self.assertEqual(manifest["listing_requirement_compact_rows"], 146)
        self.assertEqual(manifest["listing_metadata_unresolved"], 924)

    def test_listing_requirement_batch_008_is_176_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_008.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["CLD", "EW", "MTH", "MUSA"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            176,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 44
            for row in rows
        ))


    def test_listing_requirement_batch_009_is_88_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_009.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["ACHC", "ACO", "AF", "AGP"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            88,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))


    def test_listing_requirement_batch_010_is_88_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_010.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["ALGN", "ALNY", "ALSN", "AMD"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            88,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))


    def test_listing_requirement_batch_011_is_66_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_011.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["BCR", "BIO", "BRKR"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))


    def test_listing_requirement_batch_012_is_66_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_012.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["BWA", "CACI", "CAG"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))


    def test_listing_requirement_batch_018_is_66_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_018.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["DNDN", "DXCM", "DYN"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))

    def test_listing_requirement_batch_019_is_66_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_019.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["EA", "ECHO", "ECOL"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))

    def test_listing_requirement_batch_020_is_66_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_020.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["FL", "FLR", "FLT"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))

    def test_g2_interval_ledger_has_89_unique_intervals(self):
        path = CORPUS_DIR / "listing_interval_evidence.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 89)
        self.assertEqual(
            len({row["interval_id"] for row in rows}),
            89,
        )
        by_symbol = {
            row["symbol"]: row
            for row in rows
        }
        self.assertEqual(by_symbol["DNDN"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["DXCM"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["DYN"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["GDI"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["GMCR"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["GME"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["EA"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["ECHO"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["ECOL"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["FL"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["FLR"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["FLT"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["HBI"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["IBKC"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["IDXX"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["IGT"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["INT"]["primary_exchange"], "NYSE")

        self.assertEqual(by_symbol["INWK"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["ISIL"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["ISSI"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["JWN"]["primary_exchange"], "NYSE")
        self.assertEqual(by_symbol["KELYA"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["KOPN"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["LRCX"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["LSCC"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["LSTR"]["primary_exchange"], "NASDAQ")
        self.assertEqual(by_symbol["MAT"]["primary_exchange"], "NASDAQ")


    def test_listing_requirement_batch_021_is_66_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_021.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["GDI", "GMCR", "GME"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            66,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))


    def test_listing_requirement_batch_024_is_220_observations(self):
        path = CORPUS_DIR / "listing_requirement_batch_024.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["INWK", "ISIL", "ISSI", "JWN", "KELYA", "KOPN", "LRCX", "LSCC", "LSTR", "MAT"],
        )
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            220,
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))


if __name__ == "__main__":
    unittest.main()
