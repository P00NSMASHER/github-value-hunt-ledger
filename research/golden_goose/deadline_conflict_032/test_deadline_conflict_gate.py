import unittest
import json
import pathlib
from deadline_conflict_gate import evaluate, fictional_unit_economics

URL = "https://example.gov/rfp/1"
def item(dt, kind="third_party_headline", url=URL):
    return {"kind":kind, "close_local":dt, "tz":"America/Los_Angeles", "url":url}
def one(*items):
    return {"solicitation_id":"RP 1", "observations":list(items)}

class TestDeadlineConflictGate(unittest.TestCase):
    def test_real_public_mirror_conflict(self):
        path=pathlib.Path(__file__).parent/"sound_transit_rp_0157_26.json"
        result=evaluate(json.loads(path.read_text()))
        self.assertEqual(result["status"],"CONFLICT_REVIEW")
        self.assertEqual(result["distinct_deadlines"],2)
        self.assertEqual(result["local_calendar_gap_days"],14)
        self.assertEqual(result["claim_count"],3)
        self.assertIsNone(result["decision_deadline"])
    def test_identical_dates_still_unverified(self):
        r=evaluate(one(item("2026-11-04 15:00"),item("2026-11-04 15:00")))
        self.assertEqual(r["status"],"UNCONFIRMED_SINGLE_DATE")
        self.assertIsNone(r["decision_deadline"])
    def test_same_day_time_disagreement(self):
        r=evaluate(one(item("2026-11-04 15:00"),item("2026-11-04 15:01")))
        self.assertEqual(r["status"],"CONFLICT_REVIEW")
        self.assertEqual(r["local_calendar_gap_days"],0)
    def test_portal_link_without_content_no_deadline(self):
        o={"kind":"official_agency_portal_link","url":URL,"close_local":None}
        self.assertEqual(evaluate(one(o))["status"],"SOURCE_INSUFFICIENT")
    def test_forged_portal_deadline_refused(self):
        o={"kind":"official_agency_portal_link","url":URL,"close_local":"2026-11-04 15:00"}
        with self.assertRaises(ValueError): evaluate(one(o))
    def test_unparseable_calendar_date(self):
        with self.assertRaises(ValueError): evaluate(one(item("2026-02-30 15:00")))
    def test_unknown_timezone(self):
        o=item("2026-11-04 15:00");o["tz"]="PT"
        with self.assertRaises(ValueError): evaluate(one(o))
    def test_missing_provenance(self):
        o=item("2026-11-04 15:00");o.pop("url")
        with self.assertRaises(ValueError): evaluate(one(o))
    def test_empty_observations(self):
        with self.assertRaises(ValueError): evaluate(one())
    def test_duplicate_mirror_not_separate(self):
        o=item("2026-11-04 15:00")
        self.assertEqual(evaluate(one(o,o,o))["claim_count"],1)
    def test_missing_bid_identity(self):
        with self.assertRaises(ValueError): evaluate({"solicitation_id":"", "observations":[item("2026-11-04 15:00")]})
    def test_fictional_margin_but_no_revenue(self):
        a=fictional_unit_economics()
        self.assertEqual(a["assumed_contribution_per_paid_audit"],"29")
        self.assertEqual(a["verified_revenue"],"0")
        b=fictional_unit_economics(review_minutes=60)
        self.assertEqual(b["assumed_contribution_per_paid_audit"],"-1")
    def test_negative_cost_rejected(self):
        with self.assertRaises(ValueError): fictional_unit_economics(review_minutes=-1)

if __name__=="__main__": unittest.main()
