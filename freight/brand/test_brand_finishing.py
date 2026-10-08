"""Regression gates for the RETALLY visual-finishing PR (stdlib only)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BRAND = ROOT / "brand"

class RetallyFinishingTests(unittest.TestCase):
    def test_restrained_colors_preserve_typography_and_mobile_guard(self):
        css=(SITE / "foundry.css").read_text(encoding="utf-8")
        self.assertIn("RETALLY restrained-surface pass",css)
        self.assertIn("--navy:#0e1e29;",css)
        self.assertIn(".section-cobalt { background-color:#183940; }",css)
        self.assertIn("font-family:Instrument,Georgia,serif;",css)
        self.assertIn("font-style:italic;",css)
        self.assertIn(".home-simple .mobile-cta { display:none!important; }",css)

    def test_site_hero_and_contact_workflow_unchanged(self):
        page=(SITE / "index.html").read_text(encoding="utf-8")
        script=(SITE / "site.js").read_text(encoding="utf-8")
        self.assertIn("We find freight billing errors, document the evidence, and help recover overpayments.",page)
        self.assertIn('id="auditForm"',page)
        self.assertIn("mailto:",script)
        self.assertIn('id="fee-calculator"',page)

    def test_signature_cannot_claim_unverified_mailbox(self):
        html=(BRAND / "RETALLY_EMAIL_SIGNATURE.html").read_text(encoding="utf-8")
        self.assertIn("[Verified company email]",html)
        self.assertIn("[Verified sender name]",html)
        self.assertNotIn("mailto:sales@retallyrecovery.com",html)

    def test_report_preserves_settlement_statuses(self):
        report=(BRAND / "RETALLY_AUDIT_REPORT_TEMPLATE.md").read_text(encoding="utf-8")
        for state in ("Potential issue","Supported finding","Authorized claim","Received funds"):
            self.assertIn(state,report)
        self.assertIn("fictional",report.lower())

if __name__=="__main__":
    unittest.main()
