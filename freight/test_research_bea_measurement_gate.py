"""Mission 30 adversarial BEA gross-output / GDP value-added compatibility tests.

Synthetic BEA HTML fixtures test the original-data parser but do not prove
network provenance; the separate exact-domain CI job authenticates pages.
No unpublished BEA real gross-output quantity values are invented.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight import research_bea_measurement_gate as m30

TODAY=date(2026,10,12)


def book():
    return json.loads(m30.BOOK.read_text(encoding="utf-8"))


def pages():
    definitions=(
        '<!doctype html><html><body><h1>BEA measurement definitions</h1>'
        '<h3>Value added by industry</h3><p>Gross output minus intermediate inputs.</p>'
        '<h3>Gross Output by Industry</h3><p>Industry sales and receipts.</p>'
        '<h3>Chain-Type Quantity Indexes for Gross Output</h3>'
        '<p>Measures real quantities of output.</p></body></html>'
    ).encode("utf-8")
    gross=(
        '<html><body><h1>Gross Output by Industry</h1>'
        '<p>Industry sales and gross output released by BEA.</p></body></html>'
    ).encode("utf-8")
    return definitions,gross


class BEAMeasurementCompatibilityTests(unittest.TestCase):
    def test_source_catalog_pinned_git_blob_and_trust_holds(self):
        self.assertEqual(m30._blob(m30.BOOK.read_bytes()),m30.BOOK_SHA1)
        self.assertEqual(m30.validate_book(book(),as_of=TODAY),[])
        self.assertEqual(book()["scope"],m30.BOOK_SCOPE)
        self.assertFalse(book()["original_gross_output_484_source_verified"])

    def test_real_value_added_and_gross_output_distinct_by_official_definition(self):
        b=book()
        self.assertEqual(b["definitions"]["gdp_value_added"],"GROSS_OUTPUT_MINUS_INTERMEDIATE_INPUTS")
        self.assertEqual(b["definitions"]["real_gross_output"],"CHAIN_QUANTITY_INDEX_FOR_GROSS_OUTPUT_INDUSTRY")
        for benchmark in ("BEA_REAL_GDP_VALUE_ADDED_BY_INDUSTRY",
                          "FRED_DISTRIBUTED_BEA_REAL_GDP_VALUE_ADDED",
                          "BEA_CHAIN_QUANTITY_REAL_GROSS_OUTPUT_484"):
            self.assertFalse(m30.measure_compatible(
                claimed="ILLUSTRATIVE_CENSUS_EMPLOYER_REVENUE_BLS_PPI_PROXY",
                benchmark=benchmark
            ))
        with self.assertRaisesRegex(ValueError,"M30_UNSUPPORTED_BEA_BENCHMARK_CATEGORY"):
            m30.measure_compatible(claimed="ILLUSTRATIVE_CENSUS_EMPLOYER_REVENUE_BLS_PPI_PROXY",
                                   benchmark="FREIGHT_INVOICE_REFUND")

    def test_2025_vintage_real_gdp_growth_is_historical_not_current(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_value_added_2025_vintage_2024_index_2017eq100"],"101.406")
        self.assertEqual(r["bea_value_added_2025_vintage_2017_to_2024_growth_pct"],"1.41")
        self.assertTrue(r["bea_real_gdp_2025_vintage_is_not_latest"])

    def test_2026_vintage_real_gdp_value_added_revision_changes_sign(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_value_added_2026_vintage_2024_index_2017eq100"],"97.585")
        self.assertEqual(r["bea_value_added_2026_vintage_2017_to_2024_growth_pct"],"-2.42")
        self.assertEqual(r["bea_real_value_added_2024_index_revision_points"],"-3.821")
        self.assertLess(int(book()["bea_real_value_added_2026_vintage"]["year_values"]["2024"]),
                        int(book()["bea_real_value_added_2026_vintage"]["year_values"]["2017"]))

    def test_provisional_ppi_revenue_proxy_is_not_bea_model_error(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertEqual(r["census_bls_484_price_adjusted_revenue_proxy_2017_2024_pct"],"1.18")
        self.assertEqual(r["proxy_minus_bea_real_value_added_growth_points_noncomparable"],"3.60")
        self.assertFalse(r["proxy_vs_bea_value_added_difference_is_model_error"])
        self.assertFalse(r["bea_real_gdp_value_added_cannot_certify_gross_revenue_deflator"] is False)
        self.assertEqual(r["economic_measurement_compatibility_verdict"],
                         "HOLD_BEA_REAL_GROSS_OUTPUT_NOT_AUTHENTICATED_NO_QUANTITATIVE_MODEL_VALIDATION")

    def test_bea_real_gross_output_values_remain_unavailable(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertEqual(r["bea_gross_output_original_source_status"],
                         "HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED")
        self.assertFalse(r["bea_484_real_gross_output_2017_2024_available_for_validation"])
        self.assertFalse(r["bea_484_real_gross_output_original_values_authenticated_this_run"])
        self.assertIsNone(book()["bea_real_gross_output_484_2017_2024_values"])

    def test_web_observed_distributor_data_not_fake_bea_original_replay(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertFalse(r["fred_bea_numeric_source_replayed_in_this_ci"])
        self.assertEqual(r["bea_gdp_value_added_secondary_source_provenance"],
                         "FRED_ALFRED_WEB_OBSERVED_NOT_DIRECT_BEA_ORIGINAL_DATA_REPLAY")
        self.assertFalse(book()["original_bea_value_added_data_bytes_replayed_in_ci"])
        self.assertEqual(book()["source_replay_ci_result"]["fred_bea_real_gdp_chained_dollars"],
                         "BLOCKED_TIMEOUT")

    def test_offline_state_never_marks_source_definitions_fetched_this_run(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertEqual(r["status"],m30.OFFLINE)
        self.assertFalse(r["bea_original_measure_definitions_verified_in_this_run"])
        self.assertIsNone(r["bea_first_party_definitions_sha256_this_run"])
        self.assertIsNone(r["bea_first_party_gross_output_home_sha256_this_run"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_synthetic_html_definitions_validate_but_do_not_contain_real_output_values(self):
        raw,gr=pages()
        result=m30.verify_bea_methods(as_of=TODAY,definition_html=raw,gross_html=gr)
        self.assertEqual(result["status"],m30.VERIFIED)
        self.assertTrue(result["bea_original_measure_definitions_verified_in_this_run"])
        self.assertFalse(result["bea_484_real_gross_output_original_values_authenticated_this_run"])
        self.assertEqual(len(result["bea_first_party_definitions_sha256_this_run"]),64)
        self.assertEqual(len(result["bea_first_party_gross_output_home_sha256_this_run"]),64)

    def test_missing_official_measurement_terms_fails_semantic_check(self):
        for term in ("Gross Output by Industry","Value added by industry",
                     "Chain-Type Quantity Indexes for Gross Output","intermediate inputs"):
            raw,gr=pages()
            mutated=raw.decode().replace(term,"UNRELATED_INVOICE_CLAIMS")
            with self.assertRaisesRegex(ValueError,"M30_BEA_ORIGINAL_DEFINITIONS_MISSING",
                                        msg=term):
                m30.verify_bea_methods(as_of=TODAY,definition_html=mutated.encode(),
                                       gross_html=gr)

    def test_wrong_bea_gross_output_page_fails(self):
        raw,_=pages()
        with self.assertRaisesRegex(ValueError,"M30_BEA_FIRST_PARTY_GROSS_OUTPUT_PAGE_NOT_IDENTIFIED"):
            m30.verify_bea_methods(as_of=TODAY,definition_html=raw,
                                   gross_html=b"<html>unrelated consumer debt</html>")

    def test_nonbytes_and_oversize_fake_original_files_rejected(self):
        raw,gr=pages()
        for invalid in (None,"fake",b"",b"x"*(m30.MAX_HTML+1)):
            with self.assertRaisesRegex(ValueError,"M30_INVALID_FIRST_PARTY_BEA_ORIGINAL_DOCUMENT_BYTES"):
                m30.verify_bea_methods(as_of=TODAY,definition_html=invalid,gross_html=gr)
            with self.assertRaisesRegex(ValueError,"M30_INVALID_FIRST_PARTY_BEA_ORIGINAL_DOCUMENT_BYTES"):
                m30.verify_bea_methods(as_of=TODAY,definition_html=raw,gross_html=invalid)

    def test_bea_fetch_only_two_allowlisted_first_party_urls(self):
        with self.assertRaisesRegex(ValueError,"M30_UNAUTHORIZED_BEA_SOURCE_URL"):
            m30._fetch_document("https://attacker.example/alternate.csv")

    def test_no_customer_market_or_real_invoice_metrics_created(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertEqual(r["lab"],14)
        self.assertFalse(r["new_lab_created"])
        self.assertEqual(r["real_invoice_rows_validated"],0)
        self.assertEqual(r["actual_adjudicated_customer_billing_errors"],0)
        self.assertIsNone(r["recoverable_freight_market_tam_usd"])
        self.assertIsNone(r["cash_collected_from_recoveries_usd"])
        self.assertEqual(r["real_buyers_proven"],0)
        self.assertFalse(r["external_marketing_or_carrier_contact_authorized"])
        self.assertTrue(r["all_18_real_customer_pilot_requirements_unmet"])
        self.assertFalse(r["scheduled_tasks_modified"])

    def test_source_policy_false_real_gross_output_promotion_rejected(self):
        for field in (
            "original_gross_output_484_source_verified",
            "original_bea_value_added_data_bytes_replayed_in_ci",
            "ppi_deflated_census_revenue_is_official_real_gross_output",
            "bea_value_added_measure_sufficient_to_certify_ppi_revenue_proxy",
            "gdp_and_gross_output_are_same_denominator",
            "ppi_proxy_minus_value_added_delta_as_statistical_validation_allowed",
            "reauthorize_external_business_claims",
            "all_18_customer_pilot_approvals_satisfied",
            "new_lab_created",
            "scheduled_tasks_modified",
        ):
            b=book()
            b[field]=True
            self.assertTrue(m30.validate_book(b,as_of=TODAY),field)

    def test_source_catalog_rejects_unapproved_bea_real_output_number(self):
        b=book()
        b["bea_real_gross_output_484_2017_2024_values"]={"2024":110}
        self.assertTrue(m30.validate_book(b,as_of=TODAY))

    def test_source_catalog_rejects_wrong_bea_revisions_or_date(self):
        for path,val in (
            (("bea_real_value_added_2025_vintage","year_values","2024"),"97.585"),
            (("bea_real_value_added_2026_vintage","year_values","2024"),180468),
            (("bea_real_value_added_2026_vintage","date_last_updated"),"2025-09-26"),
        ):
            b=book()
            ref=b
            for part in path[:-1]:ref=ref[part]
            ref[path[-1]]=val
            self.assertTrue(m30.validate_book(b,as_of=TODAY),str(path))

    def test_source_downgrade_to_2025_as_latest_rejected(self):
        b=book()
        b["current_bea_release_date"]="2025-09-26"
        self.assertTrue(m30.validate_book(b,as_of=TODAY))

    def test_fred_timed_out_not_an_absent_government_dataset(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertTrue(r["bea_source_definitions_first_party_ci_probe_success"])
        self.assertEqual(r["bea_gross_output_original_source_status"],
                         "HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED")
        self.assertFalse(r["bea_484_real_gross_output_2017_2024_available_for_validation"])

    def test_source_date_before_publication_observation_rejected(self):
        self.assertTrue(m30.validate_book(book(),as_of=date(2026,10,11)))
        with self.assertRaisesRegex(ValueError,"M30_FROZEN_BEA_BENCHMARK_SOURCE_INVALID"):
            m30.report_shell(as_of=date(2026,10,11))

    def test_blocked_network_returns_zero_authenticated_document_files(self):
        r=m30.blocked(as_of=TODAY)
        self.assertEqual(r["status"],m30.BLOCKED)
        self.assertFalse(r["bea_original_measure_definitions_verified_in_this_run"])
        self.assertIsNone(r["bea_first_party_definitions_sha256_this_run"])
        self.assertEqual(r["receipt_sha256"],canon_hash({
            k:v for k,v in r.items() if k!="receipt_sha256"
        }))

    def test_cli_timeout_is_blocked_without_gross_output_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["m30","--out",folder,"--as-of-date","2026-10-12",
                                   "--fetch-bea-definitions"]):
                with patch.object(m30,"_fetch_document",side_effect=TimeoutError("source down")):
                    m30.main()
            r=json.loads((Path(folder)/"bea_measure_compatibility.json").read_text())
            self.assertEqual(r["status"],m30.BLOCKED)
            self.assertFalse(r["bea_484_real_gross_output_original_values_authenticated_this_run"])
            self.assertIsNone(r["recoverable_freight_market_tam_usd"])

    def test_available_wrong_bea_page_is_failure_not_network_block(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("sys.argv",["m30","--out",folder,"--as-of-date","2026-10-12",
                                   "--fetch-bea-definitions"]):
                with patch.object(m30,"_fetch_document",return_value=b"<html>consumer</html>"):
                    with self.assertRaisesRegex(ValueError,"M30_BEA_ORIGINAL_DEFINITIONS_MISSING"):
                        m30.main()

    def test_html_escapes_injected_caveats_and_holds_recoverable_market(self):
        report=m30.report_shell(as_of=TODAY)
        report["caveat"]="<script>alert('real output')</script>"
        html=m30.render_html(report)
        self.assertIn("&lt;script&gt;",html)
        self.assertNotIn("<script>",html)
        self.assertIn("HOLD_PRIMARY_BEA_QUANTITY_INDEX_NOT_RETRIEVED",html)
        self.assertIn("value added",html.lower())
        self.assertIn("not gross output",html.lower())

    def test_no_false_2026_revenue_inflation_proxy_sign_certification(self):
        r=m30.report_shell(as_of=TODAY)
        self.assertEqual(r["proxy_minus_bea_real_value_added_growth_points_noncomparable"],"3.60")
        self.assertFalse(r["proxy_vs_bea_value_added_difference_is_model_error"])
        self.assertFalse(m30.measure_compatible(
            claimed="ILLUSTRATIVE_CENSUS_EMPLOYER_REVENUE_BLS_PPI_PROXY",
            benchmark="BEA_REAL_GDP_VALUE_ADDED_BY_INDUSTRY"
        ))


if __name__=="__main__":
    unittest.main()
