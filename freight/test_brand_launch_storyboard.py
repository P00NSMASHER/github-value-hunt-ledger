"""Source-bound historical RETALLY storyboard safety and arithmetic checks.

This does not validate any actual video or grant media rights.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import unittest

STORYBOARD = Path(__file__).parent / "brand/social/video/storyboard.json"


class BrandStoryContractTests(unittest.TestCase):
    def setUp(self):
        self.story = json.loads(STORYBOARD.read_text(encoding="utf-8"))

    def test_not_approved_or_publishable(self):
        self.assertEqual(self.story["status"], "preproduction-not-approved")
        self.assertIs(self.story["deliverable"]["auto_publish"], False)
        self.assertIn("owner explicitly approves final MP4", self.story["human_release_gates"])

    def test_pronunciation_and_rights_notice(self):
        p = self.story["pronunciation"]
        self.assertEqual(p["spoken"], "re-tally")
        self.assertIs(p["must_be_listened_to"], True)
        self.assertIn("never reuse", self.story["reference"])

    def test_illustrative_evidence_arithmetic_not_customer_cash(self):
        h = self.story["hypothetical"]
        fmt = "%H:%M"
        delta = datetime.strptime(h["departure"], fmt) - datetime.strptime(h["arrival"], fmt)
        self.assertEqual(int(delta.total_seconds() // 60), h["dwell_minutes"])
        self.assertEqual(
            max(h["dwell_minutes"] - h["contract_free_minutes"], 0),
            h["excess_minutes"],
        )
        self.assertEqual(h["billed_minutes"] - h["excess_minutes"],
                         h["candidate_variance_minutes"])
        self.assertGreaterEqual(h["candidate_variance_minutes"], 0)
        self.assertIn("NOT ACTUAL CUSTOMER RESULTS", h["disclaimer"])

    def test_scenes_are_contiguous_and_within_duration(self):
        scenes = self.story["scenes"]
        self.assertTrue(scenes)
        self.assertEqual(scenes[0]["start"], 0)
        for first, second in zip(scenes, scenes[1:]):
            self.assertEqual(first["end"], second["start"])
            self.assertLess(first["start"], first["end"])
        self.assertLess(scenes[-1]["start"], scenes[-1]["end"])
        duration = scenes[-1]["end"]
        lo, hi = self.story["deliverable"]["duration_range_seconds"]
        self.assertLessEqual(lo, duration)
        self.assertLessEqual(duration, hi)


if __name__ == "__main__":
    unittest.main()
