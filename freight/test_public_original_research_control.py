"""Lab 14 original public source corpus must never self-promote recovery claims."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from freight import public_original_research_control as src


class Lab14PublicSourceCensusTests(unittest.TestCase):
    def test_fixed_source_census_without_any_first_party_customer_recovery(self):
        data=src.snapshot()
        self.assertEqual(data["total_bounded_observations"],307)
        self.assertEqual(len(data["original_public_source_record_counts"]),5)
        self.assertEqual(data["standalone_official_publisher_examples"],1)
        self.assertEqual(data["standalone_external_adjudication_records"],1)
        self.assertEqual(data["census_official_md_origin_pums_record_count"],612317)
        self.assertEqual(data["census_official_md_origin_gvf_cv_percent"],"9.74")
        self.assertTrue(data["fmc_award_actual_cash_received_verified"] is False)
        self.assertEqual(data["real_RETALLY_customer_invoices_seen"],0)
        self.assertEqual(data["actual_RETALLY_cash_recovered_cents"],0)
        self.assertEqual(data["original_historical_findings_still_open"],26)
        self.assertEqual(data["independent_first_customer_human_gates_unmet"],18)
        self.assertEqual(data["commercial_claim_clearance"],"NO_GO")

    def test_locally_recomputable_digest_does_not_claim_external_signature(self):
        r=src.snapshot()
        claimed=r.pop("local_content_sha256")
        self.assertTrue(r.pop("local_hash_not_an_external_original_source_signature"))
        observed=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        self.assertEqual(claimed,observed)

    def test_forged_payment_is_never_counted_as_a_recovery(self):
        original=src.verified_public_order()
        with patch.object(src,"verified_public_order",return_value={
            **original,"actual_payment_verified_cents":965451}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_census_prefix_cannot_be_promoted_to_full_statistical_estimate(self):
        original=src.cfs_prefix()
        with patch.object(src,"cfs_prefix",return_value={
            **original,"national_estimate_authorized":True}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_stb_2024_accounting_period_cannot_relabel_2018_waybills(self):
        original=src.stb_prefix()
        with patch.object(src,"stb_prefix",return_value={
            **original,"waybill_year_histogram":{"2024":100}}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_INVALID_CUSTOMER_CLAIM"):
                src.snapshot()

    def test_source_counts_cannot_silently_add_forged_records(self):
        original=src.public_context_report()
        with patch.object(src,"public_context_report",return_value={
            **original,"faf6_source_rows_in_snapshot":79}):
            with self.assertRaisesRegex(ValueError,"LAB14_PUBLIC_EVIDENCE_SOURCE_COUNTS"):
                src.snapshot()

    def test_report_contains_no_raw_customer_personal_information(self):
        summary=src.snapshot()
        html=src.html_report(summary)
        self.assertIn("research only",html)
        self.assertIn("NOT verified customer invoices",html)
        self.assertNotIn("Work email:",html)
        self.assertNotIn("SHIPMT_ID,",html)
        self.assertNotIn("Customer recovered",html)

    def test_sanitized_json_and_html_are_written_only_with_explicit_output(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            summary=src.snapshot()
            rendered=src.html_report(summary)
            (d/"index.html").write_text(rendered)
            (d/"public_evidence_census.json").write_text(json.dumps(summary))
            saved=json.loads((d/"public_evidence_census.json").read_text())
            self.assertEqual(saved["total_bounded_observations"],307)
            self.assertTrue((d/"index.html").read_text().startswith("<!doctype html>"))


if __name__=="__main__":
    unittest.main()
