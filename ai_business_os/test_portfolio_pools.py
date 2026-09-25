import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"ai_business_os"/"PORTFOLIO_POOLS_V1.json"

class PortfolioPoolContractTests(unittest.TestCase):
    def test_starblox_isolated_from_b2b_cash_flow(self):
        data=json.loads(CONTRACT.read_text())
        pools={p["pool_key"]:p for p in data["pools"]}
        self.assertEqual(["starblox"],pools["consumer-rnd"]["initiatives"])
        self.assertNotIn("starblox",pools["b2b-cash-flow"]["initiatives"])
        self.assertFalse(pools["consumer-rnd"]["cash_allocation_allowed"])
        self.assertNotIn("CASH_CENTS",pools["consumer-rnd"]["allowed_resource_types"])

    def test_pool_separation_canaries_passed(self):
        data=json.loads(CONTRACT.read_text())
        self.assertTrue(data["canary"]["consumer_cash_rejected"])
        self.assertTrue(data["canary"]["consumer_b2b_metric_rejected"])
        self.assertEqual(0,data["canary"]["persistent_synthetic_rows"])

if __name__=="__main__":
    unittest.main()
