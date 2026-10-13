"""Exact post-creation readback, without conflating planner status with delivery."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from datetime import datetime
import json
import unittest

ROOT=Path(__file__).resolve().parent
PLAN=json.loads((ROOT/"feb2027-organic-fieldnotes-plan.json").read_text(encoding="utf-8"))
RECEIPT=json.loads((ROOT/"observations"/"retally-feb2027-queue-readback-20261013.json").read_text(encoding="utf-8"))

class FebruaryPlannerReceiptTest(unittest.TestCase):
    def test_live_planner_readback_contains_every_planned_network_topic(self):
        plan=PLAN["posts"]
        got=RECEIPT["posts"]
        self.assertEqual(RECEIPT["count"],16)
        self.assertEqual(len(got),len(plan))
        self.assertEqual(Counter(x["network"] for x in got),
                         {"facebook":8,"instagram":8})
        keys={(x["topic"],x["network"]):x for x in got}
        self.assertEqual(len(keys),16)
        for p in plan:
            key=(p["topic"],p["network"])
            self.assertIn(key,keys)
            q=keys[key]
            self.assertEqual(q["dateTime"],p["dateTime"])
            self.assertEqual(q["timezone"],p["timezone"])
            self.assertEqual(q["mediaCount"],len(p["media"]))
            self.assertEqual(q["captionMatchesPlan"],True)
            self.assertEqual(q["altMatchesPlan"],True)
            self.assertEqual(q["mediaMatchesPlan"],True)

    def test_all_explicitly_auto_scheduled_without_provider_error(self):
        for row in RECEIPT["posts"]:
            self.assertTrue(row["autoPublish"])
            self.assertFalse(row["draft"])
            self.assertEqual(row["observedState"],"SCHEDULED_NOT_VERIFIED_PUBLIC")
            self.assertTrue(row["idAtReceipt"].isdigit())
            self.assertTrue(bool(row["uuid"]))
            self.assertIsInstance(row["providerStatus"],list)
            self.assertFalse(any(v in {"FAILED","ERROR","REJECTED"} for v in row["providerStatus"]))
        self.assertEqual(len({x["uuid"] for x in RECEIPT["posts"]}),16)

    def test_exposure_policy_explicitly_unknown_until_independently_proven(self):
        self.assertEqual(RECEIPT["independentlyPublishedProven"],0)
        self.assertEqual(RECEIPT["qualifiedLeadsProven"],0)
        self.assertEqual(RECEIPT["recoveriesProven"],0)
        self.assertIn("no post-publishing/permalink evidence",RECEIPT["evidence"].lower())
        self.assertTrue(RECEIPT["networkReadOnly"])
        self.assertEqual(RECEIPT["brandId"],"7322512")

    def test_local_times_and_numeric_ids_do_not_substitute_as_social_receipt(self):
        for item in RECEIPT["posts"]:
            ts=datetime.fromisoformat(item["dateTime"])
            self.assertEqual(ts.year,2027)
            self.assertEqual(ts.month,2)
            self.assertEqual(item["timezone"],"America/New_York")
            self.assertFalse(item.get("public_perma_link"))
            self.assertFalse(item.get("carrier_customer"))
            self.assertFalse(item.get("actual_savings"))
        self.assertIn("Facebook text-first link posts",RECEIPT["notes"])

if __name__=="__main__":
    unittest.main()
