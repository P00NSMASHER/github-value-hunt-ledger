"""Adversarial Mission 18 source-quality tests; never uses external network."""
from __future__ import annotations
from copy import deepcopy
from datetime import date
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight.research_ltl_revenue_bridge import (
    BOOK, EXPECTED_BOOK_GIT_BLOB_SHA1, RECORDS, REPORT_SCOPE, YEARS,
    _git_blob_sha1, build_revenue, download_fred_csv, parse_fred_csv,
    render_html, validate_catalog, main,
)

TODAY = date(2026, 10, 11)


def book():
    return json.loads(BOOK.read_text(encoding="utf-8"))


def csv_bytes(naics: str, *, header: str = "observation_date", include_2025: bool = False):
    spec = RECORDS[naics]
    content = header + "," + spec["series"] + "\n"
    content += "\n".join(
        str(y) + "-01-01," + str(spec["values"][i])
        for i, y in enumerate(YEARS)
    )
    if include_2025:
        content += "\n2025-01-01,999999\n"
    else:
        content += "\n"
    return content.encode("utf-8")


class AiesLtlRevenueBridgeTests(unittest.TestCase):
    def test_frozen_source_and_expected_three_series_nine_rows(self):
        self.assertEqual(_git_blob_sha1(BOOK.read_bytes()), EXPECTED_BOOK_GIT_BLOB_SHA1)
        self.assertEqual(validate_catalog(book(), as_of=TODAY), [])
        self.assertEqual(len(book()["fred_aies_series"]), 3)
        self.assertEqual(sum(len(x["observations"]) for x in book()["fred_aies_series"]), 9)

    def test_new_2024_employer_carrier_revenue_not_goods_or_billings(self):
        r = build_revenue(as_of=TODAY)
        self.assertEqual(r["scope"], REPORT_SCOPE)
        self.assertEqual(r["latest_observed_reference_year"], 2024)
        self.assertEqual(r["ltl_2024_revenue_billion_usd"], "65.096")
        self.assertEqual(r["tl_2024_revenue_billion_usd"], "161.329")
        self.assertEqual(r["all_trucking_2024_revenue_billion_usd"], "402.827")
        self.assertEqual(r["ltl_2024_share_of_all_trucking_pct"], "16.16")
        self.assertEqual(r["ltl_2024_growth_vs_2023_pct"], "0.69")
        self.assertEqual(r["ltl_2024_growth_vs_2022_pct"], "-0.90")
        self.assertEqual(r["real_ltl_invoice_cases_observed"], 0)
        self.assertIsNone(r["ltl_freight_audit_recoverable_tam_usd"])
        self.assertIsNone(r["ltl_invoice_volume_or_share_of_customer_spend_usd"])
        self.assertIsNone(r["verified_invoice_error_rate_pct"])
        self.assertIsNone(r["actual_cash_recovered_usd"])
        self.assertFalse(r["buyer_demand_proven"])
        self.assertFalse(r["commercial_uses_or_external_contact_allowed"])
        self.assertFalse(r["customer_or_carrier_data_ingested"])
        self.assertFalse(r["source"]["full_census_origin_api_bytes_replayed"])
        self.assertFalse(r["source"]["fred_public_csv_replay_completed"])
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["lab"], 14)
        self.assertEqual(r["receipt_sha256"], canon_hash({
            k: v for k, v in r.items() if k != "receipt_sha256"
        }))

    def test_2022_values_reconcile_and_sas_not_interchangeable(self):
        r = build_revenue(as_of=TODAY)
        self.assertEqual(r["ltl_2022_aies_thousand_usd"], 65688461)
        self.assertEqual(r["historical_2022_sas_comparator_million_usd"], 68411)
        self.assertFalse(r["legacy_2022_comparator_is_interchangeable"])
        self.assertTrue(r["legacy_series_cannot_be_spliced_into_aies"])
        self.assertFalse(r["cross_cfs_shipped_goods_value_division_allowed"])
        self.assertTrue(r["cfs_2022_mode111_and_aies_484122_populations_are_not_equivalent"])

    def test_three_fred_codes_not_three_independent_studies(self):
        r = build_revenue(as_of=TODAY)
        self.assertIn("SINGLE_UNDERLYING_PUBLISHER", r["source"]["source_family"])
        self.assertEqual(r["source"]["publisher"], "U.S. Census Bureau")
        self.assertEqual(r["source"]["distributor"], "Federal Reserve Bank of St. Louis (FRED)")
        self.assertEqual(len(r["revenue_by_year"]), 3)
        for year in r["revenue_by_year"]:
            self.assertLess(year["ltl_484122_thousand_usd"], year["all_trucking_484_thousand_usd"])
            self.assertLess(year["tl_484121_thousand_usd"], year["all_trucking_484_thousand_usd"])

    def test_aies_revenue_cannot_be_replaced_by_cfs_goods_value(self):
        for field, value in [
            ("cfs_origin_naics_population", "SAME_AS_AIES_REVENUE"),
            ("metric", "PAID_LTL_INVOICES"),
            ("naics_classification", "2022_CFS_4931"),
            ("units", "MILLIONS_OF_USD"),
            ("geographic_scope", "Pennsylvania"),
            ("source_family", "THREE_INDEPENDENT_STUDIES"),
            ("observation_method", "OFFICIAL_API_SIGNED"),
        ]:
            b = book()
            b[field] = value
            self.assertTrue(validate_catalog(b, as_of=TODAY), field)

    def test_forged_separate_survey_or_direct_source_proof_rejected(self):
        for field in (
            "direct_official_census_api_or_original_ftp_bytes_replayed_in_repo",
            "three_fred_series_independent_market_surveys",
            "ltl_recovery_tam_established",
            "aies_revenue_equals_auditable_customer_invoice_volume",
            "naics_484122_includes_all_ltl_transport",
            "commercial_or_outreach_authority",
            "data_source_terms_or_publisher_digital_signature_audited",
        ):
            b = book()
            b["evidence_guards"][field] = True
            self.assertIn("FALSE_COMMERCIAL_OR_SOURCE_PROMOTION",
                          "; ".join(validate_catalog(b, as_of=TODAY)), field)

    def test_actual_invoice_counts_and_leaks_fail_closed(self):
        b = book()
        b["evidence_guards"]["actual_customer_invoice_cases_examined"] = 10
        self.assertIn("UNSUPPORTED_REAL_INVOICE_COUNT",
                      "; ".join(validate_catalog(b, as_of=TODAY)))
        b = book()
        b["customer_private_invoice_account_id"] = "private"
        self.assertTrue(validate_catalog(b, as_of=TODAY))

    def test_forged_2024_ltl_value_or_wrong_year_rejected(self):
        for naics in ("484", "484121", "484122"):
            b = book()
            series = next(x for x in b["fred_aies_series"] if x["naics"] == naics)
            series["observations"][-1]["revenue_thousand_usd"] += 1
            self.assertIn("AIES_SOURCE_VALUE_CHANGED_OR_WRONG_UNITS",
                          "; ".join(validate_catalog(b, as_of=TODAY)), naics)
        b = book()
        b["fred_aies_series"][-1]["observations"][0]["year"] = 2024
        self.assertTrue(validate_catalog(b, as_of=TODAY))

    def test_mismatched_series_identity_label_order_or_duplicates_rejected(self):
        for key, value in (
            ("series_id", "AIES484121RCT00US"),
            ("source_url", "https://evil.example/pretend"),
            ("industry_name", "LTL invoices with errors"),
            ("naics", "4931"),
        ):
            b = book()
            b["fred_aies_series"][-1][key] = value
            self.assertTrue(validate_catalog(b, as_of=TODAY), key)
        b = book()
        b["fred_aies_series"].append(deepcopy(b["fred_aies_series"][0]))
        self.assertTrue(validate_catalog(b, as_of=TODAY))

    def test_legacy_sas_2022_splicing_rejected(self):
        for key, value in [
            ("interchangeable_with_aies", True),
            ("unit", "THOUSANDS_OF_NOMINAL_US_DOLLARS"),
            ("revenue_million_usd", 65688461),
            ("series_id", "AIES484122RCT00US"),
        ]:
            b = book()
            b["legacy_2022_sas_comparator"][key] = value
            self.assertTrue(validate_catalog(b, as_of=TODAY), key)

    def test_future_or_backdated_snapshot_rejected(self):
        for key, changed in [
            ("observed_on", "2026-10-10"),
            ("observed_on", "2028-01-01"),
            ("fred_series_last_updated_on", "2026-10-12"),
            ("census_2024_release_date", "2025-09-03"),
        ]:
            b = book()
            b[key] = changed
            self.assertTrue(validate_catalog(b, as_of=TODAY), key)
        self.assertTrue(validate_catalog(book(), as_of=date(2026, 10, 10)))

    def test_both_common_fred_csv_header_forms_are_supported(self):
        b = book()
        for naics in RECORDS:
            for hdr in ("observation_date", "DATE"):
                r = parse_fred_csv(RECORDS[naics]["series"], csv_bytes(naics, header=hdr), b)
                self.assertEqual(r["verified_observation_years"], list(YEARS))
                self.assertFalse(r["downloaded_from_census_origin_api"])
                self.assertFalse(r["original_census_publisher_signature_proven"])
                self.assertEqual(len(r["csv_sha256"]), 64)

    def test_fred_source_mismatch_suppression_missing_year_or_extra_column_rejected(self):
        b = book()
        series = RECORDS["484122"]["series"]
        good = csv_bytes("484122")
        cases = [
            good.replace(b"65096292", b"65096293"),
            good.replace(b"2023-01-01,64651167\n", b""),
            good.replace(b"64651167", b"."),
            good.replace(series.encode(), b"OTHER_SERIES"),
            good.replace(b"observation_date", b"TRANSPORT_SPENDING"),
            good + b"2024-01-01,65096292\n",
            good.replace(b"2022-01-01", b"2022-04-01"),
            good.replace(b"\n", b",unexpected\n", 1),
        ]
        for i, data in enumerate(cases):
            with self.assertRaises(ValueError, msg=str(i)):
                parse_fred_csv(series, data, b)

    def test_newer_2025_year_does_not_silently_change_latest_observed_year(self):
        b = book()
        with self.assertRaisesRegex(ValueError, "NEWER_FRED_YEAR"):
            parse_fred_csv(RECORDS["484122"]["series"],
                           csv_bytes("484122", include_2025=True), b)

    def test_optional_all_three_csv_replay_still_not_census_origin_or_recovery(self):
        csvs = {x["series"]: csv_bytes(naics) for naics, x in RECORDS.items()}
        r = build_revenue(as_of=TODAY, downloaded_csv=csvs)
        self.assertTrue(r["source"]["fred_public_csv_replay_completed"])
        self.assertEqual(len(r["source"]["fred_csv_replay_receipts"]), 3)
        self.assertFalse(r["source"]["full_census_origin_api_bytes_replayed"])
        self.assertIsNone(r["ltl_freight_audit_recoverable_tam_usd"])
        with self.assertRaisesRegex(ValueError, "ALL_THREE_SERIES"):
            build_revenue(as_of=TODAY, downloaded_csv={
                RECORDS["484122"]["series"]: csv_bytes("484122")
            })

    def test_requested_fred_timeout_produces_explicit_blocked_receipt_not_false_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv", ["module", "--as-of-date", "2026-10-11",
                                    "--out", folder, "--verify-fred-csv"]):
                with patch("freight.research_ltl_revenue_bridge.download_fred_csv",
                           side_effect=TimeoutError("simulated no FRED endpoint")):
                    main()
            r=json.loads((Path(folder)/"aies_ltl_revenue.json").read_text())
            self.assertEqual(r["source"]["fresh_fred_source_status"],
                             "BLOCKED_EXTERNAL_FRED_CSV_UNREACHABLE_NOT_VERIFIED")
            self.assertFalse(r["source"]["fred_public_csv_replay_completed"])
            self.assertEqual(r["source"]["fred_csv_replay_receipts"], [])
            self.assertIsNone(r["ltl_freight_audit_recoverable_tam_usd"])
            self.assertEqual(r["receipt_sha256"], canon_hash({
                k:v for k,v in r.items() if k!="receipt_sha256"
            }))

    def test_requested_fred_value_mismatch_still_fails_not_downgraded_to_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            def bad_series(sid):
                naics=next(k for k,x in RECORDS.items() if x["series"]==sid)
                raw=csv_bytes(naics)
                return raw.replace(b"65096292", b"65096293")
            with patch("sys.argv", ["module", "--as-of-date", "2026-10-11",
                                    "--out", folder, "--verify-fred-csv"]):
                with patch("freight.research_ltl_revenue_bridge.download_fred_csv",
                           side_effect=bad_series):
                    with self.assertRaisesRegex(ValueError,"FRED_CSV_SOURCE_OBSERVATION_MISMATCH"):
                        main()

    def test_unauthorized_csv_download_series_rejected_before_network(self):
        with self.assertRaisesRegex(ValueError, "FRED_ONLY_THREE_ALLOWLISTED"):
            download_fred_csv("PRIVATE-INVOICE-DATA")

    def test_html_escapes_untrusted_caveat_and_does_not_infer_recovery(self):
        r = build_revenue(as_of=TODAY)
        r["source_category_warning"] = "<img src=x onerror=evil()>"
        html = render_html(r)
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img", html)
        self.assertIn("not audit recoveries", html.lower())
        self.assertIn("65.096", html)
        self.assertIn("2024", html)


if __name__ == "__main__":
    unittest.main()
