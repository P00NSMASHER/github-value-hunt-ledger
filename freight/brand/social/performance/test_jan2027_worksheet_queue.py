"""Offline integrity gate for RETALLY's January 2027 social campaign receipt.

Reads only committed public planner metadata, never sends/posts/queries any
social account. A scheduled post is NOT independent proof of publication.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import json
import re
import unittest

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"observations"/"retally-jan-2027-worksheet-queue-20261013.json"
SOURCE=ROOT/"retally-worksheet-social-drafts-20261013.json"
CAMPAIGN="retally_worksheet_education_2027q1"
HOST="www.retallyrecovery.com"
PAGE="/freight-invoice-audit-checklist"

class JanuaryCampaignReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.source=json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.posts=cls.receipt["posts"]

    def test_exact_facebook_instagram_count_and_four_weeks(self):
        self.assertEqual(len(self.posts),16)
        self.assertEqual(Counter(x["network"] for x in self.posts),
                         {"facebook":8,"instagram":8})
        self.assertEqual(len({x["scheduled_local"] for x in self.posts}),16)
        self.assertEqual(
            sorted(x["scheduled_local"] for x in self.posts),
            [f"2027-01-{d:02d}T{h}:00:00" for d,h in (
                (5,"09"),(6,"10"),(7,"09"),(8,"10"),
                (12,"09"),(13,"10"),(14,"09"),(15,"10"),
                (19,"09"),(20,"10"),(21,"09"),(22,"10"),
                (26,"09"),(27,"10"),(28,"09"),(29,"10"))])

    def test_future_dates_are_consistent_and_never_timezone_naive(self):
        for row in self.posts:
            dt=datetime.fromisoformat(row["scheduled_local"])
            self.assertEqual(dt.year,2027)
            self.assertEqual(dt.month,1)
            self.assertEqual(row["timezone"],"America/New_York")
            self.assertFalse(row["draft"])
            self.assertTrue(row["auto_publish"])
            self.assertTrue(row["planner_id_at_capture"].isdigit())
            self.assertTrue(bool(row["uuid"]))

    def test_immutable_identity_uniqueness(self):
        self.assertEqual(len({x["uuid"] for x in self.posts}),16)
        self.assertEqual(len({x["planner_id_at_capture"] for x in self.posts}),16)
        self.assertEqual(len(set((x["network"],x["scheduled_local"]) for x in self.posts)),16)

    def test_source_copies_match_the_original_review_proposals(self):
        candidates=[p for p in self.source["posts"] if p["network"] in ("facebook","instagram")]
        self.assertEqual(len(candidates),16)
        seen=set()
        for row in self.posts:
            matching=[p for p in candidates if
                      p["network"]==row["network"] and
                      p["copy"].splitlines()[0]==row["first_line"]]
            self.assertEqual(len(matching),1,row["uuid"])
            self.assertEqual(row["caption"].splitlines()[0],row["first_line"])
            item=matching[0]
            seen.add(item["id"])
            if row["network"]=="instagram":
                self.assertEqual(row["caption"],item["copy"])
        self.assertEqual(len(seen),16)

    def test_new_facebook_campaign_links_are_unique_and_exact(self):
        utms=set()
        for row in self.posts:
            urls=re.findall(r"https://[^\s<>]+",row["caption"])
            if row["network"]=="instagram":
                self.assertFalse(urls,row["uuid"])
                continue
            self.assertEqual(len(urls),1,row["uuid"])
            u=urlsplit(urls[0])
            self.assertEqual((u.scheme,u.hostname,u.path,u.fragment),
                             ("https",HOST,PAGE,"worksheet"))
            self.assertFalse(u.username or u.password or u.port)
            q=parse_qs(u.query)
            self.assertEqual(q.get("utm_campaign"),[CAMPAIGN])
            self.assertEqual(q.get("utm_source"),["facebook"])
            self.assertEqual(q.get("utm_medium"),["organic_social"])
            self.assertEqual(len(q.get("utm_content",[])),1)
            marker=q["utm_content"][0]
            self.assertNotIn(marker,utms)
            utms.add(marker)
        self.assertEqual(len(utms),8)

    def test_all_media_comes_from_previous_public_planner_assets(self):
        for row in self.posts:
            media=row["media"]
            alts=row["media_alt_text"]
            self.assertIsInstance(media,list)
            self.assertIsInstance(alts,list)
            self.assertTrue(media)
            self.assertEqual(len(media),len(alts))
            self.assertLessEqual(len(media),4)
            for url,alt in zip(media,alts):
                p=urlsplit(url)
                self.assertEqual((p.scheme,p.hostname),
                                 ("https","static.metricool.com"))
                self.assertTrue(p.path.startswith("/planner/202610/7322512-"))
                self.assertIn(Path(p.path).suffix.lower(),
                              {".png",".jpeg",".jpg",".webp"})
                self.assertGreater(len(alt.strip()),40)
                self.assertNotIn("real customer invoice",alt.lower())

    def test_only_rate_topic_contains_four_slide_carousels(self):
        rated=[p for p in self.posts if len(p["media"])==4]
        self.assertEqual(len(rated),2)
        self.assertTrue(all("rate" in p["caption"].lower() for p in rated))

    def test_no_fabricated_customer_success_or_guarantee(self):
        for row in self.posts:
            copy=row["caption"]
            for marker in (r"\bwe recovered \$",r"\bour customers saved \$",
                           r"\bguaranteed refund\b",r"\bconfirmed customer case\b",
                           r"\bsend us your invoices\b"):
                self.assertNotRegex(copy.lower(),marker)
            self.assertNotIn("/api/inquiry",copy)

    def test_illustrative_detention_disclosure_remains_explicit(self):
        sample=[p for p in self.posts if "08:30" in p["caption"]]
        self.assertEqual(len(sample),2)
        for row in sample:
            text=row["caption"]
            self.assertIn("ILLUSTRATIVE",text)
            self.assertIn("NOT A CUSTOMER RESULT",text)
            self.assertIn("11:00",text)
            self.assertIn("120",text)
            self.assertIn("60",text)
            self.assertNotRegex(text,r"(?i)we recovered.*\d")

    def test_instagram_does_not_assume_a_verified_profile_bio_link(self):
        for row in self.posts:
            if row["network"]!="instagram":continue
            self.assertNotRegex(row["caption"].lower(),
                                r"(?i)link in (?:our |the )?bio")
            self.assertNotIn("utm_campaign=",row["caption"])
            self.assertNotIn("https://",row["caption"])

    def test_amended_preexisting_facebook_post_scope_is_exact(self):
        changes=self.receipt["amended_existing_posts"]
        self.assertEqual(len(changes),3)
        self.assertEqual([x["scheduled_local"][:10] for x in changes],
                         ["2026-11-10","2026-11-17","2026-12-07"])
        uuids=set()
        for entry in changes:
            self.assertEqual(entry["network"],"facebook")
            self.assertTrue(entry["automatic_publish"])
            self.assertFalse(entry["draft"])
            self.assertGreaterEqual(entry["original_media_count"],1)
            self.assertNotIn(entry["uuid"],uuids)
            uuids.add(entry["uuid"])
            u=urlsplit(entry["current_cta"])
            self.assertEqual(u.hostname,HOST)
            self.assertEqual(u.path,PAGE)
            self.assertEqual(u.fragment,"worksheet")
            self.assertEqual(parse_qs(u.query)["utm_source"],["facebook"])

    def test_manifest_state_not_mistaken_for_public_delivery(self):
        self.assertEqual(self.receipt["status"],
                         "PLANNER_ONLY_NOT_INDEPENDENT_PUBLISH_PROOF")
        self.assertEqual(self.receipt["metricool_brand_id"],"7322512")
        self.assertTrue(all(x["state"]=="SCHEDULED_NOT_INDEPENDENTLY_PUBLISHED"
                            for x in self.posts))
        self.assertIn("independently dated source records",self.receipt["platform_analytics_not_proof"].lower())
        self.assertIn("LinkedIn",self.receipt["status_of_original_20_drafts"])
        self.assertNotIn("oauth",str(self.receipt).lower())

    def test_no_new_paid_or_unregistered_customer_action(self):
        policy=self.receipt["permission_scope"].lower()
        self.assertIn("no paid spend",policy)
        self.assertIn("customer outreach",policy)
        self.assertIn("business registration",policy)
        self.assertEqual(self.receipt["brand"],"RETALLY")

if __name__=="__main__":
    unittest.main()
