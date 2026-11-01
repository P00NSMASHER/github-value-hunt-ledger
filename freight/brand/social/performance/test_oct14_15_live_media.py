"""Offline, immutable RETALLY Oct14-15 deployed media acceptance test.

Provider-reported scheduled state and locally verified original JPEG hashes are
separate from Meta public publication or a byte-for-byte CDN rehost receipt.
"""
from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BEFORE = ROOT / "baselines" / "retally-2026-10-12-creative-approved.json"
AFTER = ROOT / "baselines" / "retally-2026-10-12-oct14-15-creative-approved.json"
RECEIPT = ROOT / "receipts" / "retally-2026-10-12-oct14-15-live-media.json"
ORIGINAL_MEDIA = "https://static.metricool.com/planner/202610/7322512-file-14283620392379791152.jpeg"
APPROVED = {
    "-7129364071318205444": {
        "network": "facebook",
        "date": "2026-10-14T15:00:00",
        "new_media": "https://static.metricool.com/planner/202610/7322512-file-17668956900351564739.jpeg",
        "id": 394236354,
        "original_hash": "ce46f4ac4ba89d6d5893818e94476f54e593f4ea7cab127d2a7eb041ead3f5ff",
        "original_bytes": 238671,
        "canva_id": "MAHXy6EvN24",
        "alt_terms": ("already have a freight auditor", "prior findings", "credits"),
    },
    "6484508306152771452": {
        "network": "instagram",
        "date": "2026-10-15T16:00:00",
        "new_media": "https://static.metricool.com/planner/202610/7322512-file-6419974974892061437.jpeg",
        "id": 394236766,
        "original_hash": "c6d01acb4b0cd79a7e1dc56359d95ee4bcf11954360b95a905c2aee68c7b3ad2",
        "original_bytes": 221639,
        "canva_id": "MAHXy245ZUs",
        "alt_terms": ("two invoices", "one shipment", "credits"),
    },
}


