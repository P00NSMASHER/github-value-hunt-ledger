"""RETALLY synthetic customer-collateral regression checks.
No actual RecoveryOS transaction or customer outcome is asserted.
Run: python -m unittest discover -s freight/brand/mission2b -p 'test_*m2c*.py'
"""
from pathlib import Path
from decimal import Decimal
from datetime import date
import json,unittest
DATA=json.loads((Path(__file__).parent/'COMMERCIAL_TRUTH_M2C_V1.json').read_text())
D=lambda v:Decimal(str(v))
class CustomerCollateralM2C(unittest.TestCase):
    def test_hard_sample_boundary(self):
        self.assertFalse(DATA['financial_public_synthetic']['real_customer_result'])
        self.assertFalse(DATA['financial_public_synthetic']['source_level_verified'])
        self.assertEqual(DATA['financial_public_synthetic']['fee_eligibility_status'],'UNVERIFIED')
    def test_gross_to_net(self):
        f=DATA['financial_public_synthetic']
        self.assertEqual(D(f['gross_recovered_usd'])-D(f['reversal_usd']),D(f['net_recovered_usd']))
    def test_fee_difference_unallocated(self):
        f=DATA['financial_public_synthetic']
        self.assertEqual(D(f['net_recovered_usd'])-D(f['published_fee_eligible_usd']),D(f['difference_unallocated_usd']))
        self.assertNotEqual(f['fee_eligibility_status'],'VERIFIED')
    def test_stage_counts(self):
        f=DATA['financial_public_synthetic']
        counts=[f[x] for x in ('reviewed','candidates','supported','authorized','submitted','approved','posted')]
        self.assertEqual(counts,sorted(counts,reverse=True))
    def test_rate_effective(self):
        w=DATA['worked_invoice_synthetic']
        self.assertLessEqual(date.fromisoformat(w['rate_effective_from']),date.fromisoformat(w['date']))
        self.assertLessEqual(date.fromisoformat(w['date']),date.fromisoformat(w['rate_effective_to']))
    def test_worked_invoice(self):
        w=DATA['worked_invoice_synthetic']
        self.assertEqual(w['currency'],'USD')
        fuel=(D(w['base'])*D(w['fuel_percentage'])).quantize(D('.01'))
        expected=D(w['base'])+fuel+D(w['authorized_liftgate'])
        billed=expected+D(w['second_unsupported_liftgate'])
        self.assertEqual(expected,D(w['expected_total']))
        self.assertEqual(billed,D(w['billed_total']))
        self.assertEqual(billed-expected,D(w['difference']))
    def test_fake_source_label(self):
        w=DATA['worked_invoice_synthetic']
        self.assertTrue(w['source_ids_are_examples_not_evidence'])
        for field in ('shipment','invoice','rate_source','shipment_evidence'):
            self.assertTrue(w[field])
    def test_no_fee_approval(self):
        self.assertEqual(DATA['commercial_policy']['actual_fee_percentage'],'UNAPPROVED')
    def test_no_secure_intake_assumption(self):
        self.assertEqual(DATA['commercial_policy']['secure_transfer'],'NOT OPERATIONALLY VERIFIED')
    def test_claim_specific_customer_authorization(self):
        self.assertIn('Separate written',DATA['commercial_policy']['claim_authority'])
    def test_master_identity_hash_format(self):
        for k in ('wordmark_sha256','emblem_sha256'):
            self.assertEqual(len(DATA['brand'][k]),64)
if __name__ == '__main__':
    unittest.main()
