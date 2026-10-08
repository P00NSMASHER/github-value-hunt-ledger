"""Scope guard for manually observed Phase 5E unpublished QA revocation repair.

This validates the frozen receipt's internal claims, NOT live Floot state,
and must not substitute for the disposable PostgreSQL regression tests.
"""
from pathlib import Path
import copy
import json
import unittest


def validate_evidence(receipt):
    if receipt.get("schema")!=1 or receipt.get("scope")!="ISOLATED_FLOOT_QA_FINANCIAL_SIGNER_REVOCATION":
        raise ValueError("WRONG_FINANCIAL_EVIDENCE_SCOPE")
    env=receipt["environments"]
    if env["qa"]["postgres_identifier"]==env["production"]["postgres_identifier"]:
        raise ValueError("STAGING_NOT_ISOLATED")
    if env["qa"]["published"] is not False or env["production"]["write_operations"]!=0:
        raise ValueError("PRODUCTION_SAFETY_MISLABELED")
    original=receipt["original_reproduction"]
    repair=receipt["repair"]
    if "HTTP 200" not in original["observed_after_revocation"] or "replay:false" not in original["observed_after_revocation"]:
        raise ValueError("ORIGINAL_DEFECT_EVIDENCE_MISSING")
    if "HTTP 400" not in repair["post_fix_new_record"] or "HTTP 200 replay:true" not in repair["post_fix_original_exact_replay"]:
        raise ValueError("REVOKED_SIGNER_REPAIR_NOT_REPRODUCED")
    if repair["read_only_database_census"]!={"accepted_baseline":1,"rejected_second_case":0}:
        raise ValueError("INVALID_STAGED_DURABILITY")
    if repair["qa_db_trigger_admission_time_checks_present"] is not True:
        raise ValueError("DATABASE_REVOCATION_GUARD_MISSING")
    outstanding=receipt["known_open_gap"]
    if outstanding["defect_status"]!="OPEN_UNMITIGATED" or outstanding["production_impact"]!="NOT_ESTABLISHED":
        raise ValueError("OWNER_SQL_BYPASS_OVERCLAIM")
    if receipt["historical_findings_closed"]!=0 or receipt["historical_findings_open"]!=26:
        raise ValueError("HISTORICAL_REGISTER_OVERCLAIM")
    if receipt["real_customer_recovery_cents"]!=0 or receipt["real_retally_fee_cents"]!=0:
        raise ValueError("FICTIONAL_REVENUE_MISLABELED")
    if receipt["qa_full_production_auth_parity"] is not False or receipt["ci_live_floot_tests"] is not False:
        raise ValueError("LIVE_AUTH_OR_CI_CLAIM_UNSUPPORTED")
    return True


class EvidenceBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads((Path(__file__).parent/"phase5e_revocation_admission_receipt.json").read_text())

    def test_original_failure_and_repair_remain_visible(self):
        self.assertTrue(validate_evidence(self.receipt))

    def test_does_not_hide_direct_sql_bypass(self):
        bad=copy.deepcopy(self.receipt)
        bad["known_open_gap"]["defect_status"]="RESOLVED"
        with self.assertRaisesRegex(ValueError,"OWNER_SQL_BYPASS_OVERCLAIM"):
            validate_evidence(bad)

    def test_real_revenue_remains_zero(self):
        bad=copy.deepcopy(self.receipt)
        bad["real_retally_fee_cents"]=150
        with self.assertRaisesRegex(ValueError,"FICTIONAL_REVENUE_MISLABELED"):
            validate_evidence(bad)

    def test_qa_remains_unpublished(self):
        bad=copy.deepcopy(self.receipt)
        bad["environments"]["qa"]["published"]=True
        with self.assertRaisesRegex(ValueError,"PRODUCTION_SAFETY_MISLABELED"):
            validate_evidence(bad)

    def test_original_26_findings_unclosed(self):
        bad=copy.deepcopy(self.receipt)
        bad["historical_findings_closed"]=1
        with self.assertRaisesRegex(ValueError,"HISTORICAL_REGISTER_OVERCLAIM"):
            validate_evidence(bad)

if __name__=="__main__":
    unittest.main()
