import csv
import unittest
from pathlib import Path

from historical_mnpi.listing_intervals import (
    ListingIntervalEvidence,
    expand_listing_intervals,
    parse_listing_interval_csv,
)
from historical_mnpi.listing_requirements import (
    expand_listing_requirements,
    parse_listing_requirement_index,
)
from historical_mnpi.metadata_resolver import (
    MetadataDataClass,
)


ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "real_corpus"


def interval(
    interval_id="interval:test",
    symbol="ABC",
    exchange="NASDAQ",
    start="2015-01-01",
    end="2015-01-31",
):
    return ListingIntervalEvidence(
        interval_id=interval_id,
        symbol=symbol,
        primary_exchange=exchange,
        valid_from=start,
        valid_through=end,
        start_evidence_url="https://www.sec.gov/start",
        end_evidence_url="https://www.sec.gov/end",
        source_name="SEC issuer releases bracketing listing interval",
        data_class=MetadataDataClass.PUBLIC_OR_AUTHORIZED_HISTORICAL,
    )


class ListingIntervalTests(unittest.TestCase):
    def test_interval_expands_only_covered_requirement_dates(self):
        result = expand_listing_intervals(
            (
                ("ABC", "2014-12-31"),
                ("ABC", "2015-01-02"),
                ("ABC", "2015-01-30"),
                ("ABC", "2015-02-02"),
            ),
            (interval(),),
        )
        self.assertEqual(
            [(x.symbol, x.session_date, x.primary_exchange)
             for x in result.resolved],
            [
                ("ABC", "2015-01-02", "NASDAQ"),
                ("ABC", "2015-01-30", "NASDAQ"),
            ],
        )
        self.assertEqual(
            result.unresolved,
            (
                ("ABC", "2014-12-31"),
                ("ABC", "2015-02-02"),
            ),
        )

    def test_overlapping_conflicting_intervals_fail_closed(self):
        first = interval(
            interval_id="interval:a",
            exchange="NASDAQ",
        )
        second = interval(
            interval_id="interval:b",
            exchange="NYSE",
            start="2015-01-10",
            end="2015-01-20",
        )
        with self.assertRaisesRegex(
            ValueError,
            "conflicting listing intervals",
        ):
            expand_listing_intervals(
                (("ABC", "2015-01-15"),),
                (first, second),
            )

    def test_agreeing_overlaps_choose_most_specific_interval(self):
        broad = interval(
            interval_id="interval:broad",
            start="2015-01-01",
            end="2015-01-31",
        )
        narrow = interval(
            interval_id="interval:narrow",
            start="2015-01-10",
            end="2015-01-20",
        )
        result = expand_listing_intervals(
            (("ABC", "2015-01-15"),),
            (broad, narrow),
        )
        self.assertEqual(len(result.resolved), 1)
        self.assertEqual(
            result.resolved[0].evidence.evidence_id,
            "interval:narrow",
        )

    def test_same_interval_id_cannot_identify_different_evidence(self):
        first = interval(
            interval_id="interval:dup",
            exchange="NASDAQ",
        )
        second = interval(
            interval_id="interval:dup",
            exchange="NYSE",
        )
        with self.assertRaisesRegex(
            ValueError,
            "same listing interval_id",
        ):
            expand_listing_intervals(
                (("ABC", "2015-01-15"),),
                (first, second),
            )

    def test_non_public_or_unauthorized_interval_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "public/authorized historical",
        ):
            ListingIntervalEvidence(
                interval_id="interval:bad",
                symbol="ABC",
                primary_exchange="NASDAQ",
                valid_from="2015-01-01",
                valid_through="2015-01-31",
                start_evidence_url="https://example.com/start",
                end_evidence_url="https://example.com/end",
                source_name="bad",
                data_class=MetadataDataClass.UNAUTHORIZED_PRIVATE_DATA,
            )

    def test_daily_evidence_keeps_both_boundary_urls(self):
        item = interval()
        row = item.as_daily_evidence("2015-01-15")
        self.assertIn(
            "https://www.sec.gov/start",
            row.evidence.source_name,
        )
        self.assertIn(
            "https://www.sec.gov/end",
            row.evidence.source_name,
        )
        self.assertEqual(
            row.evidence.source_kind.value,
            "OFFICIAL_LISTING_HISTORY",
        )


    def test_real_g2_first_six_batches_expand_726_of_3828(self):
        requirements = expand_listing_requirements(
            parse_listing_requirement_index(
                (CORPUS_DIR / "listing_requirement_index.csv").read_text(
                    encoding="utf-8"
                )
            )
        )
        intervals = parse_listing_interval_csv(
            (CORPUS_DIR / "listing_intervals.csv").read_text(
                encoding="utf-8"
            )
        )
        result = expand_listing_intervals(
            requirements,
            intervals,
        )

        self.assertEqual(len(requirements), 3828)
        self.assertEqual(len(intervals), 18)
        self.assertEqual(len(result.resolved), 726)
        self.assertEqual(len(result.unresolved), 3102)

        by_symbol = {}
        for item in result.resolved:
            by_symbol.setdefault(item.symbol, []).append(item)

        self.assertEqual(
            set(by_symbol),
            {"ADI", "BA", "CA", "CAT", "CGNX", "CNMD", "DE", "DGI", "F", "GILD", "HON", "ILMN", "JNPR", "MDU", "NKE", "PNRA", "SBUX", "VMW"},
        )
        self.assertEqual(
            {symbol: len(rows) for symbol, rows in by_symbol.items()},
            {
                "ADI": 44,
                "BA": 22,
                "CA": 44,
                "CAT": 22,
                "CGNX": 44,
                "CNMD": 22,
                "DE": 22,
                "DGI": 66,
                "F": 22,
                "GILD": 22,
                "HON": 22,
                "ILMN": 44,
                "JNPR": 88,
                "MDU": 44,
                "NKE": 22,
                "PNRA": 88,
                "SBUX": 22,
                "VMW": 66,
            },
        )

    def test_materialized_listing_metadata_matches_interval_expansion(self):
        requirements = expand_listing_requirements(
            parse_listing_requirement_index(
                (CORPUS_DIR / "listing_requirement_index.csv").read_text(
                    encoding="utf-8"
                )
            )
        )
        intervals = parse_listing_interval_csv(
            (CORPUS_DIR / "listing_intervals.csv").read_text(
                encoding="utf-8"
            )
        )
        expected = expand_listing_intervals(
            requirements,
            intervals,
        ).resolved

        with (
            CORPUS_DIR / "import" / "listing_metadata.csv"
        ).open("r", encoding="utf-8", newline="") as handle:
            actual = list(csv.DictReader(handle))

        self.assertEqual(len(actual), 726)
        expected_rows = {
            (
                item.symbol,
                item.session_date,
                item.primary_exchange,
                item.evidence.evidence_id,
                item.evidence.source_name,
            )
            for item in expected
        }
        actual_rows = {
            (
                row["symbol"],
                row["session_date"],
                row["primary_exchange"],
                row["evidence_id"],
                row["source_name"],
            )
            for row in actual
        }
        self.assertEqual(actual_rows, expected_rows)

    def test_real_interval_evidence_uses_only_sec_boundaries(self):
        intervals = parse_listing_interval_csv(
            (CORPUS_DIR / "listing_intervals.csv").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(intervals), 18)
        for item in intervals:
            self.assertTrue(item.start_evidence_url.startswith(
                "https://www.sec.gov/"
            ))
            self.assertTrue(item.end_evidence_url.startswith(
                "https://www.sec.gov/"
            ))


if __name__ == "__main__":
    unittest.main()
