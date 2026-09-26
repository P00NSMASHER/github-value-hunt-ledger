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
    def test_g3_shares_resolves_all_3828_requirements(self):
        imported = load_import_bundle()
        requirements = expanded_requirements()

        self.assertEqual(len(imported.shares), 146)
        self.assertEqual(
            len({item.symbol for item in imported.shares}),
            146,
        )
        self.assertEqual(len(requirements), 3828)

        resolutions = tuple(
            resolve_shares_outstanding(
                symbol,
                day,
                imported.shares,
            )
            for symbol, day in requirements
        )

        self.assertEqual(
            sum(
                item.state is ResolutionState.RESOLVED
                for item in resolutions
            ),
            3828,
        )
        self.assertFalse(any(
            item.state is ResolutionState.UNRESOLVED
            for item in resolutions
        ))
        self.assertFalse(any(
            item.state is ResolutionState.CONFLICT
            for item in resolutions
        ))

        by_symbol = Counter(
            item.symbol
            for item in resolutions
            if item.state is ResolutionState.RESOLVED
        )
        self.assertEqual(len(by_symbol), 146)
        self.assertEqual(sum(by_symbol.values()), 3828)
        self.assertEqual(by_symbol["JNPR"], 88)
        self.assertEqual(by_symbol["PNRA"], 88)
        self.assertEqual(by_symbol["DGI"], 66)
        self.assertEqual(by_symbol["VMW"], 66)
        self.assertEqual(by_symbol["IDTI"], 44)
        self.assertEqual(by_symbol["ILMN"], 44)
        self.assertEqual(by_symbol["WTS"], 22)

    def test_all_share_facts_preserve_official_sec_provenance(self):
        imported = load_import_bundle()
        self.assertEqual(len(imported.shares), 146)

        for item in imported.shares:
            self.assertEqual(
                item.evidence.source_kind,
                MetadataSourceKind.PUBLIC_EFFECTIVE_DATED_SHARES,
            )
            self.assertEqual(
                item.evidence.data_class,
                MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
            )
            self.assertTrue(
                item.evidence.evidence_id.startswith("shares:")
            )
            self.assertIn("SEC ", item.evidence.source_name)
            self.assertIn("sec.gov", item.evidence.source_name.lower())
            self.assertGreater(int(item.shares_outstanding), 0)
            datetime.fromisoformat(
                item.public_availability_timestamp
            )

    def test_each_share_fact_is_public_before_first_required_session(self):
        imported = load_import_bundle()
        first_required = {}
        for symbol, day in expanded_requirements():
            first_required.setdefault(symbol, day)

        self.assertEqual(len(first_required), 146)
        for item in imported.shares:
            self.assertIn(item.symbol, first_required)
            availability_day = datetime.fromisoformat(
                item.public_availability_timestamp
            ).date().isoformat()
            first_day = first_required[item.symbol]

            self.assertLessEqual(item.effective_date, first_day)
            self.assertLessEqual(availability_day, first_day)

            first = resolve_shares_outstanding(
                item.symbol,
                first_day,
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
            "JNPR": (
                "2011-02-18",
                "534922000",
                "0001445305-11-000332",
            ),
            "IDTI": (
                "2014-10-31",
                "148650153",
                "0000703361-14-000038",
            ),
            "ILMN": (
                "2014-10-08",
                "142000000",
                "0001110803-14-000363",
            ),
            "F": (
                "2014-10-24",
                "3848687417",
                "0000037996-14-000057",
            ),
            "KELYA": (
                "2013-02-03",
                "37175755",
                "0001437749-13-001540",
            ),
            "MKC": (
                "2012-12-31",
                "132678095",
                "0000063754-13-000002",
            ),
            "SKX": (
                "2015-02-17",
                "52021294",
                "0001193125-15-068511",
            ),
            "URI": (
                "2014-10-13",
                "99808171",
                "0001067701-14-000033",
            ),
            "VDSI": (
                "2011-07-29",
                "38043306",
                "0001193125-11-211583",
            ),
            "VEEV": (
                "2014-11-28",
                "130594979",
                "0001564590-14-006187",
            ),
            "WTS": (
                "2014-10-31",
                "35129832",
                "0001104659-14-076471",
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

    def test_manifest_tracks_complete_g3_shares_coverage(self):
        manifest = json.loads(
            (CORPUS_DIR / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["shares_requirement_total"], 3828)
        self.assertEqual(manifest["shares_facts_verified"], 146)
        self.assertEqual(manifest["shares_batches_completed"], 8)
        self.assertEqual(manifest["shares_symbols_resolved"], 146)
        self.assertEqual(manifest["shares_metadata_resolved"], 3828)
        self.assertEqual(manifest["shares_metadata_unresolved"], 0)
        self.assertEqual(
            manifest["shares_metadata_resolved"],
            manifest["shares_requirement_total"],
        )
        self.assertFalse(manifest["live_use_allowed"])


if __name__ == "__main__":
    unittest.main()
