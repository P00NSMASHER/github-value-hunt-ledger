"""Regression gates for the RETALLY visual-finishing PR (stdlib only)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BRAND = ROOT / "brand"

class RetallyFinishingTests(unittest.TestCase):
    def test_restrained_colors_preserve_typography_and_mobile_guard(self):
        css=(SITE / "foundry.css").read_text(encoding="utf-8")
        self.assertIn("Final RETALLY forest/emerald brand layer",css)
        final_brand = css.split("Final RETALLY forest/emerald brand layer", 1)[1]
        self.assertIn("--navy:#062c26;",final_brand)
        self.assertIn(".section-cobalt{background:#105039}",final_brand)
        self.assertIn("rgba(2,34,29,.97)",final_brand)
        self.assertIn(".sample-report .document-hero{",final_brand)
        self.assertNotIn("--navy:#0e1e29;",final_brand)
        self.assertIn("font-family:Instrument,Georgia,serif;",css)
        self.assertIn("font-style:italic;",css)
        self.assertIn(".home-simple .mobile-cta{display:none!important}",css)

    def test_site_hero_and_contact_workflow_unchanged(self):
        page=(SITE / "index.html").read_text(encoding="utf-8")
        script=(SITE / "site.js").read_text(encoding="utf-8")
        self.assertIn("We find freight billing errors, document the evidence, and help recover overpayments.",page)
        self.assertIn('id="auditForm"',page)
        self.assertIn("mailto:",script)
        self.assertIn('id="fee-calculator"',page)

    def test_signature_uses_company_domain_and_no_fabricated_credentials(self):
        html=(BRAND / "RETALLY_EMAIL_SIGNATURE.html").read_text(encoding="utf-8")
        self.assertIn('mailto:jay@retallyrecovery.com',html)
        self.assertIn("https://www.retallyrecovery.com/",html)
        self.assertIn("RETALLY",html)
        self.assertNotIn("jayp19386@",html)
        self.assertNotIn("guaranteed",html.lower())
        self.assertNotIn("certified",html.lower())

    def test_report_preserves_settlement_statuses(self):
        report=(BRAND / "RETALLY_AUDIT_REPORT_TEMPLATE.md").read_text(encoding="utf-8")
        for state in ("Potential issue","Supported finding","Authorized claim","Received funds"):
            self.assertIn(state,report)
        self.assertIn("fictional",report.lower())

if __name__=="__main__":
    unittest.main()
