"""Mission 27 adversarial FRED publisher-distributor vs BLS original API tests.

Synthetic HTML table fixtures do not mean the FRED domain was contacted.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight.research_evidence_gate import canon_hash
from freight import research_fred_parent_ppi as m27

TODAY=date(2026,10,12)


def frozen():
    return json.loads(m27.BOOK.read_text(encoding="utf-8"))


def fake_fred_html(*, dataset=None) -> bytes:
    if dataset is None: dataset=frozen()["year_to_monthly_observations"]
    cells="".join(
        "<tr><td>"+str(year)+"-"+str(month).zfill(2)+"-01</td><td>"+
        str(value)+"</td></tr>"
        for year in m27.YEARS for month,value
        in enumerate(dataset[str(year)],1)
    )
    doc=(
        "<!doctype html><html lang='en'><head><title>"+
        "Producer Price Index by Industry: Truck Transportation" +
        "</title></head><body><h1>Table Data</h1>"+
        "<p>Series ID PCU484484</p><p>U.S. Bureau of Labor Statistics</p>"+
        "<p>Not Seasonally Adjusted; Dec 2003=100</p>"+
        "<table><tr><th>DATE</th><th>VALUE</th></tr>"+
        cells+"</table></body></html>"
    )
    return doc.encode("utf-8")


class FredAggregateProvenanceTests(unittest.TestCase):
    def test_original_web_snapshot_git_blob_and_provenance_controls(self):
        self.assertEqual(m27._git_blob(m27.BOOK.read_bytes()),m27.BOOK_SHA1)
        self.assertEqual(m27.validate_catalog(frozen(),as_of=TODAY),[])
        b=frozen()
        self.assertEqual(b["series_id"],"PCU484484")
        self.assertEqual(b["public_issuer"],"U.S. Bureau of Labor Statistics")
        self.assertEqual(b["public_distributor"],"Federal Reserve Bank of St. Louis FRED")
        self.assertFalse(b["original_fred_publisher_bytes_replayed_in_ci"])
        self.assertFalse(b["original_bls_api_month_values_replayed"])

    def test_fred_monthly_grain_is_exactly_96_observations(self):
        b=frozen()
        self.assertEqual(b["report_years"],list(m27.YEARS))
        months=b["year_to_monthly_observations"]
        self.assertEqual(sum(len(months[str(y)]) for y in m27.YEARS),96)
        self.assertEqual([m27._index_num(x) for x in months["2017"]][:2],
                         [m27.Decimal("132.500"),m27.Decimal("132.800")])
        self.assertEqual(months["2024"][-1],"182.528")

    def test_fred_web_source_not_direct_bls_api(self):
        r=m27.report_shell(as_of=TODAY)
        self.assertEqual(r["source_status"],m27.OFFLINE)
        self.assertFalse(r["source_is_direct_bls_api_verified"])
        self.assertFalse(r["fresh_fred_distributor_http_replay_completed"])
        self.assertEqual(r["fresh_monthly_observations_verified_against_fred_http_this_run"],0)
        self.assertEqual(r["source_months_2017_2024_in_web_observed_snapshot"],96)
        self.assertFalse(r["parent_index_adjusted_estimate_can_be_marked_source_authenticated"])
        self.assertTrue(r["m26_bls_original_api_parent_source_rejection_preserved"])

    def test_public_2017_2024_index_and_census_adjustment_arithmetic(self):
        r=m27.report_shell(as_of=TODAY)
        self.assertEqual(r["parent_2017_to_2024_nominal_census_growth_pct"],"38.65")
        self.assertEqual(r["parent_2017_to_2024_fred_displayed_price_index_change_pct"],"37.04")
        self.assertEqual(r["parent_2017_to_2024_provisional_price_adjusted_revenue_proxy_pct"],"1.18")
        p=r["parent_price_proxy_annual_observations"]
        self.assertEqual(len(p),8)
        self.assertEqual(p[0]["public_fred_snapshot_mean_ppi"],"134.3583")
        self.assertEqual(p[-1]["public_fred_snapshot_mean_ppi"],"184.1238")
        self.assertEqual(p[-1]["provisional_2017_ppi_level_revenue_proxy_million_usd"],
                         "293949.981")
        self.assertEqual(p[0]["provisional_2017_ppi_level_revenue_proxy_million_usd"],
                         "290532.000")
        self.assertTrue(all(not x["is_official_real_freight_output"] for x in p))

    def test_m26_child_api_evidence_remains_separately_qualified(self):
        r=m27.report_shell(as_of=TODAY)
        c={x["naics"]:x for x in r["m26_child_ppi_comparison"]}
        self.assertEqual(set(c),{"484121","484122"})
        self.assertEqual(c["484121"]["2017_index_level_adjusted_proxy_growth_pct"],"2.82")
        self.assertEqual(c["484122"]["2017_index_level_adjusted_proxy_growth_pct"],"-1.89")
        self.assertTrue(all(not x["bls_api_replayed_in_this_job"] for x in c.values()))
        self.assertTrue(all(x["source_provenance"].startswith("PREVIOUS_M26_BLS_ORIGINAL")
                            for x in c.values()))

    def test_complete_synthetic_html_parser_validates_snapshot_only(self):
        rows=m27.parse_fred_html(fake_fred_html(),book=frozen())
        self.assertEqual(len(rows),8)
        self.assertEqual(sum(len(x) for x in rows.values()),96)
        self.assertEqual(rows[2024][-1],"182.528")

    def test_fake_html_replay_fulfills_parser_not_actual_bls_origin(self):
        result=m27.verify_fred_html_source(as_of=TODAY,raw=fake_fred_html())
        self.assertEqual(result["source_status"],m27.VERIFIED_FRED)
        self.assertTrue(result["fresh_fred_distributor_http_replay_completed"])
        self.assertEqual(result["fresh_monthly_observations_verified_against_fred_http_this_run"],96)
        self.assertFalse(result["source_is_direct_bls_api_verified"])
        self.assertEqual(result["fresh_fred_http_sha256"],sha256(fake_fred_html()).hexdigest())
        self.assertTrue(result["parent_index_adjusted_estimate_can_be_marked_source_authenticated"])

    def test_one_changed_fred_month_rejected_not_silently_accepted(self):
        b=deepcopy(frozen()["year_to_monthly_observations"])
        b["2018"][5]="999.000"
        with self.assertRaisesRegex(ValueError,"M27_FRED_DISTRIBUTOR_MONTHLY_VALUE_CHANGED"):
            m27.parse_fred_html(fake_fred_html(dataset=b),book=frozen())

    def test_absent_fred_month_rejected(self):
        b=deepcopy(frozen()["year_to_monthly_observations"])
        b["2024"].pop(3)
        with self.assertRaisesRegex(ValueError,"M27_FRED_ORIGINAL_96_MONTHLY_VALUES_INCOMPLETE|M27_FRED_DISTRIBUTOR_MONTHLY_VALUE_CHANGED"):
            m27.parse_fred_html(fake_fred_html(dataset=b),book=frozen())

    def test_duplicate_source_date_rejected(self):
        doc=fake_fred_html().decode("utf-8")
        row="<tr><td>2017-01-01</td><td>132.500</td></tr>"
        doc=doc.replace("</table>",row+"</table>")
        with self.assertRaisesRegex(ValueError,"M27_FRED_DUPLICATE_MONTH_OBSERVATION"):
            m27.parse_fred_html(doc.encode(),book=frozen())

    def test_metadata_wrong_unit_rejected(self):
        for old,new in (
            ("Dec 2003=100","Jan 2017=100"),
            ("Not Seasonally Adjusted","Seasonally Adjusted"),
            ("U.S. Bureau of Labor Statistics","Private employer claims"),
            ("Producer Price Index by Industry: Truck Transportation","Invoice errors"),
        ):
            doc=fake_fred_html().decode("utf-8").replace(old,new)
            with self.assertRaisesRegex(ValueError,"M27_FRED_BLS_SERIES_METADATA_MISSING",msg=old):
                m27.parse_fred_html(doc.encode(),book=frozen())

    def test_altered_series_id_or_html_origin_rejected(self):
        doc=fake_fred_html().replace(b"PCU484484",b"PCU484121484121")
        with self.assertRaisesRegex(ValueError,"M27_NOT_THE_FRED_DISTRIBUTOR_484_TABLE"):
            m27.parse_fred_html(doc,book=frozen())
        with self.assertRaisesRegex(ValueError,"M27_NOT_THE_FRED_DISTRIBUTOR_484_TABLE"):
            m27.parse_fred_html(b"2000-01-01,100.000",book=frozen())

    def test_fred_pub_value_non_numeric_or_integer_cannot_be_accepted(self):
        for value in ("0","-1","S","NaN","32.1","150.1234567","",None,1):
            with self.assertRaisesRegex(ValueError,"M27_FRED_PPI_MONTHLY_NUMERIC_VALUE_INVALID"):
                m27._index_num(value)

    def test_source_month_catalog_tamper_is_detected_even_if_numeric(self):
        b=frozen()
        b["year_to_monthly_observations"]["2021"][5]="999.000"
        self.assertIn("M27_PINNED_FRED_WEB_INDEXED_PUBLICATION_SNAPSHOT_CHANGED",
                      ";".join(m27.validate_catalog(b,as_of=TODAY)))

    def test_catalog_evidence_promotion_and_external_source_forgery_rejected(self):
        for key,value in (
            ("original_bls_api_month_values_replayed",True),
            ("original_fred_publisher_bytes_replayed_in_ci",True),
            ("original_fred_binary_checksum","0"*64),
            ("direct_bls_authenticated_parent_index_available",True),
            ("price_adjustment_is_illustrative_from_public_table_only",False),
            ("source_observations_should_be_marked_fresh_verified_without_direct_fetch",True),
            ("pilot_18_independent_human_controls_unmet",False),
            ("real_refund_volume_usd",12345),
            ("known_fred_table_url","https://adversary.example/pci"),
        ):
            b=frozen()
            b[key]=value
            self.assertTrue(m27.validate_catalog(b,as_of=TODAY),key)

    def test_fred_endpoint_timeout_cannot_be_misreported_as_no_observations(self):
        report=m27.blocked(as_of=TODAY)
        self.assertEqual(report["source_status"],m27.BLOCKED)
        self.assertEqual(report["fresh_monthly_observations_verified_against_fred_http_this_run"],0)
        self.assertFalse(report["fresh_fred_distributor_http_replay_completed"])
        self.assertEqual(report["source_months_2017_2024_in_web_observed_snapshot"],96)
        self.assertIsNone(report["fresh_fred_http_sha256"])
        self.assertFalse(report["parent_index_adjusted_estimate_can_be_marked_source_authenticated"])

    def test_network_timeout_creates_explicit_blocked_report(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv",["m27","--out",directory,"--as-of-date","2026-10-12","--fetch-fred"]):
                with patch.object(m27,"_fetch_fred_page",side_effect=TimeoutError("synthetic publisher down")):
                    m27.main()
            report=json.loads((Path(directory)/"fred_parent_ppi_provenance.json").read_text())
            self.assertEqual(report["source_status"],m27.BLOCKED)
            self.assertFalse(report["source_is_direct_bls_api_verified"])
            self.assertIsNone(report["actual_refunds_or_cash_recoveries_usd"])

    def test_fred_html_changed_values_fail_not_blocked(self):
        b=deepcopy(frozen()["year_to_monthly_observations"])
        b["2024"][-1]="999.000"
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv",["m27","--out",directory,"--as-of-date","2026-10-12","--fetch-fred"]):
                with patch.object(m27,"_fetch_fred_page",return_value=fake_fred_html(dataset=b)):
                    with self.assertRaisesRegex(ValueError,"M27_FRED_DISTRIBUTOR_MONTHLY_VALUE_CHANGED"):
                        m27.main()

    def test_all_real_customer_monetization_controls_still_zero_unmet(self):
        report=m27.report_shell(as_of=TODAY)
        self.assertEqual(report["lab"],14)
        self.assertFalse(report["new_lab_created"])
        self.assertEqual(report["client_paid_ltl_invoice_rows_observed"],0)
        self.assertEqual(report["actual_carrier_bill_overcharge_count_verified"],0)
        self.assertIsNone(report["actual_refunds_or_cash_recoveries_usd"])
        self.assertIsNone(report["freight_recoverable_market_tam_usd"])
        self.assertFalse(report["independent_buyer_demand_established"])
        self.assertFalse(report["public_performance_claims_or_external_contacts_authorized"])
        self.assertTrue(report["human_customer_pilot_18_independent_requirements_still_unmet"])
        self.assertFalse(report["scheduled_tasks_created_or_modified"])

    def test_source_time_travel_and_extra_customer_fields_rejected(self):
        self.assertTrue(m27.validate_catalog(frozen(),as_of=date(2026,10,11)))
        b=frozen()
        b["customer_account_id"]="forbidden"
        self.assertTrue(m27.validate_catalog(b,as_of=TODAY))
        with self.assertRaisesRegex(ValueError,"M27_PPI_SOURCE_GUARDS_FAILED"):
            m27.report_shell(as_of=date(2026,10,11))

    def test_html_report_escapes_foreign_metadata_and_labels_unverified(self):
        report=m27.report_shell(as_of=TODAY)
        report["caveat"]="<script>alert('revenues')</script>"
        html=m27.render_html(report)
        self.assertNotIn("<script>",html)
        self.assertIn("&lt;script&gt;",html)
        self.assertIn("provisional FRED webpage",html)
        self.assertIn("not freshly authenticated",html)
        self.assertIn("PCU484484",html)

    def test_evidence_receipt_hashes_are_deterministic(self):
        report=m27.report_shell(as_of=TODAY)
        self.assertEqual(report["receipt_sha256"],canon_hash({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))


if __name__=="__main__":
    unittest.main()
