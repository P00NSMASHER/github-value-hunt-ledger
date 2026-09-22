import unittest

import shaq_parse


PORT_SAMPLE = """Found 3 port(s):

  Aarhus (DKAAR) [Denmark] - aka: Aarhus, AAR
  AEX (XXXXX) [Unknown]
  Altamira (MXATM) [Mexico]
"""

BATCH_SAMPLE = """Batch freight rate query (3 route(s)):

[1] Shenzhen to Los Angeles 40HC
  Parsed: Shenzhen -> Los Angeles | 40HQ
  No currently-valid rates for this route; data needs to be added for it.

[2] Shanghai to Hamburg 40HC
  Parsed: Shanghai -> Hamburg | 40HQ
  Found 6 valid rate(s); container types: 40HQ
    40HQ 3400.0 USD (valid 2026-09-20 to 2026-10-07)
    40HQ 3450.0 USD (valid 2026-09-20 to 2026-10-07)
    40HQ 3500.0 USD (valid 2026-09-20 to 2026-10-07)

[3] Ningbo to Long Beach 20GP
  Parsed: Ningbo -> Long Beach | 20GP
  No currently-valid rates for this route; data needs to be added for it.

Note: rates are spot market prices; use the booking flow for firm quotes.
"""


class ShaqParseTests(unittest.TestCase):
    def test_port_parser_preserves_unknown_codes(self):
        total, rows = shaq_parse.parse_ports(PORT_SAMPLE)
        self.assertEqual(total, 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].port_code, "DKAAR")
        self.assertEqual(rows[0].country, "Denmark")
        self.assertEqual(rows[0].aliases, ["Aarhus", "AAR"])
        self.assertIsNone(rows[1].port_code)
        self.assertIsNone(rows[1].country)

    def test_batch_parser_labels_live_output_spot_market(self):
        parsed = shaq_parse.parse_batch_rates(BATCH_SAMPLE)
        self.assertEqual(parsed["rate_kind"], "SPOT_MARKET")
        self.assertEqual(len(parsed["rates"]), 3)
        self.assertTrue(all(r["rate_kind"] == "SPOT_MARKET" for r in parsed["rates"]))

    def test_batch_parser_does_not_claim_visible_rows_are_complete(self):
        parsed = shaq_parse.parse_batch_rates(BATCH_SAMPLE)
        route = parsed["routes"][1]
        self.assertEqual(route["advertised_rate_count"], 6)
        self.assertEqual(route["parsed_visible_rate_count"], 3)
        self.assertEqual(route["status"], "RATES_FOUND")

    def test_no_rate_routes_are_retained_as_negative_observations(self):
        parsed = shaq_parse.parse_batch_rates(BATCH_SAMPLE)
        self.assertEqual(parsed["routes"][0]["status"], "NO_CURRENT_RATES")
        self.assertEqual(parsed["routes"][2]["status"], "NO_CURRENT_RATES")

    def test_validity_dates_are_preserved(self):
        parsed = shaq_parse.parse_batch_rates(BATCH_SAMPLE)
        first = parsed["rates"][0]
        self.assertEqual(first["valid_from"], "2026-09-20")
        self.assertEqual(first["valid_to"], "2026-10-07")
        self.assertEqual(first["currency"], "USD")


if __name__ == "__main__":
    unittest.main()
