"""No claim that a real third-party reparations award equals recovered money."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from freight import public_fmc_adjudication_v1 as f

class FMCOriginalOrderTest(unittest.TestCase):
    def test_real_administratively_final_public_order_reconciles_not_paid(self):
        p=f.verified_public_order()
        self.assertEqual(p["documented_reparations_cents"],866879)
        self.assertEqual(p["documented_interest_cents"],98572)
        self.assertEqual(p["documented_final_reparations_order_cents"],965451)
        self.assertTrue(p["administratively_final_as_of_2026_04_28"])
        self.assertFalse(p["claimant_bank_or_payment_receipt_confirmed"])
        self.assertIsNone(p["actual_payment_verified_cents"])
        self.assertEqual(p["retally_validated_recovery_cents"],0)
        self.assertFalse(p["retally_invoice_data_used"])
        self.assertEqual(p["customer_recovery_or_marketing_authority"],"NOT_ESTABLISHED")

    def _forgery(self,edit):
        j=json.loads(f.SOURCE.read_text(encoding="utf8"))
        edit(j)
        with tempfile.TemporaryDirectory() as d:
            x=Path(d)/"forged.json";x.write_text(json.dumps(j))
            with patch.object(f,"SOURCE",x):
                with self.assertRaisesRegex(ValueError,"FMC_ORDER_EVIDENCE_OR_PAYMENT_STATUS_CHANGED"):
                    f.verified_public_order()

    def test_cannot_relabel_court_order_as_cash_recovered(self):
        self._forgery(lambda x:x.update({"actual_money_recovered_cents":965451}))
        self._forgery(lambda x:x.update({"proof_order_paid_or_settled":True}))
        self._forgery(lambda x:x.update({"third_party_payment_receipt_inspected":True}))
        self._forgery(lambda x:x.update({"retally_customer_recoveries_cents":965451}))

    def test_cannot_forge_extra_invoice_data_or_change_award(self):
        self._forgery(lambda x:x.update({"original_invoice_and_tariff_independently_replayed":True}))
        self._forgery(lambda x:x.update({"adjudicated_interest_cents":98573}))
        self._forgery(lambda x:x.update({"customer_invoice_count":10}))
        self._forgery(lambda x:x.update({"admin_final_as_of_notice_date":False}))
if __name__=="__main__":
    unittest.main()
