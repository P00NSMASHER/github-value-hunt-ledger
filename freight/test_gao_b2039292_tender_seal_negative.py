"""Offline official-GAO independent historical freight false-positive control.

B-203929.2 is an independently adjudicated REVERSAL of GSA's audit, not a
modern private-customer overcharge. No network, provider, engine, or money call.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path


class GAOB2039292TenderSealNegativeTests(unittest.TestCase):
    @staticmethod
    def pack():
        p = Path(__file__).with_name("fixtures") / "gao_b2039292_tender_seal_negative_candidate_v0.json"
        return json.loads(p.read_text(encoding="utf-8"))

    @staticmethod
    def _value(data, path):
        for part in path.split("."):
            data = data[part]
        return data

    @classmethod
    def held(cls, pack):
        expected = {
            "schema_version": "0.1.0",
            "pack_id": "GAO_B2039292_TENDER_SEAL_NEGATIVE_CANDIDATE_V0",
            "evaluation_family": "FREIGHT_HISTORICAL_INDEPENDENT_ADJUDICATION_NEGATIVE_NOT_ACCOUNTING_RECONCILIATION",
            "admission_status": "HISTORICAL_PUBLIC_NEGATIVE_CONTROL_ONLY_NO_MODERN_CUSTOMER_ACCURACY_LABEL",
            "source.official_decision_url": "https://www.gao.gov/products/b-203929.2",
            "source.official_pdf_url": "https://www.gao.gov/assets/b-203929.2.pdf",
            "source.decision_id": "B-203929.2",
            "source.decision_date": "1982-04-09",
            "source.inspected_original_pdf_pages": [1, 2, 3],
            "source.rights_url": "https://www.gao.gov/copyright",
            "source.original_publisher_pdf_http_bytes_held": False,
            "source.original_publisher_pdf_sha256": None,
            "source.original_signed_gbl_or_full_tender_266_pages_held": False,
            "source.third_party_tender_reproduction_rights": "UNVERIFIED_HOLD",
            "source.commercial_modern_rating_authority": "UNKNOWN",
            "cohort.exact_shipment_date": "UNKNOWN",
            "cohort.heldout_from_private_commercial_invoice_corpus": True,
            "cohort.modern_customer_invoice_records": 0,
            "adjudicated_facts.carrier": "American Farm Lines Inc.",
            "adjudicated_facts.government_bol": "S-0,551,728",
            "adjudicated_facts.exclusive_use_requested_and_furnished": True,
            "adjudicated_facts.shipper_applied_numbered_seals": False,
            "adjudicated_facts.paid_initial_charge_based_on_tariff": True,
            "adjudicated_facts.tender_number": 266,
            "adjudicated_facts.tender_item_179_requires_shipper_seals_for_discount": True,
            "adjudicated_facts.tender_item_130_optional_exclusive_use_seal_does_not_waive_item_179": True,
            "adjudicated_facts.adjudicated_outcome": "GAO_REVERSED_GSA_OVERCHARGE_AUDIT",
            "adjudicated_facts.valid_historical_gsa_deduction": False,
            "adjudicated_facts.original_paid_charge_cents": None,
            "adjudicated_facts.original_gsa_deduction_cents": None,
            "adjudicated_facts.final_refund_or_cash_receipt_cents": None,
            "labels.independently_adjudicated_historical_negative_cases": 1,
            "labels.independently_adjudicated_historical_positive_cases": 0,
            "labels.independently_scored_present_day_invoice_error_cases": 0,
            "labels.independently_scored_present_day_clean_invoice_cases": 0,
            "labels.independently_verified_exact_dollar_labels": 0,
            "labels.original_publisher_bytes_sha256": "UNKNOWN",
            "labels.independent_recovery_and_settlement": "UNKNOWN",
            "labels.freight_customer_precision_recall": "UNKNOWN",
            "labels.verified_retally_customer_recovery_cents": 0,
            "quality.historical_agency_adjudication_ground_truth": "INDEPENDENT_NEGATIVE_GSA_AUDIT_ACTION_REVERSED",
            "quality.commercial_customer_scoring_rights": "UNVERIFIED_HOLD",
            "quality.no_network_provider_calls_or_production_changes": True,
            "consumer_handoffs.retally_recoveryos_engineering": ":12",
            "consumer_handoffs.independent_qa": ":44",
            "consumer_handoffs.engine_code_modified": False,
            "consumer_handoffs.production_release_authorized": False,
        }
        try:
            if any(cls._value(pack, key) != value for key, value in expected.items()):
                return False
            controls = pack["synthetic_negative_controls"]
            return (
                len(controls) == 6 and len({c["id"] for c in controls}) == 6
                and all(c["kind"] == "SYNTHETIC" and
                        c["expected"].startswith("REJECT_") for c in controls)
            )
        except (KeyError, TypeError, ValueError):
            return False

    def test_real_agency_adjudication_negative_and_unknown_money(self):
        x = self.pack()
        self.assertTrue(self.held(x))
        self.assertIsNone(x["adjudicated_facts"]["original_gsa_deduction_cents"])
        self.assertEqual(x["labels"]["independently_scored_present_day_invoice_error_cases"], 0)

    def test_synthetic_forged_positive_truth_and_source_custody_fail(self):
        source = self.pack()
        self.assertTrue(self.held(source))
        attacks = [
            ("adjudicated_facts.valid_historical_gsa_deduction", True),
            ("adjudicated_facts.adjudicated_outcome", "GSA_OVERCHARGE_UPHELD"),
            ("adjudicated_facts.tender_item_179_requires_shipper_seals_for_discount", False),
            ("adjudicated_facts.tender_item_130_optional_exclusive_use_seal_does_not_waive_item_179", False),
            ("adjudicated_facts.original_gsa_deduction_cents", 15000),
            ("adjudicated_facts.final_refund_or_cash_receipt_cents", 15000),
            ("source.original_publisher_pdf_sha256", "f" * 64),
            ("source.original_publisher_pdf_http_bytes_held", True),
            ("source.commercial_modern_rating_authority", "VERIFIED"),
            ("source.third_party_tender_reproduction_rights", "CLEARED"),
            ("labels.independently_scored_present_day_invoice_error_cases", 1),
            ("labels.verified_retally_customer_recovery_cents", 15000),
            ("consumer_handoffs.production_release_authorized", True),
        ]
        for path, value in attacks:
            with self.subTest(synthetic_mutation=path):
                x = json.loads(json.dumps(source))
                pointer = x
                parts = path.split(".")
                for part in parts[:-1]:
                    pointer = pointer[part]
                pointer[parts[-1]] = value
                self.assertFalse(self.held(x))


if __name__ == "__main__":
    unittest.main()
