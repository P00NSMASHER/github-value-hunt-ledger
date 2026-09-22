import sqlite3
import tempfile
import unittest
from pathlib import Path

import crawler


class TariffLedgerTests(unittest.TestCase):
    def test_canonicalize_strips_tracking(self):
        got = crawler.canonicalize_url(
            "HTTP://WWW.Example.com//tariff.pdf?utm_source=x&rev=2#frag"
        )
        self.assertEqual(got, "http://www.example.com/tariff.pdf?rev=2")

    def test_effective_date_and_version(self):
        text = "Tariff No. FMC-7 Revision 4. Effective April 1, 2026."
        self.assertEqual(crawler.detect_effective_dates(text)[0], "2026-04-01")
        self.assertEqual(crawler.detect_source_version(text, "https://x.test/tariff"), "FMC-7|REV:4")

    def test_compact_maritime_effective_and_expiration_dates(self):
        text = """
        Tariff No. 019075-002 Amendment No. 7
        Effective Date: 5MAY2022
        Expire Date: 11-AUG-2023
        """
        self.assertEqual(
            crawler.detect_effective_dates(text),
            ("2022-05-05", "2023-08-11"),
        )
        self.assertEqual(
            crawler.detect_source_version(text, "https://x.test/title"),
            "019075-002|AMD:7",
        )

    def test_numeric_compact_effective_date(self):
        text = "Tariff No. 12 Effective Date: 20260401"
        self.assertEqual(crawler.detect_effective_dates(text)[0], "2026-04-01")

    def test_applicability_and_pass_through_rule_families(self):
        text = """
        Rates, charges, and rules applicable are those in effect on the date
        cargo is received by the carrier. The listed ocean carrier surcharge
        is passed through at cost without markup.
        """
        rules = set(crawler.classify_rules(text))
        self.assertIn("applicability_date", rules)
        self.assertIn("pass_through", rules)

    def test_extract_money_and_free_time(self):
        text = """
        Tariff No. 12
        Effective 04/01/2026

        DEMURRAGE AND FREE TIME
        Free time is 4 calendar days. After expiration of free time,
        demurrage is USD 125 per day for days 5 through 10.
        """
        terms = crawler.extract_terms(text, "https://carrier.test/tariff-12.pdf")
        self.assertTrue(any(
            t.rule_type == "demurrage"
            and t.term_kind == "money"
            and t.amount_value == "125"
            for t in terms
        ))
        self.assertTrue(any(
            t.rule_type == "free_time"
            and t.term_kind == "quantity"
            and t.quantity_value == "4"
            for t in terms
        ))
        self.assertTrue(all(
            t.effective_from == "2026-04-01"
            for t in terms
            if t.rule_type in {"demurrage", "free_time"}
        ))

    def test_schema_initializes(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "ledger.sqlite"
            conn = crawler.init_db(db)
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            self.assertTrue(
                {"entities", "tariff_locations", "snapshots", "terms", "crawl_errors"}
                <= tables
            )
            conn.close()

    def test_shard_assignment_is_complete_and_disjoint(self):
        rows = [
            crawler.EntitySource(
                entity_class="vocc",
                organization_no=str(i),
                legal_name=f"Carrier {i}",
                trade_name="",
                active=True,
                tariff_url=f"https://example{i}.com/tariff",
                directory_url="https://fmc.example/report",
                directory_sha256="x" * 64,
            )
            for i in range(100)
        ]
        shards = [crawler.shard_sources(rows, i, 7) for i in range(7)]
        flattened = [r.tariff_url for shard in shards for r in shard]
        self.assertEqual(len(flattened), 100)
        self.assertEqual(len(set(flattened)), 100)


if __name__ == "__main__":
    unittest.main()
