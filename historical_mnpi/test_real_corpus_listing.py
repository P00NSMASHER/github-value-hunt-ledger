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
    with (CORPUS_DIR / "listing_intervals.csv").open(
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
    def test_compact_requirement_index_is_complete(self):
        rows = load_compact_requirements()
        self.assertEqual(len(rows), 146)
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            3828,
        )
        self.assertTrue(all(row["required_dates"] for row in rows))
        self.assertTrue(all(
            len(row["required_dates"].split("|"))
            == int(row["requirement_count"])
            for row in rows
        ))

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

    def test_verified_intervals_expand_to_current_3190_rows(self):
        intervals = load_intervals()
        self.assertEqual(len(intervals), 118)

        result = expand_listing_intervals(
            expanded_requirements(),
            intervals,
        )
        self.assertEqual(len(result.resolved), 3190)
        self.assertEqual(len(result.unresolved), 638)
        self.assertEqual(
            len({item.symbol for item in result.resolved}),
            118,
        )

        # Preserve known anchor intervals from the first verified group.
        exchanges = {
            item.symbol: item.primary_exchange
            for item in result.resolved
        }
        self.assertEqual(exchanges["CAT"], "NYSE")
        self.assertEqual(exchanges["CNMD"], "NASDAQ")
        self.assertEqual(exchanges["GILD"], "NASDAQ")
        self.assertEqual(exchanges["GDI"], "NYSE")
        self.assertEqual(exchanges["GMCR"], "NASDAQ")
        self.assertEqual(exchanges["GME"], "NYSE")
        self.assertEqual(exchanges["HBI"], "NYSE")
        self.assertEqual(exchanges["IBKC"], "NASDAQ")
        self.assertEqual(exchanges["IDXX"], "NASDAQ")
        self.assertEqual(exchanges["IGT"], "NYSE")
        self.assertEqual(exchanges["INT"], "NYSE")
        self.assertEqual(exchanges["NUAN"], "NASDAQ")
        self.assertEqual(exchanges["OSK"], "NYSE")
        self.assertEqual(exchanges["P"], "NYSE")
        self.assertEqual(exchanges["PAY"], "NYSE")
        self.assertEqual(exchanges["PBI"], "NYSE")
        self.assertEqual(exchanges["PFPT"], "NASDAQ")
        self.assertEqual(exchanges["MCRI"], "NASDAQ")
        self.assertEqual(exchanges["POWI"], "NASDAQ")
        self.assertEqual(exchanges["PRU"], "NYSE")
        self.assertEqual(exchanges["PVH"], "NYSE")
        self.assertEqual(exchanges["QLIK"], "NASDAQ")
        self.assertEqual(exchanges["R"], "NYSE")
        self.assertEqual(exchanges["PLL"], "NYSE")
        self.assertEqual(exchanges["RES"], "NYSE")
        self.assertEqual(exchanges["RH"], "NYSE")
        self.assertEqual(exchanges["ROG"], "NYSE")
        self.assertEqual(exchanges["ROL"], "NYSE")
        self.assertEqual(exchanges["ROVI"], "NASDAQ")

    def test_listing_import_matches_interval_expansion_exactly(self):
        expansion = expand_listing_intervals(
            expanded_requirements(),
            load_intervals(),
        )
        imported = load_import_bundle()
        self.assertEqual(len(imported.listings), 3190)

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
        self.assertEqual(len(imported_rows), 3190)

    def test_interval_evidence_is_public_authorized_and_two_boundary(self):
        intervals = load_intervals()
        self.assertEqual(len(intervals), 118)
        for item in intervals:
            self.assertTrue(item.start_evidence_url.startswith("https://"))
            self.assertTrue(item.end_evidence_url.startswith("https://"))
            self.assertNotEqual(
                item.start_evidence_url,
                item.end_evidence_url,
            )
            self.assertEqual(
                item.data_class,
                MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
            )

    def test_manifest_tracks_restored_g2_state(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["listing_requirement_total"], 3828)
        self.assertEqual(manifest["listing_requirement_compact_rows"], 146)
        self.assertTrue(manifest["listing_full_compact_index_loaded"])
        self.assertEqual(manifest["listing_metadata_resolved"], 3190)
        self.assertEqual(manifest["listing_metadata_unresolved"], 638)
        self.assertEqual(manifest["listing_intervals_verified"], 118)
        self.assertEqual(manifest["listing_symbols_resolved"], 118)
        self.assertEqual(manifest["listing_batches_completed"], 29)


    def test_batch_23_receipt_covers_five_22_row_symbols(self):
        path = CORPUS_DIR / "listing_requirement_batch_023.csv"
        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            ["HBI", "IBKC", "IDXX", "IGT", "INT"],
        )
        self.assertTrue(all(
            int(row["requirement_count"]) == 22
            for row in rows
        ))
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            110,
        )


if __name__ == "__main__":
    unittest.main()
