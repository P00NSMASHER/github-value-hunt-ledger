"""Small CI smoke suite for the full six-mode real-engine metamorphic probe."""
import unittest

from freight.lab.six_mode_metamorphic_probe import run


class TestSixModeMetamorphic(unittest.TestCase):
    def test_six_mode_billing_mutations_preserve_authority_and_variance(self):
        result = run(iterations=15, seed=90217)
        self.assertEqual(result["rated_calls"], result["base_gold_cases"] * 15)
        self.assertEqual(result["failure_count"], 0, result["failures"])
        self.assertEqual(set(result["by_mode"]), {
            "PARCEL", "LTL", "TL", "INTERMODAL", "AIR", "OCEAN"
        })
        self.assertEqual(result["scope"], "REAL_ENGINE_SYNTHETIC_6_MODE_METAMORPHIC_ONLY")

    def test_six_mode_mutations_replay_by_seed(self):
        left = run(iterations=7, seed=16439)
        right = run(iterations=7, seed=16439)
        self.assertEqual(left["by_mode"], right["by_mode"])
        self.assertEqual(left["failure_count"], right["failure_count"])
        self.assertEqual(left["failure_count"], 0)


if __name__ == "__main__":
    unittest.main()
