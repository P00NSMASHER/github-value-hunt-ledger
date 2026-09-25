import csv
import json
import unittest
from pathlib import Path

from historical_mnpi.listing_intervals import (
    expand_listing_intervals,
    parse_listing_interval_csv,
)
from historical_mnpi.real_corpus_import import (
    import_real_corpus_metadata,
)


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


class RealCorpusListingTests(unittest.TestCase):
    def _requirement_rows(self):
        with (CORPUS_DIR / "listing_requirement_index.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            return list(csv.DictReader(handle))

    def _requirements(self):
        pairs = []
        for row in self._requirement_rows():
            for day in row["required_dates"].split("|"):
                pairs.append((row["historical_symbol"], day))
        return tuple(pairs)

    def _intervals(self):
        return parse_listing_interval_csv(
            (CORPUS_DIR / "listing_intervals.csv").read_text(
                encoding="utf-8"
            )
        )

    def test_compact_requirement_index_reconstructs_3828_rows(self):
        rows = self._requirement_rows()
        self.assertEqual(len(rows), 146)
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            3828,
        )
        requirements = self._requirements()
        self.assertEqual(len(requirements), 3828)
        self.assertEqual(len(set(requirements)), 3828)
        for row in rows:
            dates = row["required_dates"].split("|")
            self.assertEqual(len(dates), int(row["requirement_count"]))
            self.assertEqual(dates[0], row["first_date"])
            self.assertEqual(dates[-1], row["last_date"])

    def test_first_three_listing_batches_resolve_exactly_198_rows(self):
        expansion = expand_listing_intervals(
            self._requirements(),
            self._intervals(),
        )
        self.assertEqual(len(expansion.resolved), 198)
        self.assertEqual(len(expansion.unresolved), 3630)
        self.assertEqual(
            {item.symbol for item in expansion.resolved},
            {"BA", "CAT", "CNMD", "DE", "F", "GILD", "HON", "NKE", "SBUX"},
        )
        self.assertEqual(
            {
                item.symbol: item.primary_exchange
                for item in expansion.resolved
            },
            {
                "BA": "NYSE",
                "CAT": "NYSE",
                "CNMD": "NASDAQ",
                "DE": "NYSE",
                "F": "NYSE",
                "GILD": "NASDAQ",
                "HON": "NYSE",
                "NKE": "NYSE",
                "SBUX": "NASDAQ",
            },
        )


    def test_third_listing_batch_is_exactly_66_rows(self):
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

    def test_committed_listing_rows_match_interval_expansion(self):
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
        expansion = expand_listing_intervals(
            self._requirements(),
            self._intervals(),
        )

        committed = {
            (
                item.symbol,
                item.session_date,
                item.primary_exchange,
                item.evidence.evidence_id,
            )
            for item in imported.listings
        }
        expected = {
            (
                item.symbol,
                item.session_date,
                item.primary_exchange,
                item.evidence.evidence_id,
            )
            for item in expansion.resolved
        }
        self.assertEqual(len(committed), 198)
        self.assertEqual(committed, expected)

    def test_manifest_tracks_g2_first_three_batches(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["listing_requirement_total"], 3828)
        self.assertEqual(manifest["listing_metadata_resolved"], 198)
        self.assertEqual(manifest["listing_intervals_verified"], 9)
        self.assertEqual(manifest["listing_symbols_resolved"], 9)


if __name__ == "__main__":
    unittest.main()
