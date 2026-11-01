"""Proof-bound, decimal-safe freight money conversion regression tests."""
import unittest

from recoveryworks.branches.freight_audit_vendor import to_cents


class FreightMoneyConversionTests(unittest.TestCase):
    def test_half_cent_values_round_half_up_not_binary_even(self):
        for token, expected in (
            ("1.005", 101), ("-1.005", -101), (1.005, 101),
            ("2.675", 268), ("$1,234.565", 123457),
            ("$-12.34", -1234), ("-.50", -50), (".50", 50), ("-$.50", -50),
            ("(12.345)", -1235), (12, 1200),
        ):
            with self.subTest(token=token):
                self.assertEqual(to_cents(token), expected)

    def test_existing_money_formats(self):
        self.assertEqual(to_cents("$1,234.56"), 123456)
        self.assertEqual(to_cents("(12.34)"), -1234)
        self.assertEqual(to_cents("0"), 0)
        self.assertEqual(to_cents(None), 0)

    def test_oversized_nonfinite_or_malformed_amounts_are_never_positive(self):
        rejected = [
            float("nan"), float("inf"), float("-inf"), "Infinity", "-Infinity",
            "NaN", "1e10000", "999999999999999999999999999999",
            "90071992547409.92", "-90071992547409.92",
            "123..45", "1,23.00", "12 34", "$$1.00",
            "$1.00\nBcc:private@example.invalid", "-(12.34)", "(12.34",
            "(12.34))", "-$99999999999999999999.00",
            "not-money", True,
        ]
        for value in rejected:
            with self.subTest(value=str(value)):
                self.assertEqual(to_cents(value), 0)

    def test_interoperable_safe_boundary_and_near_boundary(self):
        self.assertEqual(to_cents("90071992547409.91"), 9007199254740991)
        self.assertEqual(to_cents("-90071992547409.91"), -9007199254740991)
        self.assertEqual(to_cents("90071992547409.915"), 0)
        self.assertEqual(to_cents("$0.01"), 1)
        self.assertEqual(to_cents("-0.01"), -1)

    def test_all_integer_cent_amounts_in_deterministic_sample_roundtrip(self):
        for n in range(1000):
            cents = (n * 214013 + 2531011) % 100_000_000
            amount = f"{cents // 100}.{cents % 100:02d}"
            self.assertEqual(to_cents(amount), cents)


if __name__ == "__main__":
    unittest.main()
