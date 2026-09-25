import unittest

from historical_mnpi.listing_intervals import (
    ListingIntervalEvidence,
    expand_listing_intervals,
)
from historical_mnpi.metadata_resolver import (
    MetadataDataClass,
)


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


if __name__ == "__main__":
    unittest.main()
