"""Fail closed on fractional/boolean money values at proof and settlement boundaries."""
import unittest
from freight.contracts import AuthorityRef, PopulationRow, SettlementEvent, RecoveryLedger, freeze_population, freeze_truth, make_finding
class MoneyCentsBoundaries(unittest.TestCase):
    def _finding(self, **overrides):
        kwargs=dict(finding_id="F1",buyer_id="buyer",business_unit="unit",invoice_id="INV1",
                    shipment_id="S1",customer_id="C1",carrier_id="K1",currency="USD",
                    authority_id="A1",expected_cents=10000,actual_cents=15000,status="VALIDATED")
        return make_finding(**{**kwargs,**overrides})
    def test_fractional_or_bool_finding_amount_cannot_be_hashed_as_valid_money(self):
        for field in ("expected_cents","actual_cents"):
            for value in (0.5,True,False,"100"):
                with self.subTest(field=field,value=value):
                    with self.assertRaisesRegex(ValueError,"exact integer cents"):
                        self._finding(**{field:value})
    def test_fractional_or_bool_settlement_cannot_be_recorded_or_fee_eligible(self):
        population=freeze_population("buyer","unit","all invoices",(
            PopulationRow("INV1","S1","C1","K1","USD","invoice-source"),))
        authority=AuthorityRef("A1","buyer","unit","C1","K1","USD","authority-source")
        truth=freeze_truth(population,(authority,),(self._finding(),))
        ledger=RecoveryLedger(truth)
        for value in (0.5,True,"100"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,"exact integer cents"):
                    ledger.apply(SettlementEvent(buyer_id="buyer",business_unit="unit",
                        settlement_id="S2",finding_id="F1",amount_cents=value,
                        currency="USD",source_hash="settlement-source"))
        self.assertEqual(ledger.certificate("F1").realized_cents,0)
if __name__=="__main__":unittest.main()
