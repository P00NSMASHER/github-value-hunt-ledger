"""Safe, offline synthetic-only checks for public case attachment discovery."""
import unittest
from freight.research.sungold_court_link_probe import ProbeHold, inspect_public_source


def page(*bits):
    return ("<!doctype html><html><body>"+"".join(bits)+"</body></html>").encode("utf-8")


class TestSungoldCourtLinkProbe(unittest.TestCase):
    def test_download_court_copy_button_never_invents_original_trial_exhibits(self):
        r=inspect_public_source(page(
          "<button id='copy' type='button'>Download Court Copy</button>"))
        self.assertIn("Download Court Copy",r["relevant_buttons"])
        self.assertEqual(r["relevant_public_links"],[])
        self.assertFalse(r["standalone_trial_exhibit_originals_verified"])
        self.assertFalse(r["customer_postjudgment_bank_settlement_verified"])

    def test_explicit_pdf_attachment_stays_link_not_admitted_document(self):
        r=inspect_public_source(page(
          "<a href='https://delhidistrictcourts.nic.in/uploads/case.pdf'>Judgment PDF</a>"))
        self.assertEqual(r["relevant_public_links"][0]["host"],
                         "delhidistrictcourts.nic.in")
        self.assertEqual(r["relevant_public_links"][0]["label_category"],"PDF")
        self.assertFalse(r["original_bank_statement_downloaded"])

    def test_form_present_is_not_submitted(self):
        r=inspect_public_source(page(
           "<form method='POST' action='/doc/161666818/'><button>Get in PDF</button></form>"))
        self.assertEqual(r["form_methods"],["POST"])
        self.assertIn("Get in PDF",r["relevant_buttons"])
        self.assertFalse(r["standalone_trial_exhibit_originals_verified"])

    def test_tracked_query_token_and_external_host_not_exposed(self):
        r=inspect_public_source(page(
           "<a href='https://evil.example/bank.pdf?token=secret'>Exhibit PDF</a>",
           "<a href='https://indiankanoon.org/doc/161666818/?auth=secret'>Download Court Copy</a>"))
        self.assertEqual(len(r["relevant_public_links"]),1)
        self.assertEqual(r["relevant_public_links"][0]["path"],"/doc/161666818/")
        self.assertTrue(r["relevant_public_links"][0]["has_query"])
        self.assertNotIn("secret",str(r))

    def test_blank_document_held(self):
        with self.assertRaisesRegex(ProbeHold,"EMPTY_OR_OVERSIZED"):
            inspect_public_source(b"")

    def test_non_html_response_held(self):
        with self.assertRaisesRegex(ProbeHold,"NOT_HTML"):
            inspect_public_source(b"%PDF-1.4 trailer")

    def test_unrelated_links_dont_count_as_court_exhibits(self):
        r=inspect_public_source(page(
          "<a href='https://indiankanoon.org/pricing/'>Pricing</a>",
          "<a href='https://indiankanoon.org/login/'>Sign in</a>"))
        self.assertEqual(r["relevant_public_links"],[])
        self.assertTrue(r["source_court_judgment_not_trial_evidence"])


if __name__=="__main__":
    unittest.main()
