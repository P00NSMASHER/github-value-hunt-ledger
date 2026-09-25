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
                "announcement_rows": 2,
                "listing_rows": 0,
                "shares_rows": 0,
                "control_rows": 0,
                "market_source_date_rows": 0,
                "import_hash": imported.proof_hash,
                "live_use_allowed": False,
            },
        )

        self.assertEqual(len(imported.announcements), 2)
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
        self.assertEqual(manifest["announcement_exact_resolved"], 2)
        self.assertEqual(manifest["listing_metadata_resolved"], 0)
        self.assertEqual(manifest["shares_metadata_resolved"], 0)
        self.assertEqual(manifest["control_dates_resolved"], 0)
        self.assertFalse(manifest["live_use_allowed"])
        self.assertIn("research/compliance", manifest["purpose"])


if __name__ == "__main__":
    unittest.main()
