"""Publication checks for the two independent static company sites."""
from __future__ import annotations

import importlib.util
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
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href"))
        for name, value in attrs:
            if name in ("href", "src"):
                self.references.append(value)
            if name.startswith("on") or name == "style":
                self.unsafe_attributes.append(name)


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
                        self.assertTrue({"script", "form", "iframe", "object"}.isdisjoint(document.tags))
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
                    for rule in ("script-src 'none'", "object-src 'none'", "frame-ancestors 'none'", "form-action 'none'", "nosniff", "max-age=31536000"):
                        self.assertIn(rule, headers)
                    sitemap = ET.parse(output / "sitemap.xml")
                    self.assertEqual(len(profile["pages"]), len(sitemap.getroot()))
                    info = json.loads((output / "build-info.json").read_text())
                    self.assertEqual(company, info["company"])
                    self.assertEqual("local", info["source_commit"])
                    self.assertEqual("local_unattributed", info["source_commit_kind"])

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
