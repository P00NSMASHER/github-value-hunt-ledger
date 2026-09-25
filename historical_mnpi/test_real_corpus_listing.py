import csv
import hashlib
import json
import unittest
from pathlib import Path

from historical_mnpi.listing_intervals import (
    ListingIntervalEvidence,
    expand_listing_intervals,
)
from historical_mnpi.metadata_resolver import MetadataDataClass
from historical_mnpi.real_corpus_import import import_real_corpus_metadata


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


def load_compact_requirements():
    with (CORPUS_DIR / "listing_requirement_index.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def expanded_requirements():
    pairs = []
    for row in load_compact_requirements():
        dates = row["required_dates"].split("|")
        if len(dates) != int(row["requirement_count"]):
            raise AssertionError(
                f"requirement_count mismatch for {row['historical_symbol']}"
            )
        pairs.extend(
            (row["historical_symbol"], day)
            for day in dates
        )
    return tuple(sorted(set(pairs)))


def load_intervals():
    with (CORPUS_DIR / "listing_interval_evidence.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))
    return tuple(
        ListingIntervalEvidence(
            interval_id=row["interval_id"],
            symbol=row["symbol"],
            primary_exchange=row["primary_exchange"],
            valid_from=row["valid_from"],
            valid_through=row["valid_through"],
            start_evidence_url=row["start_evidence_url"],
            end_evidence_url=row["end_evidence_url"],
            source_name=row["source_name"],
            data_class=MetadataDataClass(row["data_class"]),
        )
        for row in rows
    )


def load_import_bundle():
    import_dir = CORPUS_DIR / "import"
    names = (
        "announcement_metadata.csv",
        "listing_metadata.csv",
        "shares_metadata.csv",
        "control_metadata.csv",
        "market_source_dates.csv",
    )
    return import_real_corpus_metadata({
        name: (import_dir / name).read_text(encoding="utf-8")
        for name in names
    })


class RealCorpusListingTests(unittest.TestCase):
    def test_frozen_compact_requirement_index_is_complete(self):
        path = CORPUS_DIR / "listing_requirement_index.csv"
        payload = path.read_bytes()
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "b79d87d3ae51022c66f3038e73446188ca956a2187f32803707038d1cbb290b9",
        )

        rows = load_compact_requirements()
        self.assertEqual(len(rows), 146)
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            3828,
        )
        self.assertTrue(all(row["required_dates"] for row in rows))

    def test_expanded_requirement_index_has_exact_3828_unique_pairs(self):
        pairs = expanded_requirements()
        self.assertEqual(len(pairs), 3828)
        normalized = "".join(
            f"{symbol},{day}\n"
            for symbol, day in pairs
        )
        self.assertEqual(
            hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "cb00a9c2983c5ffb0f37ef3aff84ce8bcf328bd56565664e01abe0dfadde64af",
        )

    def test_first_interval_batch_expands_to_exactly_66_rows(self):
        result = expand_listing_intervals(
            expanded_requirements(),
            load_intervals(),
        )
        self.assertEqual(len(result.resolved), 66)
        self.assertEqual(len(result.unresolved), 3762)

        counts = {}
        for item in result.resolved:
            counts[item.symbol] = counts.get(item.symbol, 0) + 1
        self.assertEqual(
            counts,
            {
                "CAT": 22,
                "CNMD": 22,
                "GILD": 22,
            },
        )

        exchanges = {
            item.symbol: item.primary_exchange
            for item in result.resolved
        }
        self.assertEqual(exchanges["CAT"], "NYSE")
        self.assertEqual(exchanges["CNMD"], "NASDAQ")
        self.assertEqual(exchanges["GILD"], "NASDAQ")

    def test_listing_import_matches_interval_expansion_exactly(self):
        expansion = expand_listing_intervals(
            expanded_requirements(),
            load_intervals(),
        )
        imported = load_import_bundle()
        self.assertEqual(len(imported.listings), 66)

        expanded_rows = {
            (
                item.symbol,
                item.session_date,
                item.primary_exchange,
            )
            for item in expansion.resolved
        }
        imported_rows = {
            (
                item.symbol,
                item.session_date,
                item.primary_exchange,
            )
            for item in imported.listings
        }
        self.assertEqual(imported_rows, expanded_rows)
        self.assertEqual(len(imported_rows), 66)

    def test_interval_evidence_uses_two_public_official_boundaries(self):
        intervals = load_intervals()
        self.assertEqual(len(intervals), 3)
        for item in intervals:
            self.assertTrue(
                item.start_evidence_url.startswith("https://www.sec.gov/")
            )
            self.assertTrue(
                item.end_evidence_url.startswith("https://www.sec.gov/")
            )
            self.assertNotEqual(
                item.start_evidence_url,
                item.end_evidence_url,
            )
            self.assertEqual(
                item.data_class,
                MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
            )

    def test_manifest_tracks_first_g2_batch(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["listing_metadata_total"], 3828)
        self.assertEqual(manifest["listing_metadata_resolved"], 66)
        self.assertEqual(manifest["listing_metadata_unresolved"], 3762)
        self.assertEqual(manifest["listing_interval_batches_completed"], 1)
        self.assertEqual(
            manifest["listing_symbols_with_resolved_intervals"],
            3,
        )


if __name__ == "__main__":
    unittest.main()
