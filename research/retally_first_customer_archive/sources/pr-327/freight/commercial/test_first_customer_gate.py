"""Test synthetic gate mechanics; never fabricate real approval evidence."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from first_customer_gate import evaluate, verified

BASE=json.loads((Path(__file__).parent/"first_customer_acceptance_m2g.json").read_text())

class FirstCustomerGateTests(unittest.TestCase):
    def clone(self):
        return copy.deepcopy(BASE)
    def test_baseline_blocks_commercial_intake(self):
        r=evaluate(self.clone())
        self.assertFalse(r["gates"]["contact"]["ready"])
        self.assertFalse(r["gates"]["confidential_pilot"]["ready"])
        self.assertFalse(r["gates"]["claims_recovery"]["ready"])
        self.assertFalse(r["gates"]["sample_publication"]["ready"])
        self.assertFalse(r["all_customer_pilot_gates_ready"])
    def test_claim_without_reviewer_fails(self):
        self.assertFalse(verified({"status":"VERIFIED","evidence_ref":"proof","reviewed_at":"2026-10-08","reviewed_by":""}))
    def test_claim_without_source_fails(self):
        self.assertFalse(verified({"status":"VERIFIED","evidence_ref":"","reviewed_at":"2026-10-08","reviewed_by":"reviewer"}))
    def test_only_evidence_backed_contact_passes(self):
        s=self.clone()
        for name in s["readiness_gates"]["contact"]:
            s["requirements"][name].update(status="VERIFIED",evidence_ref="TEST-FIXTURE",reviewed_by="TEST-REVIEWER",reviewed_at="2026-10-08")
        r=evaluate(s)
        self.assertTrue(r["gates"]["contact"]["ready"])
        self.assertFalse(r["gates"]["confidential_pilot"]["ready"])
    def test_invalid_sample_arithmetic_rejected(self):
        s=self.clone();s["published_synthetic_sample"]["reversals_usd"]="999.00"
        with self.assertRaisesRegex(ValueError,"gross/net"):evaluate(s)
    def test_synthetic_cannot_become_real_claim(self):
        s=self.clone();s["published_synthetic_sample"]["customer_result"]=True
        with self.assertRaisesRegex(ValueError,"synthetic"):evaluate(s)
    def test_mixed_inquiry_status_rejected(self):
        s=self.clone();s["production"]["online_inquiry_status"]="READY"
        with self.assertRaisesRegex(ValueError,"contradicts"):evaluate(s)
    def test_no_approved_rate_blocks_claims(self):
        s=self.clone()
        for name in s["readiness_gates"]["claims_recovery"]:
            s["requirements"][name].update(status="VERIFIED",evidence_ref="TEST-FIXTURE",reviewed_by="TEST-REVIEWER",reviewed_at="2026-10-08")
        r=evaluate(s)
        self.assertIn("approved_actual_contingency_terms",r["gates"]["claims_recovery"]["missing"])
        self.assertFalse(r["gates"]["claims_recovery"]["ready"])

if __name__=="__main__":
    unittest.main()
