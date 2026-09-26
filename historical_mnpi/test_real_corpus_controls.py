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
            manifest["control_candidate_universe_dates_defined"],
            72,
        )
        self.assertEqual(
            manifest["control_candidate_memberships_defined"],
            3254,
        )
        self.assertEqual(
            manifest["control_source_variable_map_rows"],
            7,
        )
        self.assertEqual(
            manifest["control_acquisition_requirement_rows"],
            504,
        )
        self.assertTrue(manifest["control_acquisition_packet_ready"])
        self.assertTrue(manifest["control_external_import_contract_ready"])
        self.assertEqual(manifest["control_external_template_file_count"], 3)
        self.assertEqual(manifest["control_external_template_rows_loaded"], 0)
        self.assertEqual(
            manifest["control_candidate_source_revision"],
            "c23c7d79d067a79d70cf20e31b072d3703497eae",
        )
        self.assertEqual(
            manifest["control_candidate_sample_blob_sha"],
            "bbb68de172f7ab2104714513a72547f3dad3b86c",
        )
        self.assertFalse(manifest["live_use_allowed"])


    def test_retrospective_candidate_membership_index_is_complete_definition_only(self):
        path = CORPUS_DIR / "control_candidate_membership_index.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 72)
        self.assertEqual(
            len({row["control_date"] for row in rows}),
            72,
        )
        counts = [int(row["candidate_symbol_count"]) for row in rows]
        self.assertEqual(sum(counts), 3254)
        self.assertEqual(min(counts), 1)
        self.assertEqual(max(counts), 180)

        for row in rows:
            symbols = row["candidate_symbols"].split("|")
            self.assertEqual(
                symbols,
                sorted(set(symbols)),
            )
            self.assertEqual(
                len(symbols),
                int(row["candidate_symbol_count"]),
            )
            self.assertEqual(
                row["source_revision"],
                "c23c7d79d067a79d70cf20e31b072d3703497eae",
            )
            self.assertEqual(
                row["source_blob_sha"],
                "bbb68de172f7ab2104714513a72547f3dad3b86c",
            )
            self.assertEqual(
                row["source_kind"],
                "RETROSPECTIVE_SAMPLE_FIRMS",
            )
            self.assertEqual(
                row["admissibility_status"],
                "DEFINITION_ONLY_NOT_POINT_IN_TIME",
            )
            self.assertEqual(
                row["blocking_reason"],
                "RETROSPECTIVE_SAMPLE_NOT_POINT_IN_TIME",
            )

    def test_control_source_variable_map_matches_study_contract(self):
        path = CORPUS_DIR / "control_source_variable_map.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 7)
        by_family = {
            row["source_family"]: row
            for row in rows
        }
        self.assertEqual(
            set(by_family),
            {
                "CRSP",
                "IBES",
                "TAQ",
                "RAVENPACK",
                "MARKIT",
                "OPTIONMETRICS",
                "THOMSON_REUTERS_13F",
            },
        )
        self.assertEqual(
            by_family["CRSP"]["required_variable_anchors"],
            "lnMCAP|Beta_SPY|invPRC",
        )
        self.assertEqual(
            by_family["IBES"]["required_variable_anchors"],
            "lnnumest",
        )
        self.assertEqual(
            by_family["RAVENPACK"]["required_variable_anchors"],
            "ln_Story_Count_Relevant",
        )
        self.assertEqual(
            by_family["MARKIT"]["required_variable_anchors"],
            "DCBS",
        )
        self.assertEqual(
            by_family["THOMSON_REUTERS_13F"]["required_variable_anchors"],
            "IO",
        )
        self.assertEqual(
            by_family["TAQ"]["required_variable_anchors"],
            "",
        )
        self.assertEqual(
            by_family["OPTIONMETRICS"]["required_variable_anchors"],
            "",
        )

    def test_control_acquisition_packet_is_72_dates_times_7_sources(self):
        membership_path = (
            CORPUS_DIR / "control_candidate_membership_index.csv"
        )
        with membership_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            membership = list(csv.DictReader(handle))
        expected_counts = {
            row["control_date"]: row["candidate_symbol_count"]
            for row in membership
        }

        path = CORPUS_DIR / "control_acquisition_requirements.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 504)
        self.assertEqual(
            len({row["control_date"] for row in rows}),
            72,
        )
        expected_families = {
            "CRSP",
            "IBES",
            "TAQ",
            "RAVENPACK",
            "MARKIT",
            "OPTIONMETRICS",
            "THOMSON_REUTERS_13F",
        }
        by_date = {}
        for row in rows:
            by_date.setdefault(row["control_date"], set()).add(
                row["source_family"]
            )
            self.assertEqual(
                row["candidate_symbol_count"],
                expected_counts[row["control_date"]],
            )
            self.assertEqual(
                row["status"],
                "EXTERNAL_DATA_REQUIRED",
            )
            self.assertEqual(
                row["blocking_reason"],
                "AUTHORIZED_POINT_IN_TIME_SOURCE_NOT_LOADED",
            )

        self.assertEqual(set(by_date), set(expected_counts))
        self.assertTrue(all(
            families == expected_families
            for families in by_date.values()
        ))


if __name__ == "__main__":
    unittest.main()
