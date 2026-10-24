"""Protect FreightRecovery from a superseded GAO case and cross-tariff leakage."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from freight.gao_adjudication_chronology import (
    B165_1969, B215_1984, DEC_1984, DEC_1986,
    LATEST_HISTORICAL, PRIMARY_1984, PRIMARY_1986, PRIMARY_1969,
    REFERENCES, _fixture, make_receipt, ruling_as_of,
    run, validate_historical_inputs, validate_receipt,
)
from freight.unified_research_lab import (
    SEEDS, ResearchError, safe_url, digest,
)


class HistoricalSupersessionTests(unittest.TestCase):
    def test_asof_1984_is_not_final_and_1986_is_controlling_historical_reconsideration(self):
        self.assertEqual(ruling_as_of("B-215958", date(1984, 12, 4)),
                         "NO_GAO_DECISION_AS_OF_DATE")
        self.assertEqual(ruling_as_of("B-215958", DEC_1984),
                         "GAO_1984_INITIAL_CARRIER_FAVORABLE_ONLY")
        self.assertEqual(ruling_as_of("B-215958", date(1986, 2, 17)),
                         "GAO_1984_INITIAL_CARRIER_FAVORABLE_ONLY")
        self.assertEqual(ruling_as_of("B-215958", DEC_1986), LATEST_HISTORICAL)
        self.assertEqual(ruling_as_of("B-215958", date(2026, 10, 24)), LATEST_HISTORICAL)
        with self.assertRaisesRegex(ResearchError, "GAO_UNKNOWN_CASE"):
            ruling_as_of("B-215958-UNRELATED", date(2026, 10, 24))
        with self.assertRaisesRegex(ResearchError, "GAO_AS_OF_DATE_INVALID"):
            ruling_as_of("B-215958", "2026-10-24")

    def test_separate_1969_517v_tariff_remains_distinct_from_overturned_190a(self):
        self.assertEqual(ruling_as_of("B-165091", date(1969, 1, 2)),
                         "NO_GAO_DECISION_AS_OF_DATE")
        self.assertEqual(ruling_as_of("B-165091", date(1969, 1, 3)),
                         "1969_517V_GAO_SUSTAINED_17980_DEDUCTION_DISTINCT_CASE")
        p1984 = _fixture(B215_1984)
        p1969 = _fixture(B165_1969)
        validate_historical_inputs(p1984, p1969)
        self.assertNotEqual(p1984["source"]["historical_tariff"],
                            p1969["source"]["historical_tariff"])
        self.assertFalse(p1984["population"]["per_bill_of_lading_labels_available"])
        self.assertFalse(p1969["limits"]["independent_invoice_error_accuracy_scoring_permitted"])
        self.assertIsNone(p1969["adjudications"][1]["finally_allowed_amount_cents"])
        self.assertEqual(p1969["adjudications"][0]["adjudicated_sustained_deduction_cents"],
                         17980)

    def test_all_three_original_official_sources_are_allowlisted_without_invoice_truth(self):
        for url in (PRIMARY_1969, PRIMARY_1984, PRIMARY_1986):
            self.assertEqual(safe_url(url), url)
            self.assertIn(url, SEEDS["freightrecovery"])
        self.assertEqual(len(REFERENCES), 3)
        self.assertEqual(REFERENCES[1][1], DEC_1986)
        report = make_receipt(date(2026, 10, 24))
        self.assertTrue(report["subsequent_history_overruled_1984"])
        self.assertEqual(report["latest_historical_case_disposition"], LATEST_HISTORICAL)
        self.assertEqual(report["original_gbls_in_initial_proceeding"], 55)
        self.assertEqual(report["original_sealed_gbls_in_initial_proceeding"], 53)
        self.assertEqual(report["unresolved_1984_remainder"], 2)
        self.assertEqual(report["per_gbl_outcomes_independently_proven"], 0)
        self.assertIsNone(report["separate_contrast_actual_refund_cents"])
        self.assertEqual(report["independent_invoice_accuracy_cases"], 0)
        self.assertEqual(report["verified_recovered_cash_cents"], 0)
        self.assertEqual(report["source_document_bytes_stored"], 0)
        self.assertFalse(report["source_specific_commercial_rights_verified"])
        self.assertFalse(report["current_customer_contract_applicability_proven"])
        self.assertEqual(report["owner_commercial_reuse_attestation"],
                         "OWNER_ATTESTED_NOT_SOURCE_VERIFIED")
        self.assertEqual(report["decision_chain_sources"][1]["official_url"], PRIMARY_1986)
        validate_receipt(report, at_date=date(2026, 10, 24))

    def test_fake_1984_final_ruling_even_with_rehashed_receipt_fails(self):
        original = make_receipt(date(2026, 10, 24))
        mutations = [
            ("subsequent_history_overruled_1984", False),
            ("latest_historical_case_disposition", "GAO_1984_CARRIER_FAVORABLE_FINAL"),
            ("reconsideration_date", "1986-02-17"),
            ("reconsideration_url", "https://evil.invalid/stale"),
            ("original_gbls_in_initial_proceeding", 57),
            ("per_gbl_outcomes_independently_proven", 53),
            ("independent_invoice_accuracy_cases", 55),
            ("verified_recovered_cash_cents", 17980),
            ("source_specific_commercial_rights_verified", True),
            ("current_customer_contract_applicability_proven", True),
            ("separate_contrast_actual_refund_cents", 17980),
        ]
        for field, bogus in mutations:
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed[field] = bogus
                changed["receipt_sha256"] = digest({
                    k: v for k, v in changed.items() if k != "receipt_sha256"})
                with self.assertRaises(ResearchError):
                    validate_receipt(changed, at_date=date(2026, 10, 24))

    def test_altered_original_manifest_or_tariff_crosswalk_fails_before_receipt(self):
        a = _fixture(B215_1984)
        b = _fixture(B165_1969)
        for field, wrong in (
            ("decision_reversals_with_recorded_numbered_seals", 55),
            ("remainder_cases_with_unresolved_disposition", 0),
            ("per_bill_of_lading_labels_available", True),
        ):
            with self.subTest(field=field):
                forged = copy.deepcopy(a)
                forged["population"][field] = wrong
                with self.assertRaises(ResearchError):
                    validate_historical_inputs(forged, b)
        cross = copy.deepcopy(b)
        cross["source"]["historical_tariff"] = a["source"]["historical_tariff"]
        with self.assertRaisesRegex(ResearchError, "GAO_SOURCE_CHAIN_SCOPE_OR_AUTHORITY_MISMATCH"):
            validate_historical_inputs(a, cross)
        with patch("freight.gao_adjudication_chronology.B215_1984",
                   Path("/nonexistent/untrusted-private-fixture")):
            with self.assertRaisesRegex(ResearchError, "GAO_CHRONOLOGY_SOURCE_FIXTURE_UNAVAILABLE"):
                make_receipt(date(2026, 10, 24))
        with self.assertRaisesRegex(ResearchError, "GAO_RECEIPT_DATE_INVALID"):
            make_receipt(date(1985, 1, 1))

    def test_research_receipt_reproduces_deterministically_then_detects_tampering(self):
        today = date(2026, 10, 24)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "history.json"
            report = run(output=output, at_date=today)
            self.assertTrue(report["1984_favorable_decision_overruled"])
            self.assertEqual(report["final_historical_authority"], LATEST_HISTORICAL)
            original_bytes = output.read_bytes()
            verified = run(output=output, verify_only=True, at_date=today)
            self.assertTrue(verified["verified"])
            self.assertEqual(original_bytes, output.read_bytes())
            changed = json.loads(original_bytes)
            changed["1984_favorable_decision_overruled"] = False
            output.write_text(json.dumps(changed))
            with self.assertRaises(ResearchError):
                run(output=output, verify_only=True, at_date=today)
            run(output=output, at_date=today)
            self.assertEqual(original_bytes, output.read_bytes())
            with self.assertRaisesRegex(ResearchError, "GAO_CHRONOLOGY_RECEIPT_STALE_OR_FUTURE"):
                validate_receipt(json.loads(original_bytes),
                                 at_date=today + timedelta(days=3))


if __name__ == "__main__":
    unittest.main()
