"""RETALLY current social campaign route sampling: adversarial, no network."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from public_asset_preflight import run

MEDIA = "https://static.metricool.com/planner/202610/7322512-file-creative.png"
SITE = "https://www.retallyrecovery.com/"
Q = ("utm_source=facebook&utm_medium=organic_social"
     "&utm_campaign=retally_fieldnotes_oct2026")


def post(uid="f1", route="freight-audit-methodology", content="intro",
         network="facebook", image=MEDIA):
    return {
        "uuid": uid, "providers": [{"network": network, "status": "PENDING"}],
        "draft": False, "autoPublish": True,
        "media": [image],
        "mediaAltText": ["RETALLY source-backed educational freight audit graphic."],
        "text": (SITE + route + "?" + Q + "&utm_content=" + content
                 if network == "facebook" else "Save this freight checklist."),
    }


class RouteSamplingTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {"data": [
            post("f1", content="intro"),
            post("f2", content="second"),
            post("f3", route="accessorial-charge-audit", content="third"),
            post("i1", network="instagram"),
        ]}

    def test_offline_all_urls_still_validated_and_no_network(self):
        seen = []
        def forbidden(*args):
            seen.append(args)
            raise AssertionError("Offline mode must not fetch")
        result = run(self.snapshot, only_kind="landing",
                     one_per_route=True, fetcher=forbidden)
        self.assertEqual(seen, [])
        self.assertEqual(result["source_tracked_url_count"], 3)
        self.assertEqual(result["representative_probe_count"], 2)
        self.assertEqual(result["counts"]["NOT_CHECKED"], 2)
        self.assertFalse(result["publication_verified"])
        self.assertFalse(result["live_social_provider_checked"])

    def test_live_checks_once_per_educational_path(self):
        observed = []
        def good(url, kind):
            observed.append((url,kind))
            return 200, {"Content-Type": "text/html"}, b"<html><h1>RETALLY</h1></html>"
        result = run(self.snapshot, only_kind="landing", one_per_route=True,
                     live=True, fetcher=good)
        self.assertEqual(len(observed), 2)
        self.assertEqual(result["counts"]["PASS"], 2)
        self.assertTrue(all(x["kind"] == "landing" for x in result["targets"]))
        self.assertTrue(all(kind == "landing" for _,kind in observed))
        self.assertEqual(sum(x["tracked_url_count"] for x in result["targets"]), 3)

    def test_attribution_uuids_remain_attached_to_deduplicated_route(self):
        result = run(self.snapshot, only_kind="landing", one_per_route=True)
        bypath = {x["canonical_path"]: x for x in result["targets"]}
        self.assertEqual(set(bypath["/freight-audit-methodology"]["uuids"]), {"f1","f2"})
        self.assertEqual(bypath["/freight-audit-methodology"]["tracked_url_count"],2)
        self.assertEqual(bypath["/accessorial-charge-audit"]["uuids"], ["f3"])

    def test_original_manifest_unmodified(self):
        before = copy.deepcopy(self.snapshot)
        run(self.snapshot, only_kind="landing", one_per_route=True)
        self.assertEqual(self.snapshot, before)

    def test_every_facebook_utm_validated_before_deduplication(self):
        self.snapshot["data"][1]["text"] = (
            self.snapshot["data"][1]["text"].replace(
                "utm_source=facebook", "utm_source=instagram"))
        with self.assertRaisesRegex(ValueError, "missing unique tracked"):
            run(self.snapshot, only_kind="landing", one_per_route=True)

    def test_media_validated_even_if_landing_only(self):
        self.snapshot["data"][1]["media"] = [
            "https://static.metricool.com.evil.test/planner/malicious.png"]
        with self.assertRaisesRegex(ValueError, "allowlist"):
            run(self.snapshot, only_kind="landing", one_per_route=True)

    def test_alternative_text_validated_even_in_landing_only_mode(self):
        self.snapshot["data"][1]["mediaAltText"] = []
        with self.assertRaisesRegex(ValueError, "alt"):
            run(self.snapshot, only_kind="landing", one_per_route=True)

    def test_dedup_requires_landing_filter(self):
        with self.assertRaisesRegex(ValueError, "only_kind"):
            run(self.snapshot, one_per_route=True)
        with self.assertRaisesRegex(ValueError, "only_kind"):
            run(self.snapshot, only_kind="image", one_per_route=True)

    def test_unknown_content_type_rejected(self):
        with self.assertRaisesRegex(ValueError, "Only landing"):
            run(self.snapshot, only_kind="video")

    def test_image_only_retains_single_shared_url(self):
        result = run(self.snapshot, only_kind="image")
        self.assertEqual(result["source_tracked_url_count"], 1)
        self.assertEqual(result["representative_probe_count"], 1)
        self.assertEqual(result["targets"][0]["uuids"], ["f1","f2","f3","i1"])

    def test_no_private_or_synthetic_webhost_in_probe(self):
        self.snapshot["data"][0]["text"] = (
            self.snapshot["data"][0]["text"].replace(
                "www.retallyrecovery.com", "localhost"))
        with self.assertRaises(ValueError):
            run(self.snapshot, live=True, only_kind="landing", one_per_route=True,
                fetcher=lambda *args: self.fail("Cannot make a probe to localhost"))

    def test_network_error_is_recheck_not_fake_success(self):
        result = run(self.snapshot, live=True, only_kind="landing",
                     one_per_route=True,
                     fetcher=lambda *a: (_ for _ in ()).throw(TimeoutError()))
        self.assertEqual(result["counts"]["RECHECK"], 2)
        self.assertEqual(result["counts"]["PASS"], 0)
        self.assertFalse(result["publication_verified"])

    def test_non_html_response_fails(self):
        result = run(self.snapshot, live=True, only_kind="landing",
                     one_per_route=True, fetcher=lambda *a: (
                         200, {"Content-Type":"application/json"}, b'{"retally": true}'))
        self.assertEqual(result["counts"]["FAIL"], 2)

    def test_no_src_file_or_unsupported_file_not_inferred_public(self):
        self.snapshot["data"][0]["text"] = SITE + "private/secret?" + Q + "&utm_content=secret"
        # Exact host is allowed by this low-level URL checker; a later source
        # backed validator must reject non-indexable route. Do not claim
        # source-file existence, HTTP success or publication in this result.
        result = run(self.snapshot, only_kind="landing", one_per_route=True)
        self.assertEqual(result["counts"]["NOT_CHECKED"], 3)
        self.assertEqual(result["mode"], "offline_manifest")

    def test_cli_manifest_one_per_route_no_network(self):
        script = Path(__file__).with_name("public_asset_preflight.py")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "schedule.json"
            dst = Path(tmp) / "qa.json"
            src.write_text(json.dumps(self.snapshot), encoding="utf-8")
            cmd = [sys.executable, str(script), "--schedule", str(src),
                   "--only-kind", "landing", "--one-per-route",
                   "--json-output", str(dst)]
            p = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(p.returncode, 0, p.stderr)
            result = json.loads(dst.read_text(encoding="utf-8"))
            self.assertEqual(result["source_tracked_url_count"], 3)
            self.assertEqual(result["representative_probe_count"], 2)


if __name__ == "__main__":
    unittest.main()
