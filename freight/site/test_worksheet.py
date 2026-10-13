"""RETALLY printable social worksheet: approved-source, zero-data-transfer checks."""
from __future__ import annotations

from html.parser import HTMLParser
import re
import tempfile
import unittest
from pathlib import Path

from freight.site import build as builder

SITE = Path(__file__).resolve().parent
PAGE = SITE / "freight-invoice-audit-checklist.html"
SCRIPT = SITE / "worksheet.js"
STYLE = SITE / "foundry.css"


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.scripts = []
        self.forms = []
        self.inputs = []
        self.links = []
        self.buttons = []
    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if fields.get("id"):
            self.ids.append(fields["id"])
        if tag == "script":
            self.scripts.append(fields)
        elif tag == "form":
            self.forms.append(fields)
        elif tag == "input":
            self.inputs.append(fields)
        elif tag == "a":
            self.links.append(fields)
        elif tag == "button":
            self.buttons.append(fields)


class SocialWorksheetTests(unittest.TestCase):
    def test_checklist_is_existing_canonical_route_not_a_new_shadow_page(self):
        p = PAGE.read_text(encoding="utf-8")
        self.assertIn('href="https://p00nsmasher.github.io/github-value-hunt-ledger/freight-invoice-audit-checklist.html"',p)
        self.assertIn('id="worksheet"',p)
        self.assertIn('href="#worksheet"',p)
        self.assertIn('<title>Printable Freight Invoice Audit Checklist',p)

    def test_local_script_only_and_no_new_data_upload_form(self):
        p=PAGE.read_text(encoding="utf-8")
        a=p.index('<section id="worksheet"')
        b=p.index('<section id="modes"',a)
        target=p[a:b]
        self.assertNotIn("<form",target)
        self.assertNotIn("action=",target)
        self.assertNotIn('data-track=',target)
        self.assertNotIn('<script',target)
        parsed=Markup()
        parsed.feed(target)
        self.assertFalse(parsed.forms)
        self.assertEqual(len(parsed.buttons),5)
        self.assertTrue(all(button.get("type")=="button" for button in parsed.buttons))
        for name in ("ws-billed","ws-expected","ws-credits"):
            matching=[x for x in parsed.inputs if x.get("id")==name]
            self.assertEqual(len(matching),1,name)
            self.assertEqual(matching[0].get("autocomplete"),"off")
            self.assertEqual(matching[0].get("inputmode"),"decimal")
        self.assertNotIn('type="file"',target.lower())

    def test_form_control_ids_are_unique_and_outputs_have_labels(self):
        p=PAGE.read_text(encoding="utf-8")
        parser=Markup();parser.feed(p)
        self.assertEqual(len(parser.ids),len(set(parser.ids)))
        for uid in ("ws-unresolved","ws-difference","ws-credit-applied",
                    "ws-error","ws-status","ws-print","ws-copy","ws-share","ws-share-status","ws-clear","ws-sample"):
            self.assertEqual(parser.ids.count(uid),1)
        self.assertIn('role="status"',p)
        self.assertIn('role="alert"',p)
        self.assertIn('aria-live="polite"',p)
        self.assertIn('aria-labelledby="ws-title"',p)

    def test_no_false_money_recovered_or_client_data(self):
        p=PAGE.read_text(encoding="utf-8")
        start=p.index('<section id="worksheet"')
        end=p.index('<section id="modes"',start)
        widget=p[start:end].lower()
        self.assertIn("neither a validated overcharge",widget)
        self.assertIn("does not save, transmit or share the entered amounts",widget)
        self.assertIn("no uploads",widget)
        self.assertIn("customer authorization",widget)
        self.assertNotIn("we recovered $",widget)
        self.assertNotIn("guaranteed refund",widget)

    def test_all_fifteen_evidence_checks_are_printable_and_accessible(self):
        p=PAGE.read_text(encoding="utf-8")
        start=p.index('class="worksheet-checklist"')
        stop=p.index('class="worksheet-evidence"',start)
        checklist=p[start:stop]
        self.assertEqual(checklist.count('<input type="checkbox">'),15)
        self.assertEqual(checklist.count('</label>'),15)
        self.assertIn("credits",checklist)
        self.assertIn("Reversals",checklist)

    def test_source_policy_blocks_inline_upload_or_untrusted_code(self):
        p=PAGE.read_text(encoding="utf-8")
        js=SCRIPT.read_text(encoding="utf-8")
        self.assertIn('<script src="worksheet.js?v=local-worksheet-20261013" defer></script>',p)
        self.assertIn('form-action \'none\'',p)
        self.assertIn('connect-src \'none\'',p)
        self.assertIn("local-only-no-storage-or-upload",js)
        self.assertNotIn("fetch(",js)
        self.assertNotIn("XMLHttpRequest(",js)
        self.assertNotIn("sendBeacon(",js)
        self.assertNotIn("localStorage.setItem(",js)
        self.assertNotIn("dataLayer.push(",js)
        self.assertNotIn("window.open(",js)

    def test_style_is_scoped_and_print_does_not_affect_rest_of_site(self):
        css=STYLE.read_text(encoding="utf-8")
        self.assertIn(".worksheet-builder .worksheet-card",css)
        self.assertIn("@media(max-width:570px)",css)
        self.assertIn("@media print",css)
        self.assertIn("body.worksheet-print-mode",css)
        self.assertIn(".worksheet-head strong{color:#111!important}",css)
        self.assertIn("body.worksheet-print-mode .skip,",css)
        self.assertIn(".worksheet-checklist label:has(input:checked)::before",css)
        self.assertIn("content:\"✓\"",css)
        self.assertIn(".worksheet-checklist",css)
        self.assertIn(".worksheet-stat-focus",css)
        self.assertNotIn("body:not(.worksheet-print-mode)",css)

    def test_public_build_produces_exact_local_js_and_one_worksheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=builder.build(Path(tmp)/"public","sales@freightfixture.com",True)
            html=(dest/"freight-invoice-audit-checklist.html").read_text(encoding="utf-8")
            self.assertIn('https://p00nsmasher.github.io/github-value-hunt-ledger/',html)
            self.assertIn('id="invoiceWorksheet"',html)
            self.assertEqual(html.count('id="worksheet"'),1)
            self.assertEqual((dest/"worksheet.js").read_bytes(),SCRIPT.read_bytes())
            self.assertIn("worksheet.js",builder.PUBLIC_FILES)
            self.assertIn("worksheet.js",builder.TEXT_SOURCE_FILES)
            self.assertIn(".worksheet-builder .worksheet-card",(dest/"foundry.css").read_text())
            # Distinctly no new public endpoint, uploader, or hidden inquiry.
            self.assertFalse((dest/"api"/"worksheet").exists())


if __name__=="__main__":
    unittest.main()
