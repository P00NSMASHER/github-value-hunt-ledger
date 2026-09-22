import unittest

import crawler_v2 as v2
import publisher_adapters as publishers


class PublisherAdapterTests(unittest.TestCase):
    def test_ap_tariffs_org_number_seed(self):
        seeds = publishers.seed_urls(
            "https://www.aptariffs.com",
            "034442",
            "Example Shipping LLC",
            "",
        )
        urls = {s.url for s in seeds}
        self.assertIn(
            "https://tariff.aptariffs.com/member/tariffs?locale=en&org_nbr=034442&view=all",
            urls,
        )
        self.assertIn(
            "https://tariff.aptariffs.com/member/tariffs/rules?locale=en&tar_code=034442-001&view=all",
            urls,
        )

    def test_ratewave_entity_matching(self):
        follow, parse = publishers.allow_cross_publisher_link(
            "ratewave",
            "https://www.ratewave5.com/acme/index.htm",
            "ACME Ocean Transport",
            "123456",
            "ACME OCEAN TRANSPORT LLC",
            "",
        )
        self.assertTrue(follow)
        self.assertTrue(parse)

    def test_login_page_is_not_entity_evidence(self):
        text = "Secure Login. Please enter your User ID and Password."
        self.assertTrue(
            publishers.auth_or_login_page(text, "https://example.test/login")
        )
        self.assertFalse(
            publishers.should_parse_entity_terms(
                family="dpi",
                explicit_parse_flag=True,
                text=text,
                url="https://members.dpiusa.com/login",
                organization_no="123456",
                legal_name="Example Shipping LLC",
                trade_name="",
            )
        )

    def test_generic_rule_sections_are_preserved(self):
        text = """
        TARIFF NO. 99
        Effective May 1, 2026

        RULE 2. APPLICATION OF RATES AND CHARGES
        Rates apply according to the tariff in effect when cargo is received.

        RULE 21. DEMURRAGE
        Free time is 5 calendar days.
        Thereafter demurrage is USD 175 per day.
        """
        terms = v2.extract_terms_v2(text, "https://example.test/tariff99.txt")
        self.assertTrue(any(
            t.rule_type == "rule:2" and t.term_kind == "rule_text"
            for t in terms
        ))
        self.assertTrue(any(
            t.rule_type == "rule:21"
            and t.term_kind == "money"
            and t.amount_value == "175"
            for t in terms
        ))
        self.assertTrue(any(
            t.rule_type == "demurrage"
            and t.term_kind == "money"
            and t.amount_value == "175"
            for t in terms
        ))

    def test_publisher_landing_page_not_misattributed(self):
        text = "Tariff publisher serving thousands of carriers. No entity-specific content."
        self.assertFalse(
            publishers.should_parse_entity_terms(
                family="ratewave",
                explicit_parse_flag=False,
                text=text,
                url="https://www.ratewave.com/rate.html",
                organization_no="123456",
                legal_name="Example Shipping LLC",
                trade_name="",
            )
        )

    def test_generic_rule_number_heading_is_not_a_rule(self):
        text = """
        RULE NO. 15
        RULE 15 DEMURRAGE
        Demurrage is USD 100 per day.
        """
        terms = v2.extract_terms_v2(text, "https://example.test/tariff.txt")
        self.assertFalse(any(t.rule_type.lower() in {"rule:no", "rule:number"} for t in terms))
        self.assertTrue(any(t.rule_type == "rule:15" for t in terms))

    def test_known_shared_publishers_are_not_direct(self):
        for url in (
            "https://pctb.com",
            "https://oceantariff.com",
            "https://sumnertariff.com",
            "https://ustraf.com",
            "https://myrates.descartes.com",
            "https://plustariff.com",
        ):
            self.assertNotEqual(publishers.family_for(url), "direct")

    def test_generic_maritime_words_do_not_establish_entity_scope(self):
        text = "Ocean shipping transport carrier tariff publishing services."
        self.assertFalse(
            publishers.entity_scoped_text(
                text,
                "999999",
                "OCEAN TRANSPORT LINES LLC",
                "",
            )
        )
        self.assertTrue(
            publishers.entity_scoped_text(
                "FMC Organization 999999 Ocean transport tariff.",
                "999999",
                "OCEAN TRANSPORT LINES LLC",
                "",
            )
        )


if __name__ == "__main__":
    unittest.main()
