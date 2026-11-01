import json
import unittest
from pathlib import Path
from federal_audit_economics import evaluate

BASE = {
    'case':'base', 'identified_usd':'1000.00', 'modeled_collected_usd':'250.00',
    'hypothetical_fee_rate':'0.30', 'review_hours':'2',
    'labor_usd_hour':'45.00', 'overhead_usd':'10.00',
    'signed_contract':False, 'agency_buy_authority':False,
    'independent_receipt':False,
}

class FinancialAdversaries(unittest.TestCase):
    def check(self, **changes):
        row = dict(BASE); row.update(changes); return evaluate(row)

    def test_scenario_snapshot_and_exact_outcomes(self):
        snap = json.loads((Path(__file__).parent/'federal_audit_scenarios.json').read_text())
        expected = {
            'recovery_zero':('-100.00','0.00'),
            'recovery_10pct':('-70.00','30.00'),
            'recovery_25pct':('-25.00','75.00'),
            'near_break_even_fail':('-0.01','99.99'),
            'break_even':('0.00','100.00'),
            'near_100_contribution_fail':('99.99','199.99'),
            'hypothetical_100_contribution':('100.00','200.00'),
            'all_collected':('200.00','300.00')}
        self.assertEqual(set(expected), {r['case'] for r in snap['cases']})
        for row in snap['cases']:
            with self.subTest(case=row['case']):
                res=evaluate(row)
                self.assertEqual((res['hypothetical_contribution_usd'],res['hypothetical_fee_usd']),expected[row['case']])
                self.assertEqual(res['verified_owner_cash_usd'],'0.00')
                self.assertEqual(res['verified_collectible_usd'],'0.00')
                self.assertEqual(res['decision'],'NO_GO_FIRST_100_FEDERAL_DIRECT')
        self.assertFalse(snap['commercial_readiness']['external_customer_award_verified'])
        self.assertFalse(snap['commercial_readiness']['integrator_priority_changed'])

    def test_identified_but_uncollected_never_generates_fee(self):
        self.assertEqual(self.check(modeled_collected_usd='0.00')['hypothetical_fee_usd'],'0.00')

    def test_enforces_statutory_ceiling_scenario(self):
        self.assertEqual(self.check(hypothetical_fee_rate='0.90',modeled_collected_usd='1000.00')['hypothetical_fee_usd'],'500.00')

    def test_signed_flags_cannot_become_cash_evidence(self):
        r=self.check(signed_contract=True,agency_buy_authority=True,independent_receipt=True)
        self.assertEqual(r['verified_owner_cash_usd'],'0.00')
        self.assertEqual(r['actual_contract_status'],'NOT_VERIFIED')

    def test_recovered_more_than_identified_refused(self):
        with self.assertRaises(ValueError): self.check(modeled_collected_usd='1000.01')

    def test_negative_numbers_refused(self):
        for key in ('identified_usd','modeled_collected_usd','review_hours','labor_usd_hour','overhead_usd'):
            with self.subTest(key=key), self.assertRaises(ValueError): self.check(**{key:'-1'})

    def test_nonfinite_numbers_refused(self):
        for value in ('NaN','Infinity','-Infinity','sNaN'):
            with self.subTest(value=value), self.assertRaises(ValueError): self.check(identified_usd=value)

    def test_unbounded_large_number_refused(self):
        with self.assertRaises(ValueError): self.check(identified_usd='1e1000')

    def test_subcent_source_money_refused(self):
        for key in ('identified_usd','modeled_collected_usd','labor_usd_hour','overhead_usd'):
            with self.subTest(key=key), self.assertRaises(ValueError): self.check(**{key:'1.001'})

    def test_unknown_evidence_claim_field_refused(self):
        with self.assertRaises(ValueError): self.check(verified_owner_cash_usd='10000')

    def test_missing_evidence_refused(self):
        row=dict(BASE); del row['independent_receipt']
        with self.assertRaises(ValueError): evaluate(row)

    def test_boolean_as_money_refused(self):
        with self.assertRaises(ValueError): self.check(identified_usd=True)

    def test_untrusted_flag_types_refused(self):
        for value in ('yes',1,None):
            with self.subTest(value=value), self.assertRaises(ValueError): self.check(independent_receipt=value)

    def test_rate_over_100pct_refused(self):
        with self.assertRaises(ValueError): self.check(hypothetical_fee_rate='1.01')

    def test_rate_zero_no_fee(self):
        self.assertEqual(self.check(hypothetical_fee_rate='0')['hypothetical_fee_usd'],'0.00')

    def test_invalid_case_name_refused(self):
        with self.assertRaises(ValueError): self.check(case='')

    def test_public_sources_explicit_vendor_claim_classification(self):
        snap=json.loads((Path(__file__).parent/'federal_audit_scenarios.json').read_text())
        claims=[s for s in snap['sources'] if s['type']=='competition_vendor_claim']
        self.assertEqual(len(claims),2)
        self.assertEqual(len(snap['sources']),5)
        self.assertNotIn('collectible', snap['model_assumptions'].lower())

if __name__=='__main__': unittest.main()
