"""Adverse original GAO settlement check: an executed deduction can be unlawful."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight import public_gao_setoff_reversal_v1 as g


class OriginalGAOImproperSetoff(unittest.TestCase):
    def test_original_disallowed_1979_gsa_offset_is_not_valid_net_savings(self):
        r=g.verified_historical_reversal()
        self.assertEqual(r["original_decisions"],1)
        self.assertEqual(r["prepetition_allowable_setoff_cents_reported"],214759)
        self.assertEqual(r["postpetition_GOVERNMENT_applied_offset_LATER_DISALLOWED_cents"],514105)
        self.assertTrue(r["original_offset_was_reported_executed"])
        self.assertFalse(r["illegal_postpetition_offset_is_valid_permanent_recovery"])
        self.assertTrue(r["GAO_said_allow_carrier_claim_if_otherwise_correct"])
        self.assertFalse(r["independent_carrier_repayment_bank_receipt_obtained"])
        self.assertIsNone(r["government_final_net_collections_credible_cents"])
        self.assertFalse(r["current_private_shipment_setoff_authorized"])
        self.assertEqual(r["actual_RETALLY_cash_recovered_cents"],0)
        self.assertEqual(r["commercial_claim_clearance"],"NO_GO")

    def _alter(self,edit):
        original=json.loads(g.SOURCE.read_text(encoding="utf-8"))
        edit(original)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"forged.json"
            p.write_text(json.dumps(original),encoding="utf-8")
            with patch.object(g,"SOURCE",p):
                with self.assertRaisesRegex(ValueError,"GAO_SETTLEMENT_REVERSAL_"):
                    g.verified_historical_reversal()

    def test_wrongful_applied_offset_cannot_be_called_legally_permanent(self):
        self._alter(lambda d:d.update({"postpetition_setoff_legally_upheld":True}))
        self._alter(lambda d:d.update({"net_GAO_retained_overcharge_collections_reported_as_final_cents":514105}))

    def test_government_allow_claim_is_not_actual_carrier_repayment(self):
        self._alter(lambda d:d.update({"independent_payment_back_to_carrier_verified":True}))
        self._alter(lambda d:d.update({"actual_carrier_refund_posted_cents":514105}))

    def test_no_customer_or_current_private_bankruptcy_authority(self):
        self._alter(lambda d:d.update({"retally_customer_payment_recovered_cents":514105}))
        self._alter(lambda d:d.update({"law_currently_applicable_to_private_commercial_shipper":"YES"}))

    def test_prepetition_and_postpetition_amounts_not_interchangeable(self):
        self._alter(lambda d:d.update({"prepetition_payable_bills_proper_setoff_cents":514105}))
        self._alter(lambda d:d.update({"other_unfiled_prepetition_overcharge_claims_cents":214759}))
        self._alter(lambda d:d.update({"numeric_buckets_not_interchangeable":False}))

    def test_source_and_publication_date_pinned(self):
        self._alter(lambda d:d.update({"decision_date":"1979-03-28"}))
        self._alter(lambda d:d.update({"source_original_pdf":"https://other.example/unverified.pdf"}))
        self._alter(lambda d:d.update({"source_full_pdf_bytes_sha256_verified":True}))

    def test_reversible_decision_not_an_eighth_positive_collection_case(self):
        from freight.public_gao_historical_collection_v1 import public_collection_report
        normal=public_collection_report()
        adverse=g.verified_historical_reversal()
        self.assertEqual(normal["historical_distinct_decisions"],7)
        self.assertEqual(normal["gao_reported_collection_events"],9)
        self.assertTrue(adverse["not_included_in_GAO_approved_historical_collection_tally"])
        self.assertIsNone(adverse["government_final_net_collections_credible_cents"])

if __name__=="__main__":
    unittest.main()
