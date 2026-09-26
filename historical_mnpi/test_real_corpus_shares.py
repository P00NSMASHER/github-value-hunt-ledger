import csv
import json
import unittest
from collections import Counter
from datetime import datetime
from pathlib import Path

from historical_mnpi.metadata_resolver import (
    MetadataDataClass,
    MetadataSourceKind,
    ResolutionState,
    resolve_shares_outstanding,
)
from historical_mnpi.real_corpus_import import import_real_corpus_metadata


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


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


def expanded_requirements():
    result = []
    with (CORPUS_DIR / "listing_requirement_index.csv").open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle):
            dates = row["required_dates"].split("|")
            if len(dates) != int(row["requirement_count"]):
                raise AssertionError(
                    f"requirement_count mismatch for {row['historical_symbol']}"
                )
            result.extend(
                (row["historical_symbol"], day)
                for day in dates
            )
    return tuple(result)


class RealCorpusSharesTests(unittest.TestCase):
    def test_g3_batch_one_resolves_154_of_3828_requirements(self):
        imported = load_import_bundle()
        self.assertEqual(len(imported.shares), 6)

        resolved = []
        unresolved = []
        for symbol, day in expanded_requirements():
            item = resolve_shares_outstanding(
                symbol,
                day,
                imported.shares,
            )
            if item.state is ResolutionState.RESOLVED:
                resolved.append(item)
            else:
                unresolved.append(item)

        self.assertEqual(len(resolved), 154)
        self.assertEqual(len(unresolved), 3674)

        by_symbol = Counter(item.symbol for item in resolved)
        self.assertEqual(
            dict(by_symbol),
            {
                "ACHC": 22,
                "ACO": 22,
                "ADI": 44,
                "AF": 22,
                "AGP": 22,
                "ALGN": 22,
            },
        )

    def test_g3_batch_one_preserves_exact_sec_share_facts(self):
        imported = load_import_bundle()
        by_symbol = {
            item.symbol: item
            for item in imported.shares
        }
        expected = {
            "ACHC": (
                "2015-02-27",
                "66452931",
                "2015-02-27T16:16:15-05:00",
                "0001193125-15-069793",
            ),
            "ACO": (
                "2012-10-31",
                "31959139",
                "2012-11-07T06:06:25-05:00",
                "0001140361-12-045926",
            ),
            "ADI": (
                "2014-11-01",
                "311204926",
                "2014-12-10T16:45:07-05:00",
                "0000006281-14-000039",
            ),
            "AF": (
                "2011-10-27",
                "98537391",
                "2011-11-04T15:00:49-04:00",
                "0001144204-11-061380",
            ),
            "AGP": (
                "2011-07-29",
                "49647545",
                "2011-08-04T16:06:28-04:00",
                "0000950123-11-072902",
            ),
            "ALGN": (
                "2013-07-26",
                "79837318",
                "2013-08-02T16:08:53-04:00",
                "0001097149-13-000033",
            ),
        }

        self.assertEqual(set(by_symbol), set(expected))
        for symbol, (
            effective_date,
            shares,
            availability,
            accession,
        ) in expected.items():
            item = by_symbol[symbol]
            self.assertEqual(item.effective_date, effective_date)
            self.assertEqual(item.shares_outstanding, shares)
            self.assertEqual(
                item.public_availability_timestamp,
                availability,
            )
            self.assertEqual(
                item.evidence.source_kind,
                MetadataSourceKind.PUBLIC_EFFECTIVE_DATED_SHARES,
            )
            self.assertEqual(
                item.evidence.data_class,
                MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
            )
            self.assertIn(accession, item.evidence.evidence_id)
            self.assertIn(accession, item.evidence.source_name)
            self.assertIn("https://www.sec.gov/", item.evidence.source_name)

    def test_each_batch_one_fact_was_public_before_first_required_session(self):
        imported = load_import_bundle()
        first_required = {}
        for symbol, day in expanded_requirements():
            first_required.setdefault(symbol, day)

        for item in imported.shares:
            availability_day = datetime.fromisoformat(
                item.public_availability_timestamp
            ).date().isoformat()
            self.assertLessEqual(
                item.effective_date,
                first_required[item.symbol],
            )
            self.assertLessEqual(
                availability_day,
                first_required[item.symbol],
            )
            first = resolve_shares_outstanding(
                item.symbol,
                first_required[item.symbol],
                imported.shares,
            )
            self.assertEqual(first.state, ResolutionState.RESOLVED)
            self.assertEqual(
                first.shares_outstanding,
                item.shares_outstanding,
            )
            self.assertEqual(
                first.rejected_future_evidence_hashes,
                (),
            )

    def test_manifest_tracks_g3_batch_one_progress(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["shares_requirement_total"], 3828)
        self.assertEqual(manifest["shares_facts_verified"], 6)
        self.assertEqual(manifest["shares_batches_completed"], 1)
        self.assertEqual(manifest["shares_symbols_resolved"], 6)
        self.assertEqual(manifest["shares_metadata_resolved"], 154)
        self.assertEqual(manifest["shares_metadata_unresolved"], 3674)
        self.assertFalse(manifest["live_use_allowed"])


if __name__ == "__main__":
    unittest.main()
