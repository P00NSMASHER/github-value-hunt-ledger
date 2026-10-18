"""Research-only regression for two original US government freight datasets."""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from freight import public_faf6_eia_v1 as benchmark


class OfficialPublicDataEvidenceTests(unittest.TestCase):
    def test_original_faf6_2022_78_truck_records_exact_commodities_and_sums(self):
        rows = benchmark.read_faf6_rows()
        self.assertEqual(len(rows),78)
        by_pair={}
        for r in rows:
            pair=(r["dms_origst"],r["dms_destst"])
            by_pair.setdefault(pair,[]).append(r)
        self.assertEqual({k:len(v) for k,v in by_pair.items()},
                         {("24","42"):39,("42","24"):39})
        self.assertEqual(
            sum((Decimal(r["tons_2022"]) for r in by_pair[("24","42")]),Decimal(0)),
            Decimal("9294.353721"),
        )
        self.assertEqual(
            sum((Decimal(r["value_2022"]) for r in by_pair[("42","24")]),Decimal(0)),
            Decimal("22012.297371"),
        )
        for rows in by_pair.values():
            self.assertEqual(len({r["sctg2"] for r in rows}),39)
            self.assertTrue(all(r["trade_type"]=="1" and r["dms_mode"]=="1" for r in rows))

    def test_eia_real_weekly_prices_are_exact_to_milli_dollar_and_week(self):
        rows=benchmark.read_eia_rows()
        self.assertEqual(len(rows),18)
        latest={r["area"]:r["usd_per_gallon"] for r in rows
                if r["week_ending_monday"]=="2026-10-12"}
        self.assertEqual(latest,{"US":"6.179","PADD1":"5.908","PADD1B":"6.471"})
        self.assertEqual(len({(r["week_ending_monday"],r["area"]) for r in rows}),18)

    def test_public_source_does_not_certify_recoverable_money_or_customer_tariffs(self):
        r=benchmark.public_context_report()
        self.assertTrue(r["original_government_data"])
        self.assertEqual(r["faf6_source_rows_in_snapshot"],78)
        self.assertTrue(r["modeled_commodity_value_is_not_freight_spend"])
        self.assertTrue(r["diesel_retail_price_is_not_customer_surcharge_authority"])
        self.assertFalse(r["real_invoices_or_tariffs_examined"])
        self.assertIsNone(r["verified_overcharge_cents"])
        self.assertEqual(r["validated_customer_recovery_cents"],0)
        self.assertFalse(r["automated_customer_contact_authorized"])
        self.assertEqual(r["commercial_claim_clearance"],"NOT_ESTABLISHED")
        self.assertTrue(r["all_26_historical_findings_still_open"])
        self.assertFalse(r["human_pilot_approvals_met"])

    def _edit_fixture(self,filename,mutation,reader):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); fixtures=root/"fixtures";fixtures.mkdir()
            src=benchmark.ROOT/"fixtures"/filename
            dest=fixtures/filename
            shutil.copy2(src,dest)
            data=dest.read_text()
            dest.write_text(mutation(data))
            with patch.object(benchmark,"ROOT",root):
                with self.assertRaisesRegex(ValueError,"PUBLIC_BENCHMARK_"):
                    reader()

    def test_changed_original_faf6_value_fails_exact_aggregate(self):
        name="public_faf6_2022_md_pa_truck_domestic.csv"
        self._edit_fixture(
            name,
            lambda t:t.replace("24,42,1,1,01,26.297846,47.933851",
                               "24,42,1,1,01,26.297847,47.933851"),
            benchmark.read_faf6_rows,
        )

    def test_forged_domestic_mode_and_duplicate_commodity_fail(self):
        name="public_faf6_2022_md_pa_truck_domestic.csv"
        self._edit_fixture(
            name,
            lambda t:t.replace("24,42,1,1,01,26.297846,47.933851",
                               "24,42,2,1,01,26.297846,47.933851"),
            benchmark.read_faf6_rows,
        )
        self._edit_fixture(
            name,
            lambda t:t.replace("24,42,1,1,02,81.119550,24.135134",
                               "24,42,1,1,01,81.119550,24.135134"),
            benchmark.read_faf6_rows,
        )

    def test_invoice_and_private_evidence_columns_cannot_be_smuggled_in(self):
        name="public_faf6_2022_md_pa_truck_domestic.csv"
        self._edit_fixture(
            name,
            lambda t:t.replace("tons_2022,value_2022\n",
                               "tons_2022,value_2022,invoice_amount\n"),
            benchmark.read_faf6_rows,
        )
        self._edit_fixture(
            name,
            lambda t:t.replace("24,42,1,1,01,26.297846,47.933851",
                               "24,42,1,1,01,26.297846,47.933851,200.00"),
            benchmark.read_faf6_rows,
        )

    def test_fake_diesel_price_or_missing_week_is_rejected(self):
        name="public_eia_diesel_onhighway_2026_09_07_to_10_12.csv"
        self._edit_fixture(
            name,
            lambda t:t.replace("2026-10-12,PADD1,5.908","2026-10-12,PADD1,5.998"),
            benchmark.read_eia_rows,
        )
        self._edit_fixture(
            name,
            lambda t:t.replace("2026-10-12,PADD1,5.908","2026-10-11,PADD1,5.908"),
            benchmark.read_eia_rows,
        )
        self._edit_fixture(
            name,
            lambda t:t.replace("2026-09-07,US,5.967","2026-09-07,US,-5.967"),
            benchmark.read_eia_rows,
        )

    def test_replaced_or_forged_official_zip_never_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fake-government-source.zip"
            p.write_bytes(b"fake")
            with self.assertRaisesRegex(ValueError,"PUBLIC_BENCHMARK_OFFICIAL_ARCHIVE_SIZE_MISMATCH"):
                benchmark.verify_official_faf6_zip(p)
            size=benchmark._load_manifest()["faf6"]["archive_bytes"]
            with p.open("wb") as f:
                f.seek(size-1)
                f.write(b"\x00")
            with self.assertRaisesRegex(ValueError,"PUBLIC_BENCHMARK_OFFICIAL_ARCHIVE_SHA_MISMATCH"):
                benchmark.verify_official_faf6_zip(p)

    def test_source_archive_full_hash_is_pinned_to_official_published_zip(self):
        m=benchmark._load_manifest()
        self.assertEqual(m["faf6"]["source_archive_sha256"],
                         "50c6a8bb857b94998a634306234b805af6a114f7ce76ef0b02f34660d01a3e0d")
        self.assertEqual(m["faf6"]["internal_csv_sha256"],
                         "e6ff7d1a48a3bc0181435230df508da9b5587a5a009f341e925a31d4a6055d55")
        self.assertEqual(m["faf6"]["source_rows"],599529)
        self.assertEqual(m["faf6"]["archive_bytes"],6823123)
        self.assertEqual(m["faf6"]["internal_csv_bytes"],22948261)
        self.assertFalse(any("invoice" in x.lower() for x in benchmark.FAF_FIELDS))


if __name__ == "__main__":
    unittest.main()
