import unittest

from ai_business_os.hunter_bridge import HunterBridgeError, compile_hunter_seeds


class BusinessOsHunterBridgeTests(unittest.TestCase):
    def _plan(self, queue):
        return {"plan_hash": "a" * 64, "hunter_queue": queue}

    def _item(self, **overrides):
        item = {
            "work_id": "portfolio-plan:abc123",
            "initiative_id": "initiative-1",
            "initiative_key": "starblox",
            "initiative_name": "StarBlox",
            "metric_key": "runtime_auth_adapter",
            "gap_type": "MISSING",
            "priority": 92,
            "hunter_eligible": True,
            "required_source_type": "PUBLIC_GITHUB",
            "acceptance_target": "Find a tested public implementation with exact revision evidence.",
            "planning_only": True,
            "external_write_allowed": False,
            "human_approval_required_for_external_write": True,
        }
        item.update(overrides)
        return item

    def test_public_technical_gap_compiles_to_bounded_seed(self):
        seeds = compile_hunter_seeds(self._plan([self._item()]))
        self.assertEqual(1, len(seeds))
        seed = seeds[0]
        self.assertEqual("business_os_gap", seed["seed_type"])
        self.assertEqual("search", seed["work_action"])
        self.assertEqual("PUBLIC_GITHUB", seed["required_source_type"])
        self.assertTrue(seed["planning_only"])
        self.assertFalse(seed["external_write_allowed"])
        self.assertTrue(seed["human_approval_required_for_external_write"])
        self.assertEqual("portfolio-plan:abc123", seed["business_os_work_id"])
        self.assertEqual("a" * 64, seed["business_os_plan_hash"])
        self.assertTrue(seed["queries"])
        self.assertIn("README claims alone are insufficient", seed["instructions"]["verification_gate"])

    def test_non_public_source_fails_closed_even_if_queue_is_malformed(self):
        with self.assertRaisesRegex(HunterBridgeError, "outside the public technical allowlist"):
            compile_hunter_seeds(
                self._plan([self._item(required_source_type="BANK/GENERAL_LEDGER")])
            )

    def test_item_must_be_explicitly_hunter_eligible(self):
        with self.assertRaisesRegex(HunterBridgeError, "not explicitly Hunter-eligible"):
            compile_hunter_seeds(self._plan([self._item(hunter_eligible=False)]))

    def test_external_write_permission_is_rejected(self):
        with self.assertRaisesRegex(HunterBridgeError, "external writes must remain disabled"):
            compile_hunter_seeds(self._plan([self._item(external_write_allowed=True)]))

    def test_zero_hunter_queue_is_valid(self):
        self.assertEqual([], compile_hunter_seeds(self._plan([])))

    def test_output_is_deterministic(self):
        plan = self._plan([self._item()])
        self.assertEqual(compile_hunter_seeds(plan), compile_hunter_seeds(plan))


if __name__ == "__main__":
    unittest.main()
