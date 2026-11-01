"""Publication checks for the two independent static company sites."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

SPEC = importlib.util.spec_from_file_location("company_site_builder", Path(__file__).with_name("build.py"))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.references = []
        self.ids = set()
        self.tags = []
        self.canonicals = []
        self.unsafe_attributes = []
        self.elements = []
        self.texts = []
        self.parents = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        values = dict(attrs)
        self.elements.append((tag, values, tuple(self.parents)))
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href"))
        for name, value in attrs:
            if name in ("href", "src"):
                self.references.append(value)
            if name.startswith("on") or name == "style":
                self.unsafe_attributes.append(name)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.parents.append((tag, values))

    def handle_endtag(self, tag):
        for index in range(len(self.parents) - 1, -1, -1):
            if self.parents[index][0] == tag:
                del self.parents[index:]
                break

    def handle_data(self, text):
        self.texts.append((text, tuple(self.parents)))


class PublicationTests(unittest.TestCase):
    def test_builds_resolve_local_links_and_publish_only_allowed_files(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            for company, profile in builder.PROFILES.items():
                with self.subTest(company=company):
                    output = builder.build(company, Path(temporary) / company)
                    expected = set(profile["files"]) | set(profile["assets"]) | set(builder.GENERATED_FILES)
                    actual = {item.relative_to(output).as_posix() for item in output.rglob("*") if item.is_file()}
                    self.assertEqual(expected, actual)
                    self.assertFalse(any("functions" in item or item.endswith(".py") or "_worker" in item for item in actual))
                    documents = {item.relative_to(output).as_posix(): Document(item.read_text()) for item in output.rglob("*.html")}
                    for page, document in documents.items():
                        html = (output / page).read_text()
                        self.assertNotIn("{{", html)
                        self.assertFalse(document.unsafe_attributes)
                        self.assertTrue({"iframe", "object"}.isdisjoint(document.tags))
                        scripts = [attrs for tag, attrs, _ in document.elements if tag == "script"]
                        data_scripts = [a for a in scripts if a.get("type") == "application/ld+json" and "src" not in a]
                        runtime_scripts = [a for a in scripts if a not in data_scripts]
                        if company == "group" and page == "index.html":
                            self.assertEqual(1, document.tags.count("form"))
                            self.assertEqual(1, len(data_scripts))
                            self.assertEqual(1, len(runtime_scripts))
                            self.assertTrue(runtime_scripts[0]["src"].startswith("/enquiry.js?v="))
                        elif company == "recoveryworks" and page == "index.html":
                            self.assertEqual(1, len(data_scripts))
                            self.assertFalse(runtime_scripts)
                            self.assertNotIn("form", document.tags)
                        else:
                            self.assertFalse(scripts)
                            self.assertNotIn("form", document.tags)
                        for reference in document.references:
                            url = urlsplit(reference)
                            self.assertNotEqual("javascript", url.scheme)
                            if url.scheme or url.netloc:
                                continue
                            route = unquote(url.path)
                            if not route:
                                target = page
                            else:
                                self.assertTrue(route.startswith("/"), reference)
                                target = route.lstrip("/")
                                if route.endswith("/"):
                                    target += "index.html"
                            self.assertTrue((output / target).is_file(), (company, page, reference))
                            if url.fragment:
                                self.assertIn(unquote(url.fragment), documents[target].ids, (page, reference))
                        if "mailto:" in html:
                            self.assertIn("<!--email_off-->", html)
                            self.assertIn("<!--/email_off-->", html)
                    for path in profile["pages"]:
                        expected_url = builder.DEFAULT_URLS[profile["url_key"]] + path.removesuffix("index.html")
                        self.assertEqual([expected_url], documents[path].canonicals)
                    css = (output / "site.css").read_text()
                    for asset in re.findall(r'url\([\"\']?([^\)\"\']+)', css):
                        self.assertTrue(asset.startswith("/"))
                        self.assertTrue((output / asset.lstrip("/")).is_file(), asset)
                    headers = (output / "_headers").read_text()
                    for rule in ("object-src 'none'", "frame-ancestors 'none'", "form-action 'none'", "nosniff", "max-age=31536000"):
                        self.assertIn(rule, headers)
                    if company == "recoveryworks":
                        self.assertIn("script-src 'none'", headers)
                        self.assertIn("connect-src 'none'", headers)
                        self.assertFalse(any(name.endswith(".js") for name in actual))
                    else:
                        self.assertIn("script-src 'self' https://challenges.cloudflare.com;", headers)
                        self.assertIn("frame-src https://challenges.cloudflare.com;", headers)
                        self.assertIn("connect-src 'self' https://www.retallyrecovery.com https://challenges.cloudflare.com;", headers)
                        self.assertNotIn("'unsafe-inline'", headers)
                        self.assertNotIn("'unsafe-eval'", headers)
                    sitemap = ET.parse(output / "sitemap.xml")
                    self.assertEqual(len(profile["pages"]), len(sitemap.getroot()))
                    info = json.loads((output / "build-info.json").read_text())
                    self.assertEqual(company, info["company"])
                    self.assertEqual("local", info["source_commit"])
                    self.assertEqual("local_unattributed", info["source_commit_kind"])

    def test_group_form_preserves_the_labelled_private_receipt_contract(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            output = builder.build("group", Path(temporary) / "group")
            html = (output / "index.html").read_text()
            document = Document(html)
            by_id = {attrs["id"]: attrs for _, attrs, _ in document.elements if "id" in attrs}
            forms = [attrs for tag, attrs, _ in document.elements if tag == "form"]
            self.assertEqual(1, len(forms))
            self.assertEqual("group-enquiry", forms[0]["id"])
            self.assertEqual("post", forms[0]["method"])
            self.assertNotIn("action", forms[0])
            self.assertIn("hidden", forms[0])
            within = lambda parents: any(attrs.get("id") == "group-enquiry" for _, attrs in parents)
            controls = [(tag, attrs) for tag, attrs, parents in document.elements
                        if tag in {"input", "select", "textarea"} and within(parents)]
            for _, attrs in controls:
                self.assertNotEqual("file", attrs.get("type"))
                self.assertIn("id", attrs)
                labelled = attrs.get("aria-label") or any(text.strip() and any(
                    tag == "label" and label.get("for") == attrs["id"] for tag, label in parents
                ) for text, parents in document.texts)
                self.assertTrue(labelled, attrs)
            options = {}
            for text, parents in document.texts:
                option = next((attrs for tag, attrs in parents if tag == "option"), None)
                if option is not None and text.strip():
                    options[option["value"]] = text.strip()
            self.assertEqual({
                "general": "Help me find the right business",
                "recovery": "RETALLY Freight Recovery",
                "recoveryworks": "RETALLY RecoveryWorks",
                "permitplate": "PermitPlate",
                "capturebrief": "CaptureBrief",
            }, options)
            for name, limit in (("enquiry-name", "100"), ("enquiry-email", "160"),
                                ("enquiry-company", "140"), ("enquiry-message", "800")):
                self.assertEqual(limit, by_id[name]["maxlength"])
            self.assertEqual("email", by_id["enquiry-email"]["type"])
            self.assertNotIn("required", by_id["enquiry-company"])
            self.assertIn("required", by_id["enquiry-consent"])
            self.assertEqual("checkbox", by_id["enquiry-consent"]["type"])
            self.assertNotIn("checked", by_id["enquiry-consent"])
            self.assertIn("disabled", by_id["send-enquiry"])
            self.assertEqual("status", by_id["enquiry-status"]["role"])
            self.assertEqual("polite", by_id["enquiry-status"]["aria-live"])
            status_copy = " ".join(text.strip() for text, parents in document.texts if text.strip() and any(
                attrs.get("id") == "enquiry-status" for _, attrs in parents
            ))
            self.assertEqual(
                "Complete the security verification to enable secure sending. Nothing has been sent.",
                status_copy,
            )
            self.assertEqual("group", by_id["enquiry-turnstile"]["role"])
            self.assertEqual("Security verification", by_id["enquiry-turnstile"]["aria-label"])
            self.assertEqual("mailto", urlsplit(by_id["enquiry-draft"]["href"]).scheme)
            self.assertEqual("jay@retallyrecovery.com", urlsplit(by_id["enquiry-draft"]["href"]).path)
            self.assertEqual("button", by_id["copy-enquiry"]["type"])
            self.assertIn("readonly", by_id["enquiry-copy-text"])
            self.assertIn("hidden", by_id["enquiry-copy-text"])
            form_copy = " ".join(text for text, parents in document.texts if within(parents)).lower()
            for text in ("draft", "nothing has been sent", "privately store", "not confirm email delivery"):
                self.assertIn(text, form_copy)
            self.assertIn("https://www.retallyrecovery.com/#start-audit", document.references)
            self.assertNotIn("auditForm", document.ids)
            scripts = [attrs for tag, attrs, _ in document.elements if tag == "script" and attrs.get("src")]
            script = (output / "enquiry.js").read_text()
            revision = hashlib.sha256((output / "enquiry.js").read_bytes()).hexdigest()[:16]
            self.assertEqual(["/enquiry.js?v=" + revision], [attrs["src"] for attrs in scripts])
            self.assertTrue(all("defer" in attrs for attrs in scripts))
            self.assertIn('"https://www.retallyrecovery.com/api/group-inquiry"', script)
            self.assertIn('credentials: "omit"', script)
            self.assertIn('action: "retally_group"', script)
            self.assertIn('size: "compact"', script)
            self.assertIn('response.status !== 202', script)
            self.assertIn('receipt.received !== true', script)
            self.assertNotRegex(script, r"\b(?:localStorage|sessionStorage|sendBeacon|WebSocket)\b")
            privacy = (output / "privacy/index.html").read_text()
            for text in ("Cloudflare Turnstile", "Resend", "restricted database", "saved reference confirms storage",
                         "90 days", "Deletion is not automatic", "Copying does not send"):
                self.assertIn(text, privacy)

    def test_fingerprint_uses_cloudflare_revision_and_canonical_override(self):
        cf_sha, github_sha = "a" * 40, "b" * 40
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"CF_PAGES_COMMIT_SHA": cf_sha, "GITHUB_SHA": github_sha}, clear=True):
            output = builder.build("group", Path(temporary) / "group", "https://preview.example.com")
            info = json.loads((output / "build-info.json").read_text())
            self.assertEqual(cf_sha, info["source_commit"])
            self.assertEqual("git_commit", info["source_commit_kind"])
            self.assertEqual("https://preview.example.com/", info["canonical_url"])
            self.assertEqual(["https://preview.example.com/"], Document((output / "index.html").read_text()).canonicals)

    def test_refuses_to_overwrite_existing_output_or_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            marker = output / "existing-file.txt"
            marker.write_text("keep this file")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                builder.build("group", output)
            self.assertEqual("keep this file", marker.read_text())
        for name in builder.PROFILES:
            with self.assertRaisesRegex(ValueError, "outside company source"):
                builder.build("group", builder.SOURCE_ROOT / name)

    def test_rejects_unverifiable_revision_and_unsafe_public_destinations(self):
        for value in ("http://example.com", "https://user:pass@example.com", "https://example.com/?token=x", "https://example.com/#section"):
            with self.subTest(url=value), self.assertRaises(ValueError):
                builder._public_url(value)
        with patch.dict(os.environ, {"CF_PAGES_COMMIT_SHA": "not-a-revision"}, clear=True):
            with self.assertRaises(ValueError):
                builder._source_commit()


if __name__ == "__main__":
    unittest.main()
