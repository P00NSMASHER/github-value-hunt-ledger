import csv
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "real_corpus" / "listing_requirement_index.csv"


class ListingRequirementIndexTests(unittest.TestCase):
    def test_compact_index_is_complete_and_deterministic(self):
        with INDEX.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 146)
        self.assertEqual(
            sum(int(row["requirement_count"]) for row in rows),
            3828,
        )
        self.assertEqual(
            [row["historical_symbol"] for row in rows],
            sorted(row["historical_symbol"] for row in rows),
        )
        self.assertEqual(
            hashlib.sha256(INDEX.read_bytes()).hexdigest(),
            "b79d87d3ae51022c66f3038e73446188ca956a2187f32803707038d1cbb290b9",
        )

        for row in rows:
            dates = row["required_dates"].split("|")
            self.assertEqual(len(dates), int(row["requirement_count"]))
            self.assertEqual(len(dates), len(set(dates)))
            self.assertEqual(dates, sorted(dates))
            self.assertEqual(dates[0], row["first_date"])
            self.assertEqual(dates[-1], row["last_date"])

    def test_first_listing_batch_has_expected_requirement_counts(self):
        with INDEX.open("r", encoding="utf-8", newline="") as handle:
            rows = {
                row["historical_symbol"]: row
                for row in csv.DictReader(handle)
            }

        expected = {
            "CNMD": ("2011-03-28", "2011-04-27", 22),
            "CAT": ("2011-12-22", "2012-01-25", 22),
            "GILD": ("2015-01-02", "2015-02-03", 22),
        }
        for symbol, (first, last, count) in expected.items():
            row = rows[symbol]
            self.assertEqual(row["first_date"], first)
            self.assertEqual(row["last_date"], last)
            self.assertEqual(int(row["requirement_count"]), count)


if __name__ == "__main__":
    unittest.main()
