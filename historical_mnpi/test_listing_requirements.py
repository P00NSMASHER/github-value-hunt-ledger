import unittest
from pathlib import Path

from historical_mnpi.listing_requirements import (
    EXPECTED_EXPANDED_PAIR_SHA256,
    SOURCE_REQUIREMENTS_SHA256,
    expand_listing_requirements,
    expanded_pair_sha256,
    listing_requirement_index_hash,
    parse_listing_requirement_index,
)


ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "real_corpus" / "listing_requirement_index.csv"


class ListingRequirementIndexTests(unittest.TestCase):
    def test_real_compact_index_expands_to_exact_gate_size(self):
        rows = parse_listing_requirement_index(
            INDEX_PATH.read_text(encoding="utf-8")
        )
        expanded = expand_listing_requirements(rows)

        self.assertEqual(len(rows), 146)
        self.assertEqual(len(expanded), 3828)
        self.assertEqual(len(set(expanded)), 3828)
        self.assertEqual(
            sum(row.requirement_count for row in rows),
            3828,
        )
        self.assertEqual(len(listing_requirement_index_hash(rows)), 64)
        self.assertEqual(
            expanded_pair_sha256(rows),
            EXPECTED_EXPANDED_PAIR_SHA256,
        )
        self.assertEqual(
            SOURCE_REQUIREMENTS_SHA256,
            "58e05613603b95b806eedb49ede774fce763f5ca7519487bed66282e4fe0a3fb",
        )

    def test_first_listing_batch_symbols_have_22_requirements_each(self):
        rows = parse_listing_requirement_index(
            INDEX_PATH.read_text(encoding="utf-8")
        )
        by_symbol = {
            row.historical_symbol: row
            for row in rows
        }

        self.assertEqual(by_symbol["CNMD"].requirement_count, 22)
        self.assertEqual(by_symbol["CAT"].requirement_count, 22)
        self.assertEqual(by_symbol["GILD"].requirement_count, 22)

        self.assertEqual(by_symbol["CNMD"].first_date, "2011-03-28")
        self.assertEqual(by_symbol["CNMD"].last_date, "2011-04-27")
        self.assertEqual(by_symbol["CAT"].first_date, "2011-12-22")
        self.assertEqual(by_symbol["CAT"].last_date, "2012-01-25")
        self.assertEqual(by_symbol["GILD"].first_date, "2015-01-02")
        self.assertEqual(by_symbol["GILD"].last_date, "2015-02-03")

    def test_empty_index_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_listing_requirement_index(
                "historical_symbol,requirement_count,first_date,last_date,required_dates\n"
            )

    def test_count_mismatch_fails_closed(self):
        text = (
            "historical_symbol,requirement_count,first_date,last_date,required_dates\n"
            "ABC,2,2015-01-02,2015-01-02,2015-01-02\n"
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            parse_listing_requirement_index(text)


if __name__ == "__main__":
    unittest.main()