def verify(before: dict, after: dict, receipt: dict) -> list[str]:
    errors = []
    old, new = before.get("data"), after.get("data")
    if not isinstance(old, list) or not isinstance(new, list):
        return ["missing baseline data"]
    if len(old) != 17 or len(new) != 17:
        errors.append("expected exactly 17 original Facebook/Instagram records")
    old_by = {p["uuid"]: p for p in old}
    new_by = {p["uuid"]: p for p in new}
    if len(old_by) != len(old) or len(new_by) != len(new) or set(old_by) != set(new_by):
        return errors + ["duplicate, added, or removed UUID"]
    changed = set()
    for uid in old_by:
        o, n = old_by[uid], new_by[uid]
        non_media_old = {k: v for k, v in o.items() if k not in ("media", "mediaAltText")}
        non_media_new = {k: v for k, v in n.items() if k not in ("media", "mediaAltText")}
        if non_media_old != non_media_new:
            errors.append(f"non-media schedule/caption/provider metadata changed: {uid}")
        if o.get("media") != n.get("media") or o.get("mediaAltText") != n.get("mediaAltText"):
            changed.add(uid)
        if uid in APPROVED:
            a = APPROVED[uid]
            if o.get("media") != [ORIGINAL_MEDIA] or n.get("media") != [a["new_media"]]:
                errors.append(f"wrong exact media replacement: {uid}")
            if n.get("mediaAltText") == o.get("mediaAltText") or len(n.get("mediaAltText") or []) != 1:
                errors.append(f"missing updated image alt: {uid}")
            alt = (n.get("mediaAltText") or [""])[0].lower()
            if any(word not in alt for word in a["alt_terms"]):
                errors.append(f"alt text no longer describes topic: {uid}")
            if n.get("providers") != [{"network": a["network"], "status": "PENDING"}]:
                errors.append(f"unexpected historical provider status: {uid}")
            if n.get("publicationDate") != {"dateTime": a["date"], "timezone": "Europe/Madrid"}:
                errors.append(f"original local scheduled slot changed: {uid}")
            if n.get("autoPublish") is not True or n.get("draft") is not False:
                errors.append(f"active scheduled post altered: {uid}")
            if uid == "6484508306152771452" and n.get("instagramData", {}).get("isAiGenerated") is not True:
                errors.append("Instagram AI disclosure missing")
            if uid == "-7129364071318205444" and "utm_content=independent_second_look" not in n.get("text", ""):
                errors.append("Facebook tracked landing link removed")
        elif o != n:
            errors.append(f"unapproved unrelated post changed: {uid}")
    if changed != set(APPROVED):
        errors.append("changed posts differ from exactly two approved UUIDs")
    if sum(p.get("draft") is True for p in new) != 4 or any(
        p.get("autoPublish") is not False for p in new if p.get("draft") is True
    ):
        errors.append("four November drafts no longer protected")
    if after.get("revision_of") != "retally-2026-10-12-creative-approved.json":
        errors.append("previous accepted baseline lost")
    revision = after.get("accepted_creative_revision_oct14_15") or {}
    if set(revision.get("changed_post_uuids") or []) != set(APPROVED):
        errors.append("revision UUIDs mismatch")
    if revision.get("publication_verified") is not False:
        errors.append("baseline improperly claims platform publication")
    if receipt.get("status") != "DEPLOYED_TO_SCHEDULED_POSTS":
        errors.append("provider deployment status missing")
    if receipt.get("platform_publication_verified") is not False:
        errors.append("receipt improperly claims Meta publication")
    if receipt.get("post_count") != 2 or len(receipt.get("posts") or []) != 2:
        errors.append("receipt must have two records")
    receipt_by = {p.get("uuid"): p for p in receipt.get("posts") or []}
    if set(receipt_by) != set(APPROVED):
        errors.append("receipt UUIDs do not match two approved posts")
        return errors
    for uid, a in APPROVED.items():
        item = receipt_by[uid]
        if item.get("original_uploaded_file_dimensions_px") != [1136, 1408]:
            errors.append(f"wrong original JPEG dimensions: {uid}")
        if item.get("original_uploaded_file_sha256") != a["original_hash"] or not re.fullmatch(
                r"[0-9a-f]{64}", item.get("original_uploaded_file_sha256", "")):
            errors.append(f"unverified source SHA-256: {uid}")
        if item.get("original_uploaded_file_bytes") != a["original_bytes"]:
            errors.append(f"unexpected original file length: {uid}")
        if item.get("canva_media_id") != a["canva_id"]:
            errors.append(f"approved Canva ID changed: {uid}")
        if item.get("new_rehosted_media_url") != a["new_media"] or item.get("original_media_url") != ORIGINAL_MEDIA:
            errors.append(f"receipt media URL mismatch: {uid}")
        if item.get("metricool_post_id_after_change") != a["id"]:
            errors.append(f"rehosted Metricool numeric ID mismatch: {uid}")
        if item.get("publicationDate") != {"dateTime": a["date"], "timezone": "Europe/Madrid"}:
            errors.append(f"receipt post time changed: {uid}")
        if item.get("provider_status") != "PENDING" or item.get("scheduled_autoPublish") is not True or item.get("scheduled_draft") is not False:
            errors.append(f"receipt claims unexpected publication state: {uid}")
        if item.get("public_meta_permalink_verified") is not False:
            errors.append(f"no independent public Meta receipt exists: {uid}")
        if item.get("post_caption") != new_by[uid].get("text") or item.get("new_image_alt") != new_by[uid].get("mediaAltText", [None])[0]:
            errors.append(f"receipt content differs from frozen snapshot: {uid}")
        if uid == "6484508306152771452" and item.get("instagram_ai_generated") is not True:
            errors.append("receipt Instagram AI disclosure missing")
    return errors


class Oct1415MediaAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = json.loads(BEFORE.read_text(encoding="utf-8"))
        cls.after = json.loads(AFTER.read_text(encoding="utf-8"))
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_live_replacement_matches_approved_history(self):
        self.assertEqual(verify(self.before, self.after, self.receipt), [])

    def test_no_extra_post_changes(self):
        revised = copy.deepcopy(self.after)
        outside = next(p for p in revised["data"] if p["uuid"] not in APPROVED and not p["draft"])
        outside["text"] += " change"
        self.assertTrue(verify(self.before, revised, self.receipt))

    def test_no_november_release(self):
        revised = copy.deepcopy(self.after)
        next(p for p in revised["data"] if p["draft"])["autoPublish"] = True
        self.assertTrue(verify(self.before, revised, self.receipt))

    def test_no_edited_caption_or_time(self):
        revised = copy.deepcopy(self.after)
        approved = next(p for p in revised["data"] if p["uuid"] == "6484508306152771452")
        approved["publicationDate"]["dateTime"] = "2026-10-15T15:00:00"
        self.assertTrue(verify(self.before, revised, self.receipt))

    def test_no_false_verified_publication(self):
        r = copy.deepcopy(self.receipt)
        r["platform_publication_verified"] = True
        self.assertTrue(verify(self.before, self.after, r))

    def test_no_corrupted_original_fingerprint(self):
        r = copy.deepcopy(self.receipt)
        r["posts"][0]["original_uploaded_file_sha256"] = "0" * 64
        self.assertTrue(verify(self.before, self.after, r))

    def test_approved_media_url_cannot_revert(self):
        revised = copy.deepcopy(self.after)
        next(p for p in revised["data"] if p["uuid"] == "-7129364071318205444")["media"] = [ORIGINAL_MEDIA]
        self.assertTrue(verify(self.before, revised, self.receipt))


if __name__ == "__main__":
    unittest.main()
