"""Synthetic only: tests official historical rate link discovery safety."""
from __future__ import annotations

import unittest
from freight.research.cma_2022_tariff_discovery import (
    DiscoveryHold, URL, _official, extract_official_rate_links, public_report,
)


def page(*links):
    return ("<!DOCTYPE html><html><body>" + "".join(
        '<a href="'+url+'">'+name+'</a>' for url,name in links
    )+"</body></html>").encode("utf-8")


class TestHistoricalTariffLinks(unittest.TestCase):
    def test_original_export_detention_pdf_is_identified(self):
        got=extract_official_rate_links(page(
          ("/assets/public/pdf/Export%20Detention%20Charges%20-%2020%20Jan%202022.pdf",
           "Export Detention 20th Jan 2022")))
        self.assertEqual(len(got),1)
        self.assertTrue(got[0]["detention_named"])
        self.assertTrue(got[0]["export_specific"])

    def test_old_link_outside_publisher_is_never_fetched(self):
        got=extract_official_rate_links(page(
            ("https://www.cma-cgm.com.evil.invalid/assets/public/pdf/Export%20Detention.pdf",
             "Export Detention"),
            ("https://evil.invalid/a.pdf","export detention"),
        ))
        self.assertEqual(got,[])

    def test_no_guess_by_english_title_without_real_pdf_anchor(self):
        self.assertEqual(extract_official_rate_links(
          page(("/india/news/more","Export Detention Tariff"),)),[])

    def test_demurrage_is_distinct_from_detention(self):
        g=extract_official_rate_links(page(
          ("/assets/public/documents/Export%20Demurrage%20Charges%20-%2020%20Jan%202022_0.pdf",
           "Export Demurrage January 2022")))
        self.assertFalse(g[0]["detention_named"])
        self.assertTrue(g[0]["demurrage_named"])

    def test_encoding_of_link_text_and_relative_2022_pdf(self):
        g=extract_official_rate_links(page((
            "https://www.cma-cgm.com/assets/public/pdf/Export%20Detention%20Charges.pdf",
            "Client Advisory &amp; Tariff")) )
        self.assertEqual(len(g),1)
        self.assertIn("pdf",g[0]["url"])

    def test_path_traversal_is_rejected(self):
        self.assertFalse(_official(
          "https://www.cma-cgm.com/assets/public/pdf/%2e%2e/secret.pdf",pdf=True))

    def test_username_host_spoof_rejected(self):
        self.assertFalse(_official(
          "https://name:pw@www.cma-cgm.com/assets/public/pdf/export_detention.pdf",pdf=True))

    def test_html_size_limit(self):
        with self.assertRaisesRegex(DiscoveryHold,"OVERSIZED_OR_EMPTY"):
            extract_official_rate_links(b"")

    def test_zero_links_does_not_claim_tariff_or_bank_clearance(self):
        got=public_report(page(("/assets/public/pdf/random.pdf","random")))
        self.assertEqual(got["official_pdf_links"],[])
        self.assertFalse(got["original_shipment_rate_applicability_verified"])
        self.assertFalse(got["customer_settlement_verified"])

    def test_deduplicate_same_pdf_link_and_prefer_detention(self):
        items=[
          ("/assets/public/pdf/Export%20Demurrage.pdf","Demurrage"),
          ("/assets/public/pdf/Export%20Detention.pdf","Detention"),
          ("/assets/public/pdf/Export%20Detention.pdf","Detention again"),
        ]
        got=extract_official_rate_links(page(*items))
        self.assertEqual(len(got),2)
        self.assertTrue(got[0]["detention_named"])


if __name__=="__main__":
    unittest.main()
