"""Publication-boundary checks. Fixture contacts are never deployed."""

import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from freight.synthetic_pilot_bundle import verify_synthetic_pilot_bundle

spec = importlib.util.spec_from_file_location(
    "marketing_build", Path(__file__).with_name("build.py")
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def build(output, email="sales@freightfixture.com", contact_verified=True, rate="0.30"):
    return builder.build(output, email, contact_verified, rate)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.links = []
        self.ids = []
        self.forms = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img":
            self.images.append(attributes)
        if tag == "a":
            self.links.append(attributes.get("href", ""))
        if "id" in attributes:
            self.ids.append(attributes["id"])
        if tag == "form":
            self.forms.append(attributes)


class PublicBuildTests(unittest.TestCase):
    def test_sample_report_and_trust_disclosures_are_mobile_safe_and_current(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            report = (output / "recovery-status-example.html").read_text()
            trust = (output / "trust.html").read_text()
            styles = (output / "foundry.css").read_text()

            # Preserve the already-approved sample and accounting states.
            self.assertIn("Sample Recovery Report", report)
            self.assertIn("Northstar Industrial Supply", report)
            self.assertIn("Sample Population</span>", report)
            self.assertIn("2026-01-01 through 2026-03-31</span>", report)
            self.assertIn('class="meta report-population"', report)
            self.assertIn(".sample-report .report-population span{white-space:nowrap}", styles)
            self.assertIn("$13,450.00", report)
            self.assertIn("$11,800.00", report)
            # This is a synthetic aggregate, not an itemized source ledger.
            # Never silently attribute the unexplained fee-eligibility gap.
            self.assertIn("$1,650.00 difference", report)
            self.assertIn("unallocated and not independently verified", report)
            self.assertIn("no fee is established by this example", report)

            # Do not describe the new branded-domain online intake as email-only.
            self.assertIn("Cloudflare Pages at www.retallyrecovery.com", trust)
            self.assertIn("secure inquiry endpoint and required anti-abuse check", trust)
            self.assertIn("opening a draft does not send an inquiry", trust)
            self.assertIn("GitHub Pages edition remains publicly accessible", trust)
            self.assertNotIn("The marketing site is hosted through GitHub Pages.", trust)

    def test_google_search_console_verification_file_is_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            verification = (output / "google738a4fc9a0997cd0.html").read_text()
            self.assertEqual(
                verification,
                "google-site-verification: google738a4fc9a0997cd0.html\n",
            )

    def test_contact_must_be_present_and_verified(self):
        for email, verified in [
            ("", True),
            ("sales@freightfixture.com", False),
            ("sales@example.com", True),
            ("not-an-email", True),
        ]:
            with self.subTest(email=email, verified=verified):
                with tempfile.TemporaryDirectory() as temporary, self.assertRaises(ValueError):
                    build(Path(temporary) / "public", email=email, contact_verified=verified)

    def test_contingency_rate_is_validated_and_configurable(self):
        for invalid in ("", "0", "1", "-0.1", "nan"):
            with self.subTest(rate=invalid):
                with tempfile.TemporaryDirectory() as temporary, self.assertRaises(ValueError):
                    build(Path(temporary) / "public", rate=invalid)
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public", rate="0.325")
            config = (output / "commercial-config.js").read_text()
            self.assertIn('contingencyRecoveryRate: "0.325"', config)
            self.assertIn('contingencyRecoveryRateLabel: "32.5%"', config)

    def test_private_repository_cannot_be_the_output(self):
        for output in (
            builder.REPOSITORY,
            builder.REPOSITORY / "dist",
            builder.REPOSITORY.parent,
        ):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build(output)

    def test_output_contains_only_allowlisted_public_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            files = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            self.assertEqual(set(builder.PUBLIC_FILES), files)
            for name in builder.BINARY_SOURCE_FILES:
                self.assertEqual((builder.SOURCE / name).read_bytes(), (output / name).read_bytes())

    def test_configured_rate_is_visible_without_javascript(self):
        for rate, expected in (("0.30", "30%"), ("0.325", "32.5%")):
            with self.subTest(rate=rate), tempfile.TemporaryDirectory() as temporary:
                output = build(Path(temporary) / "public", rate=rate)
                homepage = (output / "index.html").read_text()
                terms = (output / "engagement-framework.html").read_text()
                self.assertIn(f"<strong data-rate-label>{expected}</strong>", homepage)
                self.assertIn(f"<b data-rate-label>{expected}</b>", terms)
                self.assertNotIn("Rate confirmed before engagement", homepage)

    def test_free_audit_is_bounded_without_promising_unapproved_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            page = (output / "index.html").read_text()
            self.assertIn("up to 20 eligible invoices after a fit and capacity check", page)
            self.assertIn("our capacity before requesting files", page)
            self.assertIn("approved secure intake route", page)
            self.assertNotIn("24-hour guaranteed review", page)

    def test_email_fallback_preserves_direct_user_gesture_and_manual_address(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            page = (output / "index.html").read_text()
            script = (output / "site.js").read_text()
            self.assertIn('id="sendAuditRequest"', page)
            self.assertIn('id="copyAuditSummary"', page)
            self.assertIn('id="auditRecipientAddress"', page)
            self.assertIn('recipient.textContent = contactEmail', script)
            self.assertIn('window.location.href = sendLink.href;', script)
            self.assertNotIn('window.setTimeout(() => { window.location.href = sendLink.href; }, 80)', script)
            self.assertIn("Review it, then press Send.", page)

    def test_public_pages_express_the_free_audit_contingency_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            page = (output / "index.html").read_text()
            config = (output / "commercial-config.js").read_text()

            self.assertIn('<span class="hero-phrase">Find it.</span> <span class="hero-phrase">Prove it.</span> <em class="hero-phrase">Recover it.</em>', page)
            self.assertIn("Recovery Evidence Pack", page)
            self.assertIn('href="second-look-freight-audit.html"', page)
            self.assertIn('href="freight-recovery-evidence-standard.html"', page)
            self.assertNotIn("Real case studies will appear when they are real.", page)
            self.assertIn("Start Free Recovery Audit", page)
            self.assertIn("<strong>$0</strong> upfront audit fee", page)
            self.assertIn("no recovery fee", page.lower())
            self.assertIn('id="auditForm"', page)
            self.assertIn('data-form-step="1"', page)
            self.assertNotIn('data-form-step="2"', page)
            self.assertNotIn('data-form-step="3"', page)
            self.assertIn('class="qualification-details"', page)
            self.assertIn("Open My Free Audit Request", page)
            self.assertIn("approved secure intake route", page)
            self.assertIn("Fixed-Fee Forensic Audit", page)
            self.assertIn("Available", page)
            self.assertIn("Potential recovery", page)
            self.assertIn("Approved claim value", page)
            self.assertIn("Actual recovered funds", page)
            self.assertIn("<strong data-rate-label>30%</strong>", page)
            self.assertIn('contingencyRecoveryRate: "0.3"', config)
            self.assertIn('contingencyRecoveryRateLabel: "30%"', config)
            self.assertIn('itemscope itemtype="https://schema.org/WebPage"', page)
            self.assertIn('itemprop="mainEntity" itemscope itemtype="https://schema.org/Service"', page)
            self.assertIn('itemprop="offers" itemscope itemtype="https://schema.org/Offer"', page)
            self.assertIn('itemprop="priceCurrency" content="USD"', page)
            self.assertIn('itemprop="price" content="0"', page)
            self.assertIn('name="twitter:title"', page)
            self.assertIn('name="twitter:description"', page)
            self.assertIn('name="twitter:image"', page)
            self.assertIn('id="actualRecoveredDisplay">$100,000</dd>', page)
            self.assertIn('content="free-audit-contingency-v5"', page)
            self.assertIn('href="freight-audit-services.html"', page)
            self.assertIn('href="freight-invoice-audit.html"', page)
            self.assertIn('href="freight-overcharge-recovery.html"', page)
            self.assertIn('href="accessorial-charge-audit.html"', page)
            self.assertIn('href="freight-audit-companies.html"', page)

            forbidden = (
                "$5,000",
                "$15,000",
                "Start checkout",
                "See prices & checkout",
                "Secure checkout is open",
                "buy.stripe.com",
                "Customer keeps 80%",
                "our recovery fee 20%",
            )
            public_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in output.rglob("*")
                if path.is_file() and path.suffix.lower() in {".html", ".js", ".css", ".txt", ".xml"}
            )
            for phrase in forbidden:
                with self.subTest(phrase=phrase):
                    self.assertNotIn(phrase, public_text)


    def test_business_structured_data_represents_a_national_b2b_service_not_a_walk_in_shop(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            index = (output / "index.html").read_text()
            about = (output / "about.html").read_text()
            self.assertEqual(index.count('<script type="application/ld+json">'), 1)
            raw_json = index.split('<script type="application/ld+json">', 1)[1].split("</script>", 1)[0]
            graph = json.loads(raw_json)["@graph"]
            by_type = {node["@type"]: node for node in graph}
            org = by_type["Organization"]
            service = by_type["Service"]
            self.assertEqual(org["name"], "RETALLY")
            self.assertEqual(
                org["logo"]["url"],
                "https://p00nsmasher.github.io/github-value-hunt-ledger/assets/brand/retally-emblem.webp",
            )
            self.assertIn("Freight Invoice Audit &amp; Overcharge Recovery | RETALLY", index)
            self.assertIn("Freight invoice audit and overcharge recovery for U.S. businesses.", index)
            self.assertNotIn("address", org)
            self.assertEqual(service["provider"]["@id"], org["@id"])
            self.assertEqual(service["areaServed"]["name"], "United States")
            self.assertNotIn("LocalBusiness", raw_json)
            self.assertIn("Start with a remote qualification request", about)

    def test_contact_is_injected_without_enabling_file_submission(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            index = (output / "index.html").read_text()
            privacy = (output / "privacy.html").read_text()
            engagement = (output / "engagement-framework.html").read_text()
            organic = [
                (output / name).read_text()
                for name in (
                    "freight-audit-services.html",
                    "freight-invoice-audit.html",
                    "freight-overcharge-recovery.html",
                    "accessorial-charge-audit.html",
                )
            ]
            for page in (index, privacy, engagement, *organic):
                self.assertIn('content="sales@freightfixture.com"', page)
                self.assertNotIn(builder.CONTACT_META, page)
            self.assertIn('href="mailto:sales@freightfixture.com', index)
            self.assertIn('href="mailto:sales@freightfixture.com', privacy)
            self.assertNotIn(">sales@freightfixture.com</a>", index)
            self.assertNotIn('type="file"', index.lower())
            self.assertIn("form-action 'none'", index)
            self.assertIn("connect-src https://www.bubblav.com", index)
            self.assertIn("form-action 'none'", index)
            self.assertNotIn("connect-src 'self'", index)

    def test_pages_have_unique_ids_and_resolvable_local_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            for name in (
                item for item in builder.TEXT_SOURCE_FILES if item.endswith(".html")
            ):
                parser = PageParser()
                parser.feed((output / name).read_text())
                self.assertEqual(len(parser.ids), len(set(parser.ids)), name)
                self.assertTrue(all("alt" in image for image in parser.images), name)
                anchors = set(parser.ids)
                for href in parser.links:
                    if not href or href.startswith(("mailto:", "https://")):
                        continue
                    if href == "#contact-pending":
                        continue
                    clean = href.split("?", 1)[0]
                    if clean.startswith("#"):
                        self.assertIn(clean[1:], anchors, f"{name}: {href}")
                    else:
                        file_part, _, fragment = clean.partition("#")
                        target = (output / file_part).resolve() if file_part else (output / name).resolve()
                        self.assertTrue(target.exists(), f"{name}: {href}")
                        if fragment and target.suffix == ".html":
                            target_parser = PageParser()
                            target_parser.feed(target.read_text())
                            self.assertIn(fragment, target_parser.ids, f"{name}: {href}")

    def test_form_and_analytics_scripts_are_local_and_truthful(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            script = (output / "site.js").read_text()
            page = (output / "index.html").read_text()
            self.assertIn('site.css?v=free-audit-contingency-v5', page)
            self.assertIn('commercial-config.js?v=free-audit-contingency-v5', page)
            self.assertIn('site.js?v=free-audit-contingency-v5', page)
            self.assertIn('id="actualRecovery" type="number" min="0" max="1000000000" step="1000" value="100000"', page)
            self.assertIn('<dd id="actualRecoveredDisplay">$100,000</dd>', page)
            self.assertNotIn('value="50000"', page)
            self.assertIn("freight_audit_form_started", script)
            self.assertIn("freight_audit_form_completed", script)
            self.assertIn("freight_data_submitted", script)
            self.assertIn("freight_qualified_lead", script)
            self.assertIn("freight_audit_completed", script)
            self.assertIn("freight_recovery_engagement_accepted", script)
            self.assertIn("freight_actual_recovery_recorded", script)
            self.assertIn("actual * contingencyRate", script)
            self.assertIn("sendLink.href = `mailto:${contactEmail}", script)
            self.assertIn("window.location.href = sendLink.href", script)
            self.assertIn("new URLSearchParams(window.location.search)", script)
            self.assertIn('utm_source: cleanCampaignValue("utm_source")', script)
            self.assertIn('utm_campaign: cleanCampaignValue("utm_campaign")', script)
            self.assertIn("Acquisition source:", script)
            self.assertIn("Review it, then press Send.", page)
            stylesheet = (output / "site.css").read_text()
            self.assertIn(".output-copy{min-width:0}", stylesheet)
            self.assertIn(".security-layout>*{min-width:0}", stylesheet)
            self.assertIn(".security-image{width:100%;margin:0;position:relative}", stylesheet)
            self.assertIn(".qualification-details{", stylesheet)
            self.assertIn(".navlinks{position:absolute;left:0;right:0;top:100%", stylesheet)
            # The same JS is shipped to legacy GitHub Pages, whose strict CSP
            # denies connections; network use is gated to the RETALLY host.
            self.assertIn('["www.retallyrecovery.com", "retallyrecovery.com"].includes(window.location.hostname)', script)
            self.assertIn('fetch("/api/inquiry"', script)
            for network_or_storage_api in (
                "XMLHttpRequest",
                "sendBeacon",
                "WebSocket",
                "localStorage",
                "sessionStorage",
            ):
                self.assertNotIn(network_or_storage_api, script)

    def test_controlled_demo_is_current_and_clearly_synthetic(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            page = (output / "index.html").read_text()
            self.assertNotIn(builder.DEMO_MARKER, page)
            self.assertIn('href="synthetic-pilot-demo.zip"', page)
            self.assertIn("Sample data only", page)
            demo = output / builder.DEMO_FILE
            receipt = verify_synthetic_pilot_bundle(demo)
            self.assertEqual(11, receipt["entry_count"])
            self.assertEqual(
                hashlib.sha256(demo.read_bytes()).hexdigest(), receipt["bundle_sha256"]
            )
            self.assertNotIn(receipt["bundle_sha256"], page)
            self.assertNotIn("SHA-256", page)
            self.assertIn("Download a sample audit walkthrough", page)

    def test_public_copy_and_private_address_are_safe(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            for name in builder.TEXT_SOURCE_FILES:
                page = (output / name).read_text(encoding="utf-8")
                self.assertNotIn("yorktowne", page.lower(), name)
                self.assertNotIn("17901", page, name)
                self.assertNotIn("jayp19386@", page.lower(), name)
            index = (output / "index.html").read_text()
            report = (output / "recovery-status-example.html").read_text()
            example = (output / "freight-audit-example.html").read_text()
            self.assertIn("Northstar Industrial Supply", report)
            self.assertIn("Sample Population</span><span>2026-01-01 through 2026-03-31</span>", report)
            self.assertIn('class="button button-light report-back"', report)
            self.assertNotIn('class="report-notice"', report)
            self.assertIn("This scenario uses sample data only.", example)
            self.assertIn("sample carrier Blue River Freight", example)
            self.assertIn('content="jay@retallyrecovery.com"', index)
            self.assertIn("Sample data", index)

    def test_fonts_and_images_retain_integrity(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            stylesheet = (output / "site.css").read_text()
            self.assertIn("@font-face", stylesheet)
            self.assertNotIn("https://", stylesheet)
            for name in builder.BINARY_SOURCE_FILES:
                payload = (output / name).read_bytes()
                if name.endswith(".webp"):
                    self.assertEqual(b"RIFF", payload[:4])
                    self.assertEqual(b"WEBP", payload[8:12])
                elif name.endswith(".woff2"):
                    self.assertEqual(b"wOF2", payload[:4])
            attribution = json.loads((output / "assets/fonts/ATTRIBUTION.json").read_text())
            copied_fonts = {
                Path(name).name for name in builder.BINARY_SOURCE_FILES if name.endswith(".woff2")
            }
            for item in attribution["assets"]:
                if item["file"] not in copied_fonts:
                    continue
                font = output / "assets/fonts" / item["file"]
                self.assertEqual(item["sha256"], hashlib.sha256(font.read_bytes()).hexdigest())
                self.assertEqual("SIL Open Font License 1.1", item["license"])

    def test_retally_mobile_brand_presentation_does_not_occlude_content(self):
        css = (builder.SOURCE / "foundry.css").read_text(encoding="utf-8")
        page = (builder.SOURCE / "index.html").read_text(encoding="utf-8")
        # Explicit mobile regression guard: the former fixed CTA hid page
        # content and inherited unreadable dark-green-on-dark-green colors.
        self.assertIn(".mobile-cta{display:none!important}", css)
        self.assertIn("body{padding-bottom:0}", css)
        self.assertIn(".hero-phrase{display:inline-block;white-space:nowrap}", css)
        self.assertIn("font-size:clamp(2.1rem,9vw,2.4rem)", css)
        # Retain the approved type assets and primary conversion route.
        self.assertIn('hanken-grotesk-latin.woff2', page)
        self.assertIn('instrument-serif-italic-latin.woff2', page)
        self.assertIn('class="button button-signal" href="#start-audit"', page)
        self.assertIn('foundry.css?v=retally-type-20261008', page)
        # Approved type hierarchy: one italic mint hero phrase, serif accents
        # on dark and light sections, and legible light/dark body colors.
        self.assertIn('<span class="hero-phrase">Prove it.</span> <em class="hero-phrase">Recover it.</em>', page)
        self.assertIn('<h2 id="output-title">See what you <em>get.</em></h2>', page)
        self.assertIn('<h2 id="pricing-title">Simple <em>pricing.</em></h2>', page)
        self.assertIn('.home-simple .hero h1 em.hero-phrase{', css)
        self.assertIn('font-family:Instrument,Georgia,serif;', css)
        self.assertIn('color:#b7f0ce;', css)
        self.assertIn('color:#087a50;', css)
        self.assertIn('color:#f6faf7;', css)
        self.assertIn('color:#40574d', css)

    def test_manual_email_fallback_preserves_mobile_user_gesture(self):
        # The fallback is the production contact path while online D1 intake
        # is disabled. On iOS, a delayed navigation can be gesture-blocked.
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            page = (output / "index.html").read_text(encoding="utf-8")
            script = (output / "site.js").read_text(encoding="utf-8")
            self.assertIn('id="sendAuditRequest"', page)
            self.assertIn('id="copyAuditSummary"', page)
            self.assertIn('sendLink.href = `mailto:${contactEmail}', script)
            self.assertIn('window.location.href = sendLink.href;', script)
            self.assertNotIn(
                'window.setTimeout(() => { window.location.href = sendLink.href; }, 80)',
                script,
            )

    def test_existing_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            marker = output / "keep.txt"
            marker.write_text("unchanged")
            with self.assertRaises(ValueError):
                build(output)
            self.assertEqual(marker.read_text(), "unchanged")
            self.assertEqual(["keep.txt"], [file.name for file in output.iterdir()])


class PublicChatbotTests(unittest.TestCase):
    """Prevent chat embedding from breaking the audited publication boundary."""

    def test_widget_is_present_once_on_public_marketing_pages(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            expected_script = (
                '<script src="https://www.bubblav.com/widget.js" '
                'data-site-id="b0e3b0a1-8f64-4dcd-ac82-507366428147" defer></script>'
            )
            for name in builder.PUBLIC_CONTACT_PAGES:
                with self.subTest(page=name):
                    html = (output / name).read_text()
                    self.assertEqual(html.count(expected_script), 1)
                    self.assertIn("script-src 'self' https://www.bubblav.com;", html)
                    self.assertIn("connect-src https://www.bubblav.com", html)
                    self.assertIn("frame-src https://www.bubblav.com", html)
            for name in ("404.html", "recovery-status-example.html"):
                self.assertNotIn(expected_script, (output / name).read_text())
            self.assertIn("Optional AI chat assistant", (output / "privacy.html").read_text())
            self.assertIn("https://www.bubblav.com", (output / "_headers").read_text())

    def test_glossy_chat_launcher_keeps_native_widget_and_accessibility(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            css = (output / "foundry.css").read_text()
            js = (output / "site.js").read_text()
            for page in builder.PUBLIC_CONTACT_PAGES:
                html = (output / page).read_text()
                with self.subTest(page=page):
                    self.assertEqual(html.count('id="retallyChatLauncher"'), 1)
                    self.assertIn('type="button" aria-label="Open RETALLY AI chat assistant"', html)
                    self.assertIn('aria-haspopup="dialog"', html)
                    self.assertIn('class="retally-chat-orb"', html)
                    self.assertEqual(html.count('data-site-id="b0e3b0a1-8f64-4dcd-ac82-507366428147"'), 1)
                    self.assertLess(html.index('id="retallyChatLauncher"'), html.index('data-site-id="b0e3b0a1-8f64-4dcd-ac82-507366428147"'))
            self.assertIn('window.BubblaV', js)
            self.assertIn('api.open()', js)
            self.assertIn('retally-chat-fallback', js)
            self.assertIn('retally-chat-open', js)
            self.assertIn('window.setInterval(syncRetallyChat, 500)', js)
            self.assertIn('.retally-chat-launcher:focus-visible', css)
            self.assertIn('@media(prefers-reduced-motion:reduce)', css)
            self.assertIn('#bv-chat-frame', css)
            for name in ("recovery-status-example.html", "404.html"):
                self.assertNotIn('id="retallyChatLauncher"', (output / name).read_text())

    def test_cloudflare_turnstile_csp_coexists_with_chatbot(self):
        from freight.site.cloudflare_build import allow_verified_pages_inquiry

        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            allow_verified_pages_inquiry(output)
            for name in ("index.html", "_headers"):
                content = (output / name).read_text()
                self.assertIn("script-src 'self' https://www.bubblav.com https://challenges.cloudflare.com;", content)
                self.assertIn("connect-src 'self' https://www.bubblav.com", content)
                self.assertIn("frame-src https://www.bubblav.com", content)
                self.assertIn("https://challenges.cloudflare.com;", content)
                self.assertNotIn("connect-src 'none'", content)



class SignatureFinishTests(unittest.TestCase):
    """Selective visual tokens without marketing-content or intake changes."""

    def test_white_primary_button_gradient_stops_meet_text_contrast(self):
        # The button's label is white. Check every base and hover stop,
        # rather than assuming a branded green is automatically legible.
        def luminance(hexcolor):
            channels = [int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [n / 12.92 if n <= 0.04045 else ((n + 0.055) / 1.055) ** 2.4
                      for n in channels]
            return sum(a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722)))

        for color in ("#0b8055", "#086f4b", "#07553a",
                      "#0c8758", "#087952", "#064b37"):
            with self.subTest(color=color):
                self.assertGreaterEqual(1.05 / (luminance(color) + 0.05), 4.5)


    def test_premium_surfaces_are_present_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build(Path(temporary) / "public")
            css = (bundle / "foundry.css").read_text(encoding="utf-8")
            home = (bundle / "index.html").read_text(encoding="utf-8")
            report = (bundle / "recovery-status-example.html").read_text(encoding="utf-8")
            self.assertEqual(css.count("RETALLY Signature Finish v1"), 1)
            for selector in (
                ".button-signal,.button-cobalt{",
                ".site-header .navlinks>.button-light{",
                ".home-simple .opportunity-card{",
                ".home-simple .price-card-primary{",
                ".home-simple .price-card-dark{",
                ".home-simple .form-shell{",
                ".home-simple .choice-grid input:checked+span{",
                ".sample-report .report-card.net{",
                "@media(prefers-reduced-motion:reduce){",
            ):
                with self.subTest(selector=selector):
                    self.assertIn(selector, css)
            # The published structure and approved claims remain unchanged.
            self.assertIn('id="auditForm"', home)
            self.assertIn('id="retallyChatLauncher"', home)
            self.assertIn("Sample audit", home)
            self.assertIn("Illustrative only. Not customer results.", home)
            self.assertIn("No recovery, no recovery fee", home)
            self.assertIn("Sample Recovery Report", report)
            self.assertIn("$13,450.00", report)
            self.assertNotIn("backdrop-filter:blur(", css[css.index("RETALLY Signature Finish v1"):])
            self.assertNotIn("@keyframes", css[css.index("RETALLY Signature Finish v1"):])
            self.assertEqual(set(builder.PUBLIC_FILES), {
                p.relative_to(bundle).as_posix() for p in bundle.rglob("*") if p.is_file()
            })


class PremiumFinishV2Tests(unittest.TestCase):
    def test_footer_contact_has_distinct_layout_and_measured_qa(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / "public")
            css = (output / "foundry.css").read_text()
            html = (output / "index.html").read_text()
            visual = Path(__file__).with_name("visual_acceptance.py").read_text()

            self.assertEqual(html.count('data-contact-link href="mailto:'), 1)
            self.assertIn("RETALLY Premium Finish V2: customer contact clarity", css)
            self.assertIn(".home-simple .simple-footer > div:first-child{", css)
            self.assertIn("flex-direction:column;", css[css.index("RETALLY Premium Finish V2:"):])
            self.assertIn("min-height:44px;", css[css.index("RETALLY Premium Finish V2:"):])
            self.assertIn("touchHeightPx", visual)
            self.assertIn("nonOverlapping", visual)
            self.assertIn("footerContact", visual)


if __name__ == "__main__":
    unittest.main()
