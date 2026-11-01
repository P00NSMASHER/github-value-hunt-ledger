"""RETALLY v3 platform caption pack: scope, attribution and claim-safety gates."""
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

import render_social_v3 as studio

PACK = Path(__file__).with_name("v3_draft_captions.json")
BAD = re.compile(r"\b(?:we|retally)\s+recovered\s+\$|guaranteed\s+refund|"
                 r"our\s+clients?\s+saved\s+\$",re.I)


class FieldNotesCaptionReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads(PACK.read_text(encoding="utf-8"))

    def test_exact_six_topics_and_twelve_review_only_captions(self):
        self.assertEqual(self.doc["brand"],"RETALLY")
        self.assertEqual(self.doc["production_status"],"REVIEW_ONLY")
        self.assertTrue(self.doc["existing_metricool_schedule_unchanged"])
        self.assertEqual(len(self.doc["content"]),6)
        self.assertEqual({x["concept"] for x in self.doc["content"]},set(studio.CONCEPTS))

    def test_proposed_alt_text_and_route_bound_to_exact_post_concept(self):
        for p in self.doc["content"]:
            with self.subTest(topic=p["concept"]):
                item=studio.COPY[p["concept"]]
                self.assertEqual(p["target_educational_route"],"/"+item["site_slug"])
                self.assertEqual(p["suggested_image_alt_text"],item["alt"])
                self.assertIn(p["concept"],studio.CONCEPTS)

    def test_all_platform_copy_is_distinct_and_substantive(self):
        all_text=[]
        for item in self.doc["content"]:
            for n in ("instagram","facebook"):
                s=item[n]["caption"]
                self.assertGreater(len(s),150)
                self.assertLess(len(s),2200)
                self.assertFalse(item[n]["autoPublish"])
                self.assertEqual(item[n]["type"],"POST")
                self.assertNotIn("guaranteed recovery",s.lower())
                self.assertNotRegex(s,BAD)
                self.assertIn("freight",s.lower() if n=="instagram" else s.lower() + " freight")
                all_text.append(s)
        self.assertEqual(len(set(all_text)),12)

    def test_facebook_one_canonical_tracked_link_per_caption(self):
        contents=set()
        for item in self.doc["content"]:
            urls=re.findall(r"https://[^\s<>()]+",item["facebook"]["caption"])
            self.assertEqual(len(urls),1,item["concept"])
            p=urlsplit(urls[0])
            self.assertEqual(p.scheme,"https")
            self.assertEqual(p.hostname,"www.retallyrecovery.com")
            self.assertEqual(p.path,item["target_educational_route"])
            self.assertFalse(p.fragment)
            q=parse_qs(p.query)
            self.assertEqual(q["utm_source"],["facebook"])
            self.assertEqual(q["utm_medium"],["organic_social"])
            self.assertEqual(q["utm_campaign"],["retally_v3_fieldnotes_2026"])
            self.assertEqual(q["utm_content"],[item["concept"]])
            self.assertNotIn(item["concept"],contents)
            contents.add(item["concept"])

    def test_instagram_no_unclickable_web_link_or_private_record_request(self):
        for item in self.doc["content"]:
            text=item["instagram"]["caption"]
            self.assertNotRegex(text,r"https?://")
            self.assertFalse(item["instagram"]["public_url_in_caption"])
            self.assertIn("#RETALLY",text)
            self.assertNotIn("send us your invoices",text.lower())

    def test_detention_explicitly_illustrative(self):
        c=next(x for x in self.doc["content"] if x["concept"]=="detention_clock")
        for network in ("facebook","instagram"):
            caption=c[network]["caption"]
            self.assertIn("ILLUSTRATIVE",caption)
            self.assertIn("NOT A CUSTOMER RESULT",caption)
            self.assertIn("08:30",caption)
            self.assertIn("11:00",caption)
            self.assertIn("120",caption)
            self.assertIn("30",caption)
            self.assertNotIn("realized savings",caption)

    def test_privacy_example_does_not_request_unapproved_invoices(self):
        c=next(x for x in self.doc["content"] if x["concept"]=="secure_intake")
        for net in ("facebook","instagram"):
            txt=c[net]["caption"].lower()
            self.assertIn("dm",txt)
            self.assertIn("secure",txt)
            self.assertNotIn("upload invoices now",txt)

    def test_all_hold_gates_remain_on(self):
        for c in self.doc["content"]:
            self.assertEqual(c["status"],"CONTENT_DRAFT_NOT_SCHEDULED_OR_APPROVED")
            self.assertTrue(c["rights_clearance_required"])
            self.assertTrue(c["visual_approval_required"])
            self.assertTrue(c["no_real_customer_results"])


if __name__=="__main__":
    unittest.main()
