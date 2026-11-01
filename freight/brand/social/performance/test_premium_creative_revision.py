"""Fail-closed offline regression for approved RETALLY premium creative rollout.

Preserve the 2026-10-11 baseline. The dated 2026-10-12 revision may change
exactly the two owner's approved launch media URLs and corresponding alt text.
Never read external accounts or infer public Meta publication from a planner.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "baselines"
OLD = ROOT / "retally-2026-10-11.json"
NEW = ROOT / "retally-2026-10-12-creative-approved.json"

APPROVED = {
    "-1816987399007942347": ("facebook", "2026-10-12T15:00:00"),
    "-7860495589122225702": ("instagram", "2026-10-13T16:00:00"),
}
PREVIOUS_MEDIA = "https://static.metricool.com/planner/202610/7322512-file-8910111593678733120.jpeg"
APPROVED_MEDIA = "https://static.metricool.com/planner/202610/7322512-file-3987091251411167546.png"


def validate(old: dict, revised: dict) -> list[str]:
    problems: list[str] = []
    a = old.get("data")
    b = revised.get("data")
    if not isinstance(a, list) or not isinstance(b, list):
        return ["snapshot does not have data arrays"]
    if len(a) != 17 or len(b) != 17:
        problems.append("must have exactly 17 FB/IG campaign records")

    by_a = {p.get("uuid"): p for p in a}
    by_b = {p.get("uuid"): p for p in b}
    if set(by_a) != set(by_b) or len(by_a) != len(a) or len(by_b) != len(b):
        problems.append("UUID set changed or duplicates present")
        return problems

    changes = set()
    active = draft = 0
    for uuid, prev in by_a.items():
        cur = by_b[uuid]
        if prev.get("media") != cur.get("media") or prev.get("mediaAltText") != cur.get("mediaAltText"):
            changes.add(uuid)
        before_other = {k: v for k, v in prev.items() if k not in ("media", "mediaAltText")}
        after_other = {k: v for k, v in cur.items() if k not in ("media", "mediaAltText")}
        if before_other != after_other:
            problems.append(f"non-media metadata changed: {uuid}")
        if uuid in APPROVED:
            network, madrid = APPROVED[uuid]
            if prev.get("media") != [PREVIOUS_MEDIA] or cur.get("media") != [APPROVED_MEDIA]:
                problems.append(f"approved media mismatch: {uuid}")
            if cur.get("mediaAltText") == prev.get("mediaAltText"):
                problems.append(f"alt text wasn't refreshed: {uuid}")
            if len(cur.get("mediaAltText") or []) != 1:
                problems.append(f"incorrect image alt count: {uuid}")
            if cur.get("providers") != [{"network": network, "status": "PENDING"}]:
                problems.append(f"provider status changed: {uuid}")
            if cur.get("publicationDate") != {"dateTime": madrid, "timezone": "Europe/Madrid"}:
                problems.append(f"original date/time moved: {uuid}")
            if cur.get("draft") is not False or cur.get("autoPublish") is not True:
                problems.append(f"approved post isn't publishing automatically: {uuid}")
            if network == "instagram" and cur.get("instagramData", {}).get("isAiGenerated") is not True:
                problems.append("Instagram AI disclosure unexpectedly removed")
        elif prev != cur:
            problems.append(f"unauthorized change to other post: {uuid}")
        if cur.get("draft") is True:
            draft += 1
            if cur.get("autoPublish") is not False:
                problems.append(f"protected draft enabled: {uuid}")
        elif cur.get("draft") is False and cur.get("autoPublish") is True:
            active += 1
        else:
            problems.append(f"unknown planner state: {uuid}")

    if changes != set(APPROVED):
        problems.append("authorized two-post change set not exact")
    if active != 13 or draft != 4:
        problems.append("wrong active/draft counts")
    revision = revised.get("accepted_creative_revision") or {}
    if (set(revision.get("changed_post_uuids") or []) != set(APPROVED)
            or revision.get("original_shared_media") != PREVIOUS_MEDIA
            or revision.get("accepted_shared_media") != APPROVED_MEDIA
            or revision.get("publication_verified") is not False):
        problems.append("change approval metadata invalid or asserts publication")
    if revised.get("revision_of") != "retally-2026-10-11.json":
        problems.append("revision provenance lost")
    return problems


class PremiumCreativeRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = json.loads(OLD.read_text(encoding="utf-8"))
        cls.revised = json.loads(NEW.read_text(encoding="utf-8"))

    def test_approved_two_post_revision_passes(self):
        self.assertEqual(validate(self.old, self.revised), [])

    def test_reject_caption_or_utm_changes(self):
        copy_revision = copy.deepcopy(self.revised)
        p = next(x for x in copy_revision["data"] if x["uuid"] in APPROVED)
        p["text"] += " unreliable claim"
        self.assertTrue(validate(self.old, copy_revision))

    def test_reject_changes_to_protected_november_drafts(self):
        copy_revision = copy.deepcopy(self.revised)
        p = next(x for x in copy_revision["data"] if x["draft"] is True)
        p["autoPublish"] = True
        self.assertTrue(validate(self.old, copy_revision))

    def test_reject_wrong_platform_and_date(self):
        copy_revision = copy.deepcopy(self.revised)
        p = next(x for x in copy_revision["data"] if x["uuid"] == APPROVED.keys().__iter__().__next__())
        p["publicationDate"]["dateTime"] = "2026-10-12T16:00:00"
        self.assertTrue(validate(self.old, copy_revision))

    def test_reject_fake_publication_proof(self):
        copy_revision = copy.deepcopy(self.revised)
        copy_revision["accepted_creative_revision"]["publication_verified"] = True
        self.assertTrue(validate(self.old, copy_revision))

    def test_reject_missing_or_extra_media(self):
        copy_revision = copy.deepcopy(self.revised)
        p = next(x for x in copy_revision["data"] if x["uuid"] == "-1816987399007942347")
        p["media"].append(APPROVED_MEDIA)
        self.assertTrue(validate(self.old, copy_revision))


if __name__ == "__main__":
    unittest.main()
