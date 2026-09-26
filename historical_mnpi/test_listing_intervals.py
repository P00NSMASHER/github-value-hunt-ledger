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


    def test_real_g2_current_batches_expand_3608_of_3828(self):
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
        self.assertEqual(len(intervals), 136)
        self.assertEqual(len(result.resolved), 3608)
        self.assertEqual(len(result.unresolved), 220)

        by_symbol = {}
        for item in result.resolved:
            by_symbol.setdefault(item.symbol, []).append(item)

        self.assertEqual(len(by_symbol), 136)
        self.assertEqual(
            {
                symbol: len(by_symbol[symbol])
                for symbol in (
                    "MCRL",
                    "MDP",
                    "MIC",
                    "MKC",
                    "NATI",
                    "NVR",
                    "INWK",
                    "ISSI",
                    "JWN",
                    "NUAN",
                    "OSK",
                    "P",
                    "PAY",
                    "PBI",
                    "PFPT",
                    "MCRI",
                    "POWI",
                    "PRU",
                    "PVH",
                    "QLIK",
                    "R",
                    "PLL",
                    "RES",
                    "RH",
                    "ROG",
                    "ROL",
                    "ROVI",
                    "SCVL",
                    "SGEN",
                    "SKX",
                    "SM",
                    "SNDK",
                    "SNX",
                    "STMP",
                    "STT",
                    "SWKS",
                    "SYMM",
                    "TER",
                    "THC",
                    "TIBX",
                    "TNGO",
                    "TPX",
                    "TRAK",
                    "TW",
                    "TXRH",
                )
            },
            {
                "MCRL": 22,
                "MDP": 22,
                "MIC": 22,
                "MKC": 22,
                "NATI": 44,
                "NVR": 22,
                "INWK": 22,
                "ISSI": 22,
                "JWN": 22,
                "NUAN": 22,
                "OSK": 22,
                "P": 22,
                "PAY": 44,
                "PBI": 22,
                "PFPT": 22,
                "MCRI": 22,
                "POWI": 22,
                "PRU": 22,
                "PVH": 22,
                "QLIK": 22,
                "R": 22,
                "PLL": 22,
                "RES": 22,
                "RH": 22,
                "ROG": 44,
                "ROL": 22,
                "ROVI": 22,
                "SCVL": 22,
                "SGEN": 22,
                "SKX": 22,
                "SM": 22,
                "SNDK": 22,
                "SNX": 22,
                "STMP": 22,
                "STT": 22,
                "SWKS": 22,
                "SYMM": 22,
                "TER": 22,
                "THC": 44,
                "TIBX": 22,
                "TNGO": 22,
                "TPX": 22,
                "TRAK": 22,
                "TW": 22,
                "TXRH": 22,
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

        self.assertEqual(len(actual), 3608)
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
        self.assertEqual(len(intervals), 136)
        for item in intervals:
            self.assertTrue(item.start_evidence_url.startswith(
                "https://www.sec.gov/"
            ))
            self.assertTrue(item.end_evidence_url.startswith(
                "https://www.sec.gov/"
            ))


if __name__ == "__main__":
    unittest.main()
