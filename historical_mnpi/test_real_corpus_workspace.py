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
                "announcement_rows": 20,
                "listing_rows": 0,
                "shares_rows": 0,
                "control_rows": 0,
                "market_source_date_rows": 0,
                "import_hash": imported.proof_hash,
                "live_use_allowed": False,
            },
        )

        self.assertEqual(len(imported.announcements), 20)
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
        self.assertEqual(manifest["announcement_exact_resolved"], 20)
        self.assertEqual(manifest["listing_metadata_resolved"], 0)
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
            4,
        )
        self.assertEqual(
            manifest["announcement_events_reviewed_in_batch_sequence"],
            120,
        )
        self.assertEqual(
            manifest["announcement_unresolved_after_batch_review"],
            104,
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


if __name__ == "__main__":
    unittest.main()
