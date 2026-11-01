import unittest
from copy import deepcopy
from private_freight_cash_gate_031 import estimate, min_recovered_for_fee

BASE = {
  'case':'synthetic_example', 'identified_usd':'1000.00',
  'modeled_customer_recovery_usd':'666.67',
  'modeled_attributable_recovery_usd':'666.67',
  'modeled_reversal_usd':'0.00', 'hypothetical_fee_rate':'0.30',
  'labor_hours':'2', 'hourly_labor_usd':'45.00', 'direct_cost_usd':'10.00',
  'signed_agreement':False, 'customer_credit_verified':False,
  'owner_bank_receipt_verified':False,
}

class TestHypotheticalFirstHundred(unittest.TestCase):
    def case(self, **kw):
        row=deepcopy(BASE);row.update(kw);return estimate(row)
    def test_default_margin(self):
        self.assertEqual(self.case()['fictional_contribution_usd'],'100.00')
    def test_no_recovery_negative_cost(self):
        x=self.case(modeled_customer_recovery_usd='0',modeled_attributable_recovery_usd='0');self.assertEqual(x['fictional_contribution_usd'],'-100.00')
    def test_attributable_excludes_incumbent_claims(self):
        x=self.case(modeled_attributable_recovery_usd='0');self.assertEqual(x['fictional_fee_usd'],'0.00')
    def test_reversal_excludes_feeable(self):
        x=self.case(modeled_attributable_recovery_usd='600.00',modeled_reversal_usd='66.67');self.assertEqual(x['fictional_fee_usd'],'180.00')
    def test_reversal_too_large_rejected(self):
        with self.assertRaises(ValueError):self.case(modeled_reversal_usd='700.00')
    def test_attributable_above_net_rejected(self):
        with self.assertRaises(ValueError):self.case(modeled_reversal_usd='1.00')
    def test_recovery_above_identified_rejected(self):
        with self.assertRaises(ValueError):self.case(modeled_customer_recovery_usd='1000.01')
    def test_rate_above_100_rejected(self):
        with self.assertRaises(ValueError):self.case(hypothetical_fee_rate='1.01')
    def test_rate_zero_allowed(self):
        self.assertEqual(self.case(hypothetical_fee_rate='0')['fictional_fee_usd'],'0.00')
    def test_nan_inf_negative_rejected(self):
        for value in ('NaN','Infinity','-0.01'):
            with self.subTest(v=value),self.assertRaises(ValueError):self.case(direct_cost_usd=value)
    def test_bools_cannot_be_money(self):
        with self.assertRaises(ValueError):self.case(identified_usd=True)
    def test_subcent_money_rejected(self):
        with self.assertRaises(ValueError):self.case(direct_cost_usd='0.001')
    def test_invalid_boolean_receipt_rejected(self):
        with self.assertRaises(ValueError):self.case(owner_bank_receipt_verified='true')
    def test_flags_never_make_cash_proof(self):
        x=self.case(signed_agreement=True,customer_credit_verified=True,owner_bank_receipt_verified=True)
        self.assertEqual(x['owner_cash_verified_usd'],'0.00')
        self.assertEqual(x['owner_collectible_observed_usd'],'0.00')
    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):self.case(owner_paid_usd='999.00')
    def test_missing_field_rejected(self):
        x=deepcopy(BASE);del x['signed_agreement']
        with self.assertRaises(ValueError):estimate(x)
    def test_no_fee_without_attribution_even_with_customer_credit(self):
        self.assertEqual(self.case(modeled_attributable_recovery_usd='0',customer_credit_verified=True)['fictional_fee_usd'],'0.00')
    def test_100_gross_floor_30_percent(self):
        self.assertEqual(min_recovered_for_fee('100.00','0.30'),'333.34')
    def test_1000_gross_floor_30_percent(self):
        self.assertEqual(min_recovered_for_fee('1000.00','0.30'),'3333.34')
    def test_100_contribution_floor_30_percent(self):
        self.assertEqual(min_recovered_for_fee('200.00','0.30'),'666.67')
    def test_1000_contribution_floor_30_percent(self):
        self.assertEqual(min_recovered_for_fee('1100.00','0.30'),'3666.67')
    def test_competitor_20_percent_floor(self):
        self.assertEqual(min_recovered_for_fee('200.00','0.20'),'1000.00')
    def test_competitor_35_percent_floor(self):
        self.assertEqual(min_recovered_for_fee('200.00','0.35'),'571.43')
    def test_rate_zero_target_rejected(self):
        with self.assertRaises(ValueError):min_recovered_for_fee('100.00','0')
    def test_fractional_cost_rounded_up(self):
        x=self.case(labor_hours='0.001', hourly_labor_usd='35.00',direct_cost_usd='0.00');self.assertEqual(x['fictional_cost_usd'],'0.04')
    def test_fractional_fee_rounded_down(self):
        x=self.case(hypothetical_fee_rate='0.333333');self.assertEqual(x['fictional_fee_usd'],'222.22')

if __name__=='__main__':unittest.main()
