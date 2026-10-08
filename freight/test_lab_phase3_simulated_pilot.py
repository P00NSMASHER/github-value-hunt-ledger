import unittest
from freight.lab_phase3_simulated_pilot import simulated_cohort
class PilotTests(unittest.TestCase):
    def test_three_synthetic_customers_zero_real_money(self):
        p=simulated_cohort()
        self.assertEqual(p['simulated_customer_count'],3)
        self.assertEqual(p['accepted_real_customer_count'],0)
        self.assertEqual(p['actual_company_revenue_cents'],0)
        self.assertEqual(p['actual_customer_recovery_cents'],0)
        self.assertFalse(p['outside_carrier_bank_or_email_activity'])
        self.assertEqual(sum(x['observed_real_recovery_cents'] for x in p['cohort']),0)
    def test_no_recovery_case_is_kept(self):
        p=simulated_cohort()
        clean=[x for x in p['cohort'] if x['state']=='DEFENSIBLE_NO_RECOVERY']
        self.assertEqual(len(clean),1)
        self.assertEqual(clean[0]['economic_scenario']['expected_collected_fee_cents'],0)
    def test_case_one_is_bound_to_previous_independent_synthetic_replay(self):
        p=simulated_cohort()
        self.assertEqual(p['cohort'][0]['simulated_accounting']['simulated_net_recovered_cents'],500)
        self.assertEqual(len(p['independent_synthetic_financial_receipt']),64)
if __name__=='__main__':unittest.main()
