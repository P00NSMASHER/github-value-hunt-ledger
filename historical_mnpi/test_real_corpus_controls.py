import csv
import json
import unittest
from pathlib import Path

from historical_mnpi.real_corpus_import import import_real_corpus_metadata


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


class RealCorpusControlTests(unittest.TestCase):
    def test_g4_requirement_index_covers_all_72_control_dates(self):
        with (CORPUS_DIR / "control_requirement_index.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        with (CORPUS_DIR / "events.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            events = list(csv.DictReader(handle))

        expected_dates = sorted({
            row["first_trade_date"]
            for row in events
        })
        actual_dates = [row["control_date"] for row in rows]

        self.assertEqual(len(rows), 72)
        self.assertEqual(len(set(actual_dates)), 72)
        self.assertEqual(actual_dates, expected_dates)
        self.assertEqual(
            sum(int(row["event_count"]) for row in rows),
            174,
        )

    def test_all_72_dates_fail_closed_on_point_in_time_control_evidence(self):
        with (CORPUS_DIR / "control_requirement_index.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        expected_reasons = {
            "RETROSPECTIVE_SAMPLE_NOT_POINT_IN_TIME",
            "POINT_IN_TIME_CONTROL_UNIVERSE_MISSING",
            "PRE_EVENT_COVARIATES_NOT_PROVEN_COMPLETE",
        }
        expected_families = {
            "CRSP",
            "IBES",
            "TAQ",
            "RAVENPACK",
            "MARKIT",
            "OPTIONMETRICS",
            "THOMSON_REUTERS_13F",
        }

        for row in rows:
            self.assertEqual(
                row["review_status"],
                "BLOCKED_POINT_IN_TIME_COVARIATES",
            )
            self.assertEqual(
                set(row["blocking_reasons"].split("|")),
                expected_reasons,
            )
            self.assertEqual(
                set(row["required_covariate_families"].split("|")),
                expected_families,
            )
            self.assertEqual(
                row["candidate_universe_source"],
                "vgreg/hacked_earnings_jfe:Data/SampleFirms.csv",
            )
            self.assertEqual(
                row["candidate_universe_revision"],
                "c23c7d79d067a79d70cf20e31b072d3703497eae",
            )
            self.assertEqual(
                row["candidate_universe_blob_sha"],
                "bbb68de172f7ab2104714513a72547f3dad3b86c",
            )

    def test_control_import_stays_empty_until_point_in_time_gate_closes(self):
        import_dir = CORPUS_DIR / "import"
        names = (
            "announcement_metadata.csv",
            "listing_metadata.csv",
            "shares_metadata.csv",
            "control_metadata.csv",
            "market_source_dates.csv",
        )
        imported = import_real_corpus_metadata({
            name: (import_dir / name).read_text(encoding="utf-8")
            for name in names
        })
        self.assertEqual(imported.controls, ())

        with (import_dir / "control_metadata.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows, [])

    def test_manifest_records_reviewed_but_unresolved_g4_state(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["control_requirement_total"], 72)
        self.assertEqual(manifest["control_dates_reviewed"], 72)
        self.assertEqual(manifest["control_dates_blocked"], 72)
        self.assertEqual(
            manifest["control_review_batches_completed"],
            1,
        )
        self.assertEqual(manifest["control_dates_resolved"], 0)
        self.assertEqual(manifest["control_metadata_unresolved"], 72)
        self.assertEqual(
            manifest["control_builder_contract_version"],
            "g4-point-in-time-v1",
        )
        self.assertEqual(
            manifest["control_required_source_family_count"],
            7,
        )
        self.assertEqual(
            manifest["control_required_variable_anchor_count"],
            7,
        )
        self.assertTrue(manifest["control_builder_ready"])
        self.assertEqual(
            manifest["control_external_point_in_time_rows_loaded"],
            0,
        )
        self.assertEqual(
            manifest["control_candidate_source_revision"],
            "c23c7d79d067a79d70cf20e31b072d3703497eae",
        )
        self.assertEqual(
            manifest["control_candidate_sample_blob_sha"],
            "bbb68de172f7ab2104714513a72547f3dad3b86c",
        )
        self.assertFalse(manifest["live_use_allowed"])


if __name__ == "__main__":
    unittest.main()
