"""Offline regression tests for GET-only RETALLY public campaign preflight."""
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from public_asset_preflight import _allowed, _dimensions, inspect, markdown, run, targets


MEDIA = "https://static.metricool.com/planner/202610/7322512-file-fixture.jpeg"
MEDIA2 = "https://static.metricool.com/planner/202610/7322512-file-fixture2.png"
LAND = ("https://www.retallyrecovery.com/freight-audit-methodology"
        "?utm_source=facebook&utm_medium=organic_social"
        "&utm_campaign=retally_oct2026_launch&utm_content=preflight")
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 1080, 1350)
JPEG = (b"\xff\xd8\xff\xc0\x00\x0b\x08" +
        struct.pack(">HH", 1350, 1080) + b"\x01\x01\x11\x00")


def fixture(*, network="facebook", uid="F1", draft=False, media=MEDIA):
    return {
        "uuid": uid, "providers": [{"network": network, "status": "PENDING"}],
        "draft": draft, "autoPublish": not draft,
        "publicationDate": {"dateTime": "2026-10-12T15:00:00",
                            "timezone": "Europe/Madrid"},
        "media": [media], "mediaAltText": ["RETALLY educational campaign graphic"],
        "text": ("Evidence first. " + LAND if network == "facebook"
                 else "Learn more through the link in our bio."),
        network + "Data": {"type": "POST"},
    }


class PublicAssetPreflightTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {"data": [fixture()]}

    def test_default_mode_does_not_call_network(self):
        def forbidden(*args):
            raise AssertionError("offline path attempted public GET")
        report = run(self.snapshot, fetcher=forbidden)
        self.assertEqual(report["mode"], "offline_manifest")
        self.assertEqual(report["counts"]["NOT_CHECKED"], 2)
        self.assertFalse(report["publication_verified"])
        self.assertIn("NOT VERIFIED", markdown(report))

    def test_exact_host_and_scheme_allowlist(self):
        for url in (
            "http://static.metricool.com/planner/x.png",
            "https://static.metricool.com.evil.example/planner/x.png",
            "https://localhost/planner/x.png",
            "https://127.0.0.1/planner/x.png",
            "https://static.metricool.com/private/x.png",
            "https://static.metricool.com/planner/../private.png",
            "https://static.metricool.com/planner/%2e%2e/private.png",
            "https://user:password@static.metricool.com/planner/x.png",
            "https://static.metricool.com:8443/planner/x.png",
            "https://static.metricool.com/planner/x.png?redirect=https://localhost",
        ):
            self.assertFalse(_allowed(url, "image"), url)
        self.assertTrue(_allowed(MEDIA, "image"))

    def test_landing_cannot_redirect_to_another_host_or_skip_tags(self):
        self.assertTrue(_allowed(LAND, "landing"))
        for url in (
            LAND.replace("www.retallyrecovery.com", "evil.retallyrecovery.com"),
            LAND.replace("https", "http", 1),
            LAND.replace("utm_source=facebook", "utm_source=instagram"),
            LAND.replace("&utm_content=preflight", ""),
            LAND + "&utm_campaign=another",
            "https://www.retallyrecovery.com:444/x?utm_source=facebook",
        ):
            self.assertFalse(_allowed(url, "landing"), url)

    def test_shared_media_deduplication_with_two_platforms(self):
        self.snapshot["data"].append(fixture(network="instagram", uid="I1"))
        a = targets(self.snapshot)
        self.assertEqual(len(a), 2)
        image = next(x for x in a if x["kind"] == "image")
        self.assertEqual(image["uuids"], ["F1", "I1"])
        self.assertEqual(image["networks"], ["facebook", "instagram"])

    def test_draft_assets_excluded_until_opt_in(self):
        self.snapshot["data"].append(fixture(uid="D1", network="instagram",
                                             media=MEDIA2, draft=True))
        self.assertEqual(len(targets(self.snapshot)), 2)
        self.assertEqual(len(targets(self.snapshot, include_drafts=True)), 3)
        self.assertFalse(run(self.snapshot, include_drafts=True)["publication_verified"])

    def test_reject_duplicate_uuid_and_missing_image(self):
        self.snapshot["data"].append(fixture(uid="F1", network="instagram"))
        with self.assertRaises(ValueError):
            targets(self.snapshot)
        self.snapshot["data"].pop()
        self.snapshot["data"][0]["mediaAltText"] = []
        with self.assertRaises(ValueError):
            targets(self.snapshot)

    def test_facebook_destination_must_be_unique(self):
        self.snapshot["data"][0]["text"] = "No link. No tracking."
        with self.assertRaises(ValueError):
            targets(self.snapshot)
        self.snapshot["data"][0]["text"] = LAND + " and " + LAND.replace(
            "preflight", "another")
        with self.assertRaises(ValueError):
            targets(self.snapshot)

    def test_png_jpeg_dimensions(self):
        self.assertEqual(_dimensions(PNG), (1080, 1350))
        self.assertEqual(_dimensions(JPEG), (1080, 1350))
        self.assertIsNone(_dimensions(b"<html>AccessDenied</html>"))

    def test_good_media_and_campaign_html_pass(self):
        def approved(url, kind):
            if kind == "image":
                return 200, {"Content-Type": "image/jpeg"}, JPEG
            return 200, {"Content-Type": "text/html; charset=utf-8"}, (
                b"<!doctype html><html lang='en'><title>RETALLY</title></html>")
        report = run(self.snapshot, live=True, fetcher=approved)
        self.assertEqual(report["counts"]["PASS"], 2)
        self.assertEqual(report["counts"]["FAIL"], 0)
        self.assertEqual(report["counts"]["RECHECK"], 0)
        self.assertEqual(report["targets"][0]["dimensions"], [1080, 1350])

    def test_403_and_429_are_recheck_not_global_failure(self):
        def denied(url, kind):
            return 403 if kind == "image" else 429, {"Content-Type": "text/html"}, b"No"
        report = run(self.snapshot, live=True, fetcher=denied)
        self.assertEqual(report["counts"]["RECHECK"], 2)
        self.assertEqual(report["counts"]["FAIL"], 0)

    def test_missing_public_media_fails_but_does_not_claim_no_post(self):
        def missing(url, kind):
            return 404, {"Content-Type": "text/plain"}, b"Missing"
        report = run(self.snapshot, live=True, fetcher=missing)
        self.assertEqual(report["counts"]["FAIL"], 2)
        self.assertFalse(report["publication_verified"])
        self.assertFalse(report["live_social_provider_checked"])

    def test_incorrect_image_mime_or_error_document_fails(self):
        result = targets(self.snapshot)[0]
        report = inspect(result, fetcher=lambda u, k: (
            200, {"Content-Type": "application/xml"}, b"<Error>AccessDenied</Error>"))
        self.assertEqual(report["state"], "FAIL")
        report = inspect(result, fetcher=lambda u, k: (
            200, {"Content-Type": "image/jpeg"}, b"<html>"))
        self.assertEqual(report["state"], "FAIL")

    def test_tiny_image_recheck_without_fabricated_success(self):
        small = PNG[:16] + struct.pack(">II", 20, 35)
        entry = next(x for x in targets(self.snapshot) if x["kind"] == "image")
        report = inspect(entry, fetcher=lambda u, k: (
            200, {"Content-Type": "image/png"}, small))
        self.assertEqual(report["state"], "RECHECK")
        self.assertEqual(report["dimensions"], [20, 35])

    def test_network_errors_have_no_publication_claim(self):
        def timeout(*args):
            raise TimeoutError("No connection")
        result = run(self.snapshot, live=True, fetcher=timeout)
        self.assertEqual(result["counts"]["RECHECK"], 2)
        self.assertNotIn("No connection", markdown(result))

    def test_cli_reads_realistic_fixture_without_get(self):
        script = Path(__file__).with_name("public_asset_preflight.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snap = root / "snapshot.json"
            out = root / "manifest.json"
            snap.write_text(json.dumps(self.snapshot), encoding="utf-8")
            response = subprocess.run(
                [sys.executable, str(script), "--schedule", str(snap),
                 "--json-output", str(out), "--fail-on-hard-errors"],
                capture_output=True, text=True, check=False)
            self.assertEqual(response.returncode, 0, response.stderr)
            result = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(result["counts"]["NOT_CHECKED"], 2)
            self.assertEqual(result["mode"], "offline_manifest")


if __name__ == "__main__":
    unittest.main()
