"""Test synthetic gate mechanics; never fabricate real approval evidence."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from first_customer_gate import evaluate, evaluate_zero_spend_profile, verified

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

    def test_zero_spend_public_manual_profile_is_ready_without_blocked_subsystems(self):
        result=evaluate(self.clone())
        profile=result["zero_spend_public_manual_profile"]
        self.assertTrue(profile["ready"])
        self.assertEqual(profile["decision"],"GO_EXISTING_ALREADY_LIVE")
        self.assertTrue(all(profile["checks"].values()))
        self.assertFalse(profile["customer_kickoff_authorized"])
        self.assertFalse(profile["financial_operations_authorized"])
        self.assertTrue(profile["blocked_subsystems_are_not_bypassed"])

    def test_zero_spend_profile_fails_if_any_automated_or_money_surface_is_removed_from_hold(self):
        cases=(
            lambda s:s["production"]["inquiry_get_body"].update(online=True),
            lambda s:s["zero_spend_launch_profile"].update(
                new_external_spend_authorized_usd="1.00"),
            lambda s:s["zero_spend_launch_profile"]["prohibited_capabilities"].remove(
                "provider_financial_event_ingestion"),
            lambda s:s["zero_spend_launch_profile"].update(
                customer_service_authorized=True),
            lambda s:s["zero_spend_launch_profile"].update(
                financial_operations_authorized=True),
        )
        for mutate in cases:
            with self.subTest(mutate=mutate):
                snapshot=self.clone()
                mutate(snapshot)
                self.assertFalse(evaluate_zero_spend_profile(snapshot)["ready"])
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
    def test_synthetic_verification_strings_never_authorize_real_pilot(self):
        s=self.clone()
        for item in s["requirements"].values():
            item.update(status="VERIFIED",evidence_ref="TEST-FIXTURE",
                        reviewed_by="MOCK-REVIEWER",reviewed_at="2026-10-14")
        s["founding_offer"]["actual_contingency_rate"]="0.30"
        # A forged release label is still just a string in source-only JSON.
        s["release_policy"]="PRETEND_ALL_CUSTOMERS_AUTHORIZED"
        result=evaluate(s)
        self.assertTrue(result["gates"]["confidential_pilot"]["declared_fields_complete"])
        self.assertFalse(result["gates"]["confidential_pilot"]["ready"])
        self.assertFalse(result["gates"]["qualified_proposal"]["ready"])
        self.assertFalse(result["gates"]["claims_recovery"]["ready"])
        self.assertFalse(result["gates"]["sample_publication"]["ready"])
        self.assertFalse(result["all_customer_pilot_gates_ready"])
        self.assertFalse(result["customer_kickoff_authorized"])
        self.assertFalse(result["actual_financial_operations_authorized"])
        self.assertTrue(result["source_only_not_external_attestation"])
        for stage in ("qualified_proposal","confidential_pilot","claims_recovery","sample_publication"):
            self.assertIn("independent_out_of_band_release_approval_required",
                          result["gates"][stage]["missing"])

    def test_ordinary_contact_metadata_can_still_be_reviewed_without_sending(self):
        s=self.clone()
        for name in s["readiness_gates"]["contact"]:
            s["requirements"][name].update(status="VERIFIED",
                evidence_ref="SOURCE-ONLY", reviewed_by="REVIEWER",
                reviewed_at="2026-10-14")
        result=evaluate(s)
        self.assertTrue(result["gates"]["contact"]["ready"])
        self.assertFalse(result["customer_kickoff_authorized"])

    def test_cli_rejects_forged_full_customer_stage(self):
        from tempfile import TemporaryDirectory
        from contextlib import redirect_stdout
        from io import StringIO
        s=self.clone()
        for item in s["requirements"].values():
            item.update(status="VERIFIED",evidence_ref="TEST-FIXTURE",
                        reviewed_by="TEST-REVIEWER",reviewed_at="2026-10-14")
        s["founding_offer"]["actual_contingency_rate"]="0.30"
        # Even a CLI --require flag cannot elevate untrusted source-only data.
        from first_customer_gate import main
        with TemporaryDirectory() as directory:
            path=Path(directory)/"fake.json"
            path.write_text(json.dumps(s))
            for stage in ("qualified_proposal","confidential_pilot",
                          "claims_recovery","sample_publication"):
                with self.subTest(stage=stage),redirect_stdout(StringIO()):
                    import sys
                    prior=sys.argv
                    try:
                        sys.argv=["first_customer_gate.py","--source",str(path),
                                  "--require",stage]
                        self.assertEqual(main(),2)
                    finally:
                        sys.argv=prior

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
