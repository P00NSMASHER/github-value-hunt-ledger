"""Read-only, offline February RETALLY social creative release controls.

Validates proposed organic posts without posting or touching accounts.
A prepared/scheduled post never establishes delivery, public reach or leads.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from collections import Counter
import json
import re
import unittest

ROOT=Path(__file__).resolve().parent
SITE=ROOT.parents[2]/"site"
SOURCE=ROOT/"feb2027-organic-fieldnotes-plan.json"
REQUIRED_TOPICS={
  "invoice_identity", "rebill_or_duplicate", "liftgate_trigger",
  "fuel_index_window", "free_audit_terms", "dispute_packet",
  "private_records", "net_credit_status",
}
DATES=[
 ("2027-02-02","facebook"),("2027-02-03","instagram"),
 ("2027-02-04","facebook"),("2027-02-05","instagram"),
 ("2027-02-09","facebook"),("2027-02-10","instagram"),
 ("2027-02-11","facebook"),("2027-02-12","instagram"),
 ("2027-02-16","facebook"),("2027-02-17","instagram"),
 ("2027-02-18","facebook"),("2027-02-19","instagram"),
 ("2027-02-23","facebook"),("2027-02-24","instagram"),
 ("2027-02-25","facebook"),("2027-02-26","instagram"),
]
MEDIA_HINTS={
 "invoice_identity":re.compile(r"invoice|freight|overcharge",re.I),
 "rebill_or_duplicate":re.compile(r"invoice|duplicate|corrected",re.I),
 "liftgate_trigger":re.compile(r"liftgate",re.I),
 "fuel_index_window":re.compile(r"rate|sheet|version",re.I),
 "free_audit_terms":re.compile(r"upfront|audit|fee|pricing",re.I),
 "dispute_packet":re.compile(r"evidence|methodology|audit|authority|rate",re.I),
 "private_records":re.compile(r"secure|inquiry|privacy|records|transfer",re.I),
 "net_credit_status":re.compile(r"credit|approval|funds|ledger",re.I),
}

class FebruaryEditorialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.rows=cls.doc["posts"]

    def test_exact_slots_and_audiences(self):
        self.assertEqual(len(self.rows),16)
        self.assertEqual(Counter(x["network"] for x in self.rows),
                         {"facebook":8,"instagram":8})
        self.assertEqual([(p["dateTime"][:10],p["network"]) for p in self.rows],DATES)
        for p in self.rows:
            when=datetime.fromisoformat(p["dateTime"])
            self.assertEqual((when.year,when.month),(2027,2))
            self.assertEqual(when.hour,9 if p["network"]=="facebook" else 10)
            self.assertEqual(when.minute,0)
            self.assertEqual(p["timezone"],"America/New_York")
        self.assertEqual(len({p["network"]+"|"+p["dateTime"] for p in self.rows}),16)

    def test_eight_distinct_buyer_topics(self):
        topics=Counter(p["topic"] for p in self.rows)
        self.assertEqual(set(topics),REQUIRED_TOPICS)
        self.assertTrue(all(n==2 for n in topics.values()))
        self.assertEqual(len({p["text"].splitlines()[0] for p in self.rows}),16)

    def test_prelaunch_authority_never_implicitly_activated(self):
        self.assertEqual(self.doc["brand"],"RETALLY")
        self.assertEqual(self.doc["brandId"],"7322512")
        self.assertIn("not independent proof",self.doc["socialProofBoundary"].lower())
        self.assertTrue(self.doc["existingCalendarUnchanged"])
        self.assertEqual(self.doc["status"],
                         "APPROVED_FOR_METRICOOL_SCHEDULING_NOT_PUBLICATION_RECEIPT")
        self.assertIn("No real customer",self.doc["legalBoundary"])
        for p in self.rows:
            self.assertTrue(p["autoPublish"])
            self.assertFalse(p["draft"])
            self.assertIn("never customer",p["sourceEvidence"])

    def test_facebook_distinct_verified_source_backed_education_routes(self):
        routed=set()
        for p in self.rows:
            if p["network"]!="facebook":
                continue
            urls=re.findall(r"https://[^\s<>()]+",p["text"])
            self.assertEqual(len(urls),1,p["topic"])
            u=urlsplit(urls[0])
            self.assertEqual((u.scheme,u.hostname),("https","www.retallyrecovery.com"))
            self.assertFalse(u.username or u.password or u.port)
            self.assertNotIn("/api/",u.path)
            if u.fragment: self.assertEqual(u.fragment,"worksheet")
            self.assertIn(u.path, {
                "/freight-invoice-audit-checklist",
                "/duplicate-freight-charges",
                "/accessorial-charge-audit",
                "/carrier-rate-audit",
                "/freight-audit-pricing",
                "/freight-overcharge-dispute-process",
                "/privacy",
                "/freight-recovery-evidence-standard",
            })
            self.assertTrue((SITE/(u.path.strip("/")+".html")).is_file())
            q=parse_qs(u.query)
            self.assertEqual(q.get("utm_source"),["facebook"])
            self.assertEqual(q.get("utm_medium"),["organic_social"])
            self.assertEqual(q.get("utm_campaign"),["retally_feb2027_controls"])
            self.assertEqual(q.get("utm_content"),["fb_"+p["topic"]])
            self.assertNotIn(u.path,routed)
            routed.add(u.path)
        self.assertEqual(len(routed),8)

    def test_instagram_no_caption_link_or_unverified_profile_claim(self):
        for p in self.rows:
            if p["network"]!="instagram":continue
            self.assertNotRegex(p["text"],r"https?://")
            self.assertNotRegex(p["text"].lower(),r"link in (our |the )?bio")
            self.assertIn("#RETALLY",p["text"])
            self.assertTrue(p["media"])

    def test_reuse_only_existing_metricool_planner_media_and_alts(self):
        for p in self.rows:
            self.assertEqual(len(p["media"]),len(p["mediaAltText"]))
            self.assertLessEqual(len(p["media"]),4)
            for index,(asset,alt) in enumerate(zip(p["media"],p["mediaAltText"])):
                uri=urlsplit(asset)
                self.assertEqual((uri.scheme,uri.hostname),
                                 ("https","static.metricool.com"))
                self.assertTrue(uri.path.startswith("/planner/202610/7322512-"))
                self.assertTrue(uri.path.endswith((".png",".jpg",".jpeg",".webp")))
                self.assertGreater(len(alt.strip()),25)
                if index==0:
                    self.assertRegex(alt,MEDIA_HINTS[p["topic"]])
            if p["media"]:
                self.assertIsNotNone(p["sourceDay"])
                self.assertIn(p["sourceNetwork"],("facebook","instagram"))

    def test_creative_fatigue_no_exact_same_platform_media_twice_in_feb(self):
        used=set()
        for p in self.rows:
            for asset in p["media"]:
                key=(p["network"],asset)
                self.assertNotIn(key,used,"February must not recycle the same visual twice per channel")
                used.add(key)
        self.assertEqual(
          [(p["topic"],p["network"]) for p in self.rows if not p["media"]],
          [("rebill_or_duplicate","facebook"),("net_credit_status","facebook")]
        )
        self.assertIn("OG previews",self.doc["imagePolicy"])

    def test_no_fake_customer_revenue_recovery_or_clandestine_intake(self):
        forbidden=(
          r"we recovered\s*\$",r"our customers (saved|recovered)\s*\$",
          r"guaranteed (refund|recovery|savings)",
          r"send (us|me) (your )?(invoice|contract|bank)",
          r"refund guaranteed",r"client case study",
        )
        for p in self.rows:
            for pattern in forbidden:
                self.assertNotRegex(p["text"].lower(),pattern,p["topic"])
            self.assertNotIn("/api/inquiry",p["text"])
            self.assertLess(len(p["text"]),2200)
            self.assertGreater(len(p["text"]),250)

    def test_competent_treatment_of_pricing_and_approval(self):
        price=[p for p in self.rows if p["topic"]=="free_audit_terms"]
        recovery=[p for p in self.rows if p["topic"]=="net_credit_status"]
        self.assertEqual(len(price),len(recovery))
        for p in price:
            self.assertIn("$0",p["text"])
            self.assertIn("written",p["text"].lower())
            self.assertRegex(p["text"].lower(),r"not guarantee|not guaranteed|aren.t guaranteed|no recovery is guaranteed|is not a refund promise")
        for p in recovery:
            self.assertIn("reversal",p["text"].lower())

    def test_no_actual_post_publication_or_lead_claims(self):
        self.assertEqual(self.doc["status"],
                         "APPROVED_FOR_METRICOOL_SCHEDULING_NOT_PUBLICATION_RECEIPT")
        self.assertIn("not independent proof",self.doc["socialProofBoundary"].lower())
        self.assertNotIn("qualified_leads",self.doc)
        self.assertNotIn("confirmed_recovered_amount",self.doc)

if __name__=="__main__":
    unittest.main()
