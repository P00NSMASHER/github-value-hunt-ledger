"""Offline integrity gate for the October 11 public-browser image observation.

The image receipt is intentionally weaker evidence than a binary checksum or
independently verified Meta post. No network, credentials, or external deps.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "baselines" / "retally-2026-10-11.json"
RECEIPT = ROOT / "observations" / "retally-october-visual-2026-10-11.json"


def validate(snapshot: dict, report: dict) -> list[str]:
    """Validate receipt completeness against the immutable campaign snapshot."""
    errors: list[str] = []
    if report.get("evidence_method") != "read_only_public_browser_direct_image_view":
        errors.append("unexpected evidence source")
    if report.get("observation_date") != "2026-10-11":
        errors.append("unexpected observation date")
    if report.get("browser_mobile_viewport_px") != 390:
        errors.append("unexpected mobile viewport")
    if report.get("conclusions", {}).get("image_bytes_checksum_verified") is not False:
        errors.append("must not claim independent byte checksum")
    if report.get("conclusions", {}).get("platform_publication_verified") is not False:
        errors.append("must not claim live Meta publication")

    expected: dict[str, dict[str, set[str]]] = {}
    active = []
    draft_count = 0
    for post in snapshot.get("data", []):
        providers = post.get("providers") or []
        if len(providers) != 1 or providers[0].get("network") not in ("facebook", "instagram"):
            continue
        network = providers[0]["network"]
        if post.get("draft") is True:
            draft_count += 1
            if post.get("autoPublish") is not False:
                errors.append("draft has auto-publish enabled")
            continue
        if post.get("draft") is not False or post.get("autoPublish") is not True:
            errors.append("unexpected campaign publication state")
            continue
        if post.get("providers")[0].get("status") != "PENDING":
            errors.append("unexpected frozen baseline provider status")
        uid = post.get("uuid")
        if not isinstance(uid, str) or not uid:
            errors.append("active post missing stable UUID")
            continue
        active.append(uid)
        for url in post.get("media") or []:
            item = expected.setdefault(url, {"stable_post_uuids": set(), "networks": set()})
            item["stable_post_uuids"].add(uid)
            item["networks"].add(network)

    if len(active) != 13 or len(set(active)) != 13:
        errors.append("expected thirteen unique active October posts")
    if draft_count != 4:
        errors.append("expected four protected November drafts")
    if len(expected) != 11:
        errors.append("expected eleven unique October images")
    if report.get("campaign_active_posts_examined") != len(active):
        errors.append("wrong claimed active post count")
    if report.get("unique_media_examined") != len(expected):
        errors.append("wrong claimed image count")

    supplied = report.get("assets")
    if not isinstance(supplied, list):
        return errors + ["receipt asset list missing"]
    seen = set()
    for asset in supplied:
        if not isinstance(asset, dict):
            errors.append("malformed asset item")
            continue
        url = asset.get("url")
        if not isinstance(url, str) or url in seen:
            errors.append("missing or duplicated asset URL")
            continue
        seen.add(url)
        p = urlsplit(url)
        if (p.scheme != "https" or p.hostname != "static.metricool.com"
                or not p.path.startswith("/planner/") or p.query or p.fragment
                or not p.path.lower().endswith((".png", ".jpeg", ".jpg"))):
            errors.append("asset URL outside exact public image allowlist")
        if url not in expected:
            errors.append("receipt contains unrelated/unapproved media")
            continue
        e = expected[url]
        if set(asset.get("stable_post_uuids") or []) != e["stable_post_uuids"]:
            errors.append("image post-UUID attribution mismatched")
        if set(asset.get("networks") or []) != e["networks"]:
            errors.append("image network attribution mismatched")
        if (asset.get("natural_width_px"), asset.get("natural_height_px")) != (1080, 1350):
            errors.append("incorrect observed media dimensions")
        if asset.get("browser_visual_status") != "PASS":
            errors.append("media not evidenced as browser-visible PASS")
        if (asset.get("public_browser_loaded") is not True
                or asset.get("mobile_crop_observed") is not False
                or asset.get("main_text_readable") is not True):
            errors.append("media visibility or mobile observation changed")
        if asset.get("checksum_verified") is not False:
            errors.append("receipt must not claim image checksum verification")
        if asset.get("provider_publication_status") != "NOT_VERIFIED":
            errors.append("receipt must not assert provider publication")
    if seen != set(expected):
        errors.append("receipt does not exactly cover the eleven scheduled images")
    return errors


class VisualReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        cls.report = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_real_october_visual_receipt_matches_frozen_campaign(self):
        self.assertEqual(validate(self.snapshot, self.report), [])

    def test_reject_missing_image_without_rewriting_schedule(self):
        broken = copy.deepcopy(self.report)
        broken["assets"].pop()
        self.assertTrue(validate(self.snapshot, broken))

    def test_reject_unsupported_publication_claim(self):
        broken = copy.deepcopy(self.report)
        broken["conclusions"]["platform_publication_verified"] = True
        self.assertIn("must not claim live Meta publication", validate(self.snapshot, broken))

    def test_reject_unapproved_image_url_and_uuid(self):
        broken = copy.deepcopy(self.report)
        broken["assets"][0]["url"] = "https://example.net/planner/other.png"
        self.assertTrue(validate(self.snapshot, broken))
        broken = copy.deepcopy(self.report)
        broken["assets"][0]["stable_post_uuids"] = ["NOT_APPROVED"]
        self.assertIn("image post-UUID attribution mismatched", validate(self.snapshot, broken))

    def test_protect_november_drafts(self):
        broken = copy.deepcopy(self.snapshot)
        draft = next(p for p in broken["data"] if p["draft"])
        draft["autoPublish"] = True
        self.assertIn("draft has auto-publish enabled", validate(broken, self.report))


if __name__ == "__main__":
    unittest.main()
