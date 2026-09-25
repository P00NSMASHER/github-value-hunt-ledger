import csv
import json
import unittest
from pathlib import Path

from historical_mnpi.listing_intervals import (
    expand_listing_intervals,
    parse_listing_intervals_csv,
)
from historical_mnpi.listing_requirements import (
    EXPECTED_EXPANDED_PAIR_SHA256,
    expand_listing_requirements,
    expanded_pair_sha256,
    parse_listing_requirement_index,
)


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


class RealCorpusListingTests(unittest.TestCase):
    def _requirements(self):
        rows = parse_listing_requirement_index(
            (CORPUS_DIR / "listing_requirement_index.csv").read_text(
                encoding="utf-8"
            )
        )
        return rows, expand_listing_requirements(rows)

    def _intervals(self):
        return parse_listing_intervals_csv(
            (CORPUS_DIR / "listing_intervals.csv").read_text(
                encoding="utf-8"
            )
        )

    def test_requirement_index_is_frozen_to_recovered_gate(self):
        rows, requirements = self._requirements()
        self.assertEqual(len(rows), 146)
        self.assertEqual(len(requirements), 3828)
        self.assertEqual(len(set(requirements)), 3828)
        self.assertEqual(
            expanded_pair_sha256(rows),
            EXPECTED_EXPANDED_PAIR_SHA256,
        )

    def test_current_intervals_resolve_exactly_1496_observations(self):
        _, requirements = self._requirements()
        intervals = self._intervals()
        expansion = expand_listing_intervals(
            requirements,
            intervals,
        )

        self.assertEqual(len(intervals), 45)
        self.assertEqual(len(expansion.resolved), 1496)
        self.assertEqual(len(expansion.unresolved), 2332)

        new_symbols = {"CLD", "EW", "MTH", "MUSA"}
        new_rows = [
            row for row in expansion.resolved
            if row.symbol in new_symbols
        ]
        self.assertEqual(len(new_rows), 176)
        for symbol in new_symbols:
            self.assertEqual(
                sum(row.symbol == symbol for row in new_rows),
                44,
            )
            self.assertEqual(
                {
                    row.primary_exchange
                    for row in new_rows
                    if row.symbol == symbol
                },
                {"NYSE"},
            )

    def test_materialized_listing_metadata_matches_interval_expansion(self):
        _, requirements = self._requirements()
        expansion = expand_listing_intervals(
            requirements,
            self._intervals(),
        )

        metadata_path = CORPUS_DIR / "import" / "listing_metadata.csv"
        with metadata_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            materialized = list(csv.DictReader(handle))

        expected = {
            (
                row.symbol,
                row.session_date,
                row.primary_exchange,
                row.evidence.evidence_id,
            )
            for row in expansion.resolved
        }
        actual = {
            (
                row["symbol"],
                row["session_date"],
                row["primary_exchange"],
                row["evidence_id"],
            )
            for row in materialized
        }

        self.assertEqual(len(materialized), 1496)
        self.assertEqual(len(actual), 1496)
        self.assertEqual(actual, expected)
        self.assertTrue(all(
            row["source_kind"] == "OFFICIAL_LISTING_HISTORY"
            for row in materialized
        ))
        self.assertTrue(all(
            row["data_class"]
            == "PUBLIC_OR_AUTHORIZED_HISTORICAL"
            for row in materialized
        ))

    def test_manifest_matches_current_listing_expansion(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            manifest["listing_intervals_verified"],
            42,
        )
        self.assertEqual(
            manifest["listing_metadata_resolved"],
            1496,
        )
        self.assertEqual(
            manifest["listing_metadata_unresolved"],
            2332,
        )
        self.assertEqual(
            manifest["listing_metadata_resolved"]
            + manifest["listing_metadata_unresolved"],
            3828,
        )


if __name__ == "__main__":
    unittest.main()
