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
    def test_g3_shares_reaches_exactly_fifty_percent_coverage(self):
        imported = load_import_bundle()
        requirements = expanded_requirements()
        self.assertEqual(len(imported.shares), 61)
        self.assertEqual(len(requirements), 3828)

        resolutions = tuple(
            resolve_shares_outstanding(
                symbol,
                day,
                imported.shares,
            )
            for symbol, day in requirements
        )
        resolved = tuple(
            item
            for item in resolutions
            if item.state is ResolutionState.RESOLVED
        )
        unresolved = tuple(
            item
            for item in resolutions
            if item.state is ResolutionState.UNRESOLVED
        )

        self.assertEqual(len(resolved), 1914)
        self.assertEqual(len(unresolved), 1914)
        self.assertEqual(len(resolved) * 2, len(requirements))
        self.assertFalse(any(
            item.state is ResolutionState.CONFLICT
            for item in resolutions
        ))

        by_symbol = Counter(item.symbol for item in resolved)
        self.assertEqual(len(by_symbol), 61)
        self.assertEqual(sum(by_symbol.values()), 1914)
        self.assertEqual(by_symbol["JNPR"], 88)
        self.assertEqual(by_symbol["PNRA"], 88)
        self.assertEqual(by_symbol["DGI"], 66)
        self.assertEqual(by_symbol["VMW"], 66)
        self.assertEqual(by_symbol["ADI"], 44)
        self.assertEqual(by_symbol["JWN"], 22)
        self.assertEqual(by_symbol["MCRI"], 22)
        self.assertEqual(by_symbol["MCRL"], 22)

    def test_all_current_share_facts_preserve_public_sec_provenance(self):
        imported = load_import_bundle()
        self.assertEqual(len(imported.shares), 61)

        for item in imported.shares:
            self.assertEqual(
                item.evidence.source_kind,
                MetadataSourceKind.PUBLIC_EFFECTIVE_DATED_SHARES,
            )
            self.assertEqual(
                item.evidence.data_class,
                MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
            )
            self.assertTrue(item.evidence.evidence_id.startswith("shares:"))
            self.assertIn("SEC EDGAR", item.evidence.source_name)
            self.assertIn("https://www.sec.gov/", item.evidence.source_name)
            self.assertGreater(int(item.shares_outstanding), 0)
            datetime.fromisoformat(item.public_availability_timestamp)

    def test_each_current_fact_was_public_before_first_required_session(self):
        imported = load_import_bundle()
        first_required = {}
        for symbol, day in expanded_requirements():
            first_required.setdefault(symbol, day)

        self.assertEqual(len(imported.shares), 61)
        for item in imported.shares:
            self.assertIn(item.symbol, first_required)
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
                first.rejected_future_evidence_hashes,
                (),
            )

    def test_anchor_share_facts_remain_exact(self):
        imported = load_import_bundle()
        by_symbol = {
            item.symbol: item
            for item in imported.shares
        }
        expected = {
            "ACHC": (
                "2015-02-27",
                "66452931",
                "0001193125-15-069793",
            ),
            "ALNY": (
                "2014-10-31",
                "76931090",
                "0001193125-14-399866",
            ),
            "JNPR": (
                "2011-02-18",
                "534922000",
                "0001445305-11-000332",
            ),
            "MDU": (
                "2014-10-31",
                "194106937",
                "0000067716-14-000123",
            ),
            "CAMP": (
                "2011-03-31",
                "28128304",
                "0001206774-11-001038",
            ),
            "MAT": (
                "2015-02-13",
                "338254021",
                "0001193125-15-062193",
            ),
            "JWN": (
                "2014-03-10",
                "189692666",
                "0000072333-14-000036",
            ),
            "MCRI": (
                "2013-03-05",
                "16147324",
                "0001104659-13-021105",
            ),
            "MCRL": (
                "2013-03-11",
                "58338520",
                "0000932111-13-000011",
            ),
        }

        for symbol, (
            effective_date,
            shares,
            accession,
        ) in expected.items():
            item = by_symbol[symbol]
            self.assertEqual(item.effective_date, effective_date)
            self.assertEqual(item.shares_outstanding, shares)
            self.assertIn(accession, item.evidence.evidence_id)
            self.assertIn(accession, item.evidence.source_name)

    def test_manifest_tracks_exact_fifty_percent_g3_milestone(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["shares_requirement_total"], 3828)
        self.assertEqual(manifest["shares_facts_verified"], 61)
        self.assertEqual(manifest["shares_batches_completed"], 5)
        self.assertEqual(manifest["shares_symbols_resolved"], 61)
        self.assertEqual(manifest["shares_metadata_resolved"], 1914)
        self.assertEqual(manifest["shares_metadata_unresolved"], 1914)
        self.assertEqual(
            manifest["shares_metadata_resolved"] * 2,
            manifest["shares_requirement_total"],
        )
        self.assertFalse(manifest["live_use_allowed"])


if __name__ == "__main__":
    unittest.main()
