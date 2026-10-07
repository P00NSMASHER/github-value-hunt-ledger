"""Regression checks for independently specified TL probe; pytest discovers unittest."""
import unittest
from freight.lab.actual_engine_probe import expected_tl, probe

class TestIndependentFreightLab(unittest.TestCase):
    def test_minimum_charge_and_fuel_rounding(self):
        self.assertEqual(expected_tl(100,10000,1000,40),(10000,1000))
        self.assertEqual(expected_tl(100,0,1500,41),(4100,615))

    def test_real_engine_supported_tl_cases(self):
        output=probe(count=100,seed=41037)
        self.assertEqual((output['tp'],output['tn']),(40,60))
        for key in ('fp','fn','abstentions'):
            self.assertEqual(output[key],0)
        for key in ('exact_expected','exact_variance','traceable'):
            self.assertEqual(output[key],100)
        self.assertIn('NOT PRODUCTION ACCURACY',output['claim_boundary'])

    def test_replay_is_deterministic_except_timing(self):
        a,b=probe(count=25,seed=17),probe(count=25,seed=17)
        keys=('tp','tn','fp','fn','exact_expected','exact_variance','traceable')
        self.assertEqual({k:a[k] for k in keys},{k:b[k] for k in keys})

if __name__=='__main__':
    unittest.main()
