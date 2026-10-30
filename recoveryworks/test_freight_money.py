import unittest

from recoveryworks.branches.freight_audit_vendor import to_cents


class FreightMoneyConversionTests(unittest.TestCase):
    def test_half_cent_values_use_currency_half_up_rounding(self):
        self.assertEqual(to_cents("1.005"), 101)
        self.assertEqual(to_cents("-1.005"), -101)
        self.assertEqual(to_cents(1.005), 101)
        self.assertEqual(to_cents("$1,234.565"), 123457)

    def test_non_finite_numeric_values_fail_to_zero_without_crashing(self):
        self.assertEqual(to_cents(float("nan")), 0)
        self.assertEqual(to_cents(float("inf")), 0)
        self.assertEqual(to_cents("-Infinity"), 0)

    def test_existing_currency_formats_remain_supported(self):
        self.assertEqual(to_cents("$1,234.56"), 123456)
        self.assertEqual(to_cents("(12.34)"), -1234)
        self.assertEqual(to_cents(12), 1200)
        self.assertEqual(to_cents(None), 0)
        self.assertEqual(to_cents("not-money"), 0)


if __name__ == "__main__":
    unittest.main()
