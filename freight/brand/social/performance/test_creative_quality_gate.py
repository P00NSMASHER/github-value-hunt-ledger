"""Offline adversarial tests for RETALLY's publication/creative quality gate."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from creative_quality_gate import audit, site_link

MEDIA = "https://static.metricool.com/planner/202610/7322512-file-1234.png"
VIDEO = "https://static.metricool.com/planner/202610/7322512-file-1234.mp4"
LINK = ("https://www.retallyrecovery.com/freight-audit-methodology?"
        "utm_source=facebook&utm_medium=organic_social"
        "&utm_campaign=retally_qa&utm_content=methodology")


def fb(uuid="fb-1", **kwargs):
    row = {
        "uuid": uuid, "providers": [{"network": "facebook", "status": "PENDING"}],
        "publicationDate": {"dateTime": "2026-11-10T09:00:00",
                            "timezone": "America/New_York"},
        "draft": False, "autoPublish": True,
        "text": "A freight invoice can look correct. Verify its source.\n" + LINK +
                "\n\n#FreightAudit",
        "media": [MEDIA], "mediaAltText": [
            "An original invoice and rate agreement shown in a branded RETALLY graphic."
        ], "facebookData": {"type": "POST"},
    }
    row.update(kwargs)
    return row


def instagram(uuid="ig-1", **kwargs):
    row = {
        "uuid": uuid, "providers": [{"network": "instagram", "status": "PENDING"}],
        "publicationDate": {"dateTime": "2026-11-11T10:00:00",
                            "timezone": "America/New_York"},
        "draft": False, "autoPublish": True,
        "text": "Liftgate charge? Does the document support it?\n\nSave this checklist.",
        "media": [MEDIA], "mediaAltText": [
            "RETALLY liftgate fee evidence graphic with signed rate and delivery paperwork."
        ], "instagramData": {"type": "POST", "isAiGenerated": True},
    }
    row.update(kwargs)
    return row


class QualityGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "freight-audit-methodology.html").write_text("<html></html>")

    def tearDown(self):
        self.temp.cleanup()

    def check(self, *rows):
        return audit({"data": list(rows)}, site_dir=self.root)

    def codes(self, *rows):
        return {x["code"] for x in self.check(*rows)["issues"]}

    def test_valid_facebook_and_instagram(self):
        result = self.check(fb(), instagram())
        self.assertEqual(result["severity_counts"]["HIGH"], 0)
        self.assertEqual(result["active_posts"], 2)
        self.assertTrue(result["provider_pending_is_not_publication_proof"])

    def test_stable_uuid_not_numeric_id_used(self):
        a, b = fb("one"), fb("two")
        b["id"] = a["id"] = 12345
        b["publicationDate"]["dateTime"] = "2026-11-11T09:00:00"
        self.assertEqual(self.check(a, b)["severity_counts"]["HIGH"], 0)

    def test_missing_and_wrong_campaign_parameters(self):
        a = fb(text="No link included")
        self.assertIn("INVALID_TRACKED_CTA", self.codes(a))
        b = fb(text=fb()["text"].replace("utm_source=facebook", "utm_source=instagram"))
        self.assertIn("INVALID_TRACKED_CTA", self.codes(b))

    def test_private_or_nonexistent_destination_is_blocked(self):
        self.assertIn("INVALID_TRACKED_CTA",
                      self.codes(fb(text=fb()["text"].replace(
                          "freight-audit-methodology?", "nonexistent-promotion?"))))
        self.assertFalse(site_link("https://www.retallyrecovery.com/api/inquiry?" +
                                   LINK.split("?", 1)[1], "facebook", site_dir=self.root)[0])

    def test_unverified_intake_anchor_rejected(self):
        url = "https://www.retallyrecovery.com/?" + LINK.split("?", 1)[1] + "#start-audit"
        self.assertIn("INVALID_TRACKED_CTA", self.codes(fb(text=url)))

    def test_topic_media_mismatch(self):
        p = instagram(text="Liftgate fee disputed.\n\nSave this checklist.",
                      mediaAltText=["Branded RETALLY warehouse rate sheet comparison illustration."])
        self.assertIn("VISUAL_TOPIC_MISMATCH", self.codes(p))

    def test_related_rate_visual_is_accepted(self):
        p = fb(text="Two rate sheets. One shipment.\n" + LINK,
               mediaAltText=["Which rate version governed the billed freight shipment?"])
        self.assertNotIn("VISUAL_TOPIC_MISMATCH", self.codes(p))

    def test_synthetic_clock_example_must_be_labeled(self):
        p = fb(text="Gate in: 08:30; gate out: 11:00\n" + LINK)
        self.assertIn("UNLABELLED_SCENARIO", self.codes(p))
        p["text"] = "ILLUSTRATIVE EXAMPLE. Gate in: 08:30; gate out: 11:00\n" + LINK
        self.assertNotIn("UNLABELLED_SCENARIO", self.codes(p))

    def test_hard_claim_denied(self):
        p = fb(text="RETALLY recovered $125,000 from real shippers.\n" + LINK)
        self.assertIn("UNVERIFIED_CLAIM", self.codes(p))
        p["text"] = "Recovery is not guaranteed. Findings need proof.\n" + LINK
        self.assertNotIn("UNVERIFIED_CLAIM", self.codes(p))

    def test_duplicate_uuid_and_schedule_collision(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(fb(), fb())
        r = self.check(fb("one"), fb("two"))
        self.assertIn("SLOT_COLLISION", {x["code"] for x in r["issues"]})

    def test_missing_media_alts_or_untrusted_origin(self):
        self.assertIn("REQUIRED_MEDIA_MISSING", self.codes(instagram(media=[],
                                                                      mediaAltText=[])))
        self.assertIn("ALT_COUNT", self.codes(instagram(mediaAltText=[])))
        self.assertIn("UNTRUSTED_MEDIA", self.codes(instagram(media=[
            "https://evil.example.com/asset.png"])))

    def test_youtube_requires_source_tags_video_and_metadata(self):
        row = fb("yt-1", providers=[{"network": "youtube", "status": "PENDING"}],
                 media=[VIDEO], mediaAltText=[],
                 text="3 freight audit checks.\n" + LINK.replace(
                     "utm_source=facebook", "utm_source=youtube"),
                 youtubeData={"title": "3 freight charges", "madeForKids": False})
        self.assertEqual(self.check(row)["severity_counts"]["HIGH"], 0)
        row["youtubeData"] = {"title": ""}
        self.assertIn("YOUTUBE_METADATA", self.codes(row))

    def test_linkedin_draft_remains_unpublished(self):
        p = fb("li", providers=[{"network": "linkedin", "status": "PENDING"}],
               draft=True, autoPublish=False, media=[], mediaAltText=[], text="For review only")
        self.assertEqual(self.check(p)["severity_counts"]["HIGH"], 0)
        self.assertEqual(self.check(p)["draft_posts"], 1)
        p["autoPublish"] = True
        self.assertIn("DRAFT_AUTO", self.codes(p))

    def test_fatigue_is_info_not_false_failure(self):
        posts = [fb(f"fb-{i}") for i in range(4)]
        for i, p in enumerate(posts):
            p["publicationDate"]["dateTime"] = f"2026-11-{10 + i:02d}T09:00:00"
        result = self.check(*posts)
        self.assertIn("CREATIVE_FATIGUE", {i["code"] for i in result["issues"]})
        self.assertEqual(result["severity_counts"]["HIGH"], 0)

    def test_nonexistent_dst_wall_clock_is_rejected(self):
        p = fb(publicationDate={"dateTime": "2026-03-08T02:30:00",
                                "timezone": "America/New_York"})
        with self.assertRaisesRegex(ValueError, "Nonexistent"):
            self.check(p)

    def test_metricool_wrapped_export(self):
        wrapped = {"text": json.dumps({"data": [fb()]})}
        self.assertEqual(audit(wrapped, site_dir=self.root)["active_posts"], 1)

    def test_read_only_does_not_mutate_input(self):
        data = {"data": [fb(), instagram()]}
        frozen = copy.deepcopy(data)
        self.check(*data["data"])
        self.assertEqual(data, frozen)


if __name__ == "__main__":
    unittest.main()
