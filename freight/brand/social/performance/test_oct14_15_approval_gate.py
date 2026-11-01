"""Offline safety gate for RETALLY's two owner-approved but not-yet-deployed premium creatives."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "baselines" / "retally-2026-10-12-creative-approved.json"
APPROVAL = ROOT / "approvals" / "retally-oct14-15-owner-approved-2026-10-12.json"
EXPECTED = {
    "-7129364071318205444": ("facebook", "2026-10-14T15:00:00", "MAHXy6EvN24"),
    "6484508306152771452": ("instagram", "2026-10-15T16:00:00", "MAHXy245ZUs"),
}
OLD_MEDIA = "https://static.metricool.com/planner/202610/7322512-file-14283620392379791152.jpeg"


def validate_approval(baseline: dict, approval: dict) -> list[str]:
    errors = []
    rows = approval.get("posts")
    source = baseline.get("data")
    if not isinstance(rows, list) or not isinstance(source, list):
        return ["missing post lists"]
    if approval.get("metricool_brand_id") != "7322512":
        errors.append("unexpected brand")
    if approval.get("production_status") != "NOT_DEPLOYED":
        errors.append("unverified deployment claim")
    if approval.get("provider_publication_verified") is not False:
        errors.append("unverified Meta publication claim")
    if approval.get("forbid_release_from_thumbnail") is not True:
        errors.append("thumbnail safety gate disabled")
    if approval.get("required_minimum_dimensions_px") != [1080, 1350]:
        errors.append("original resolution floor modified")
    if len(rows) != 2 or len({r.get("uuid") for r in rows}) != 2:
        return errors + ["must contain two distinct approved posts only"]
    by_source = {p.get("uuid"): p for p in source}
    if set(r.get("uuid") for r in rows) != set(EXPECTED):
        errors.append("unexpected target UUIDs")
    for item in rows:
        uuid = item["uuid"]
        if uuid not in EXPECTED or uuid not in by_source:
            errors.append("target not in historical approved queue")
            continue
        network, when, media_id = EXPECTED[uuid]
        original = by_source[uuid]
        if item.get("network") != network or item.get("canva_media_id") != media_id:
            errors.append(f"mismatched platform/artifact {uuid}")
        if item.get("canva_natural_px") != [1136, 1408]:
            errors.append(f"unexpected Canva source dimensions {uuid}")
        if item.get("stage") != "WAITING_ORIGINAL_RESOLUTION_BYTES":
            errors.append(f"stage changed without verified file {uuid}")
        if item.get("approved_full_resolution_public_media_url") is not None:
            errors.append(f"unverified full-size link for {uuid}")
        if item.get("original_provider_status") != "PENDING" or item.get("original_draft") is not False or item.get("original_autoPublish") is not True:
            errors.append(f"incorrect original publishing state {uuid}")
        if original.get("providers") != [{"network": network, "status": "PENDING"}] or original.get("draft") is not False or original.get("autoPublish") is not True:
            errors.append(f"source queue provider/state differs for {uuid}")
        if item.get("planned_local") != original.get("publicationDate") or item.get("planned_local") != {"dateTime": when, "timezone": "Europe/Madrid"}:
            errors.append(f"unapproved schedule drift {uuid}")
        if item.get("original_caption") != original.get("text"):
            errors.append(f"unapproved caption change {uuid}")
        if item.get("original_media") != OLD_MEDIA or original.get("media") != [OLD_MEDIA]:
            errors.append(f"original attached image mismatch {uuid}")
        if item.get("original_media_alt") != original.get("mediaAltText", [None])[0]:
            errors.append(f"original alt text mismatch {uuid}")
        if network == "instagram" and (item.get("instagram_is_ai_generated") is not True
                                        or original.get("instagramData", {}).get("isAiGenerated") is not True):
            errors.append("Instagram AI disclosure lost")
    other = [p for p in source if p.get("uuid") not in EXPECTED]
    if len(other) != 15:
        errors.append("baseline must protect 15 other campaign rows")
    protected = [p for p in source if p.get("draft") is True]
    if len(protected) != 4 or any(p.get("autoPublish") is not False for p in protected):
        errors.append("four November draft protections changed")
    return errors


class OwnerCreativeApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads(BASELINE.read_text(encoding="utf-8"))
        cls.approval = json.loads(APPROVAL.read_text(encoding="utf-8"))

    def test_exact_approved_queue_state(self):
        self.assertEqual(validate_approval(self.base, self.approval), [])

    def test_no_thumbnail_as_original_media(self):
        revised = copy.deepcopy(self.approval)
        revised["posts"][0]["approved_full_resolution_public_media_url"] = "https://media.canva.com/example-161x200.jpg"
        self.assertTrue(validate_approval(self.base, revised))

    def test_unverified_publication_is_rejected(self):
        revised = copy.deepcopy(self.approval)
        revised["provider_publication_verified"] = True
        self.assertIn("unverified Meta publication claim", validate_approval(self.base, revised))

    def test_forbid_caption_edits(self):
        revised = copy.deepcopy(self.approval)
        revised["posts"][1]["original_caption"] += " Guaranteed refund!"
        self.assertTrue(validate_approval(self.base, revised))

    def test_forbid_date_change(self):
        revised = copy.deepcopy(self.approval)
        revised["posts"][0]["planned_local"]["dateTime"] = "2026-10-14T16:00:00"
        self.assertTrue(validate_approval(self.base, revised))

    def test_protect_november_drafts(self):
        revised = copy.deepcopy(self.base)
        next(x for x in revised["data"] if x["draft"])["autoPublish"] = True
        self.assertIn("four November draft protections changed", validate_approval(revised, self.approval))


if __name__ == "__main__":
    unittest.main()
