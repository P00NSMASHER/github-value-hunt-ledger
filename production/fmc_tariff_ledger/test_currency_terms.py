import unittest

import currency_terms


class CurrencyTermTests(unittest.TestCase):
    def test_eur_and_gbp_amounts_are_preserved(self):
        text = """
        Tariff No. EU-4
        Effective June 1, 2026

        RULE 18 TERMINAL HANDLING
        Terminal handling charge is EUR 185 per container.

        RULE 22 DOCUMENTATION
        Documentation fee is £45 per B/L.
        """
        terms = currency_terms.extract_non_usd_terms(
            text,
            "https://example.test/tariff-eu4.txt",
        )
        self.assertTrue(any(
            t.rule_type == "terminal_handling"
            and t.currency == "EUR"
            and t.amount_value == "185"
            for t in terms
        ))
        self.assertTrue(any(
            t.rule_type == "rule:18"
            and t.currency == "EUR"
            and t.amount_value == "185"
            for t in terms
        ))
        self.assertTrue(any(
            t.rule_type == "documentation"
            and t.currency == "GBP"
            and t.amount_value == "45"
            for t in terms
        ))

    def test_currency_suffix_is_supported(self):
        text = """
        RULE 33 CHASSIS
        Chassis charge: 250 CAD per container.
        """
        terms = currency_terms.extract_non_usd_terms(
            text,
            "https://example.test/tariff.txt",
        )
        self.assertTrue(any(
            t.currency == "CAD" and t.amount_value == "250"
            for t in terms
        ))


if __name__ == "__main__":
    unittest.main()
