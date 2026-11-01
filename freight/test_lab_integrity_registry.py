"""Adversarial controls for the cumulative research register itself."""
from copy import deepcopy
import unittest
from freight.lab_integrity.check_registry import validate, read_reports

class RegistryChecks(unittest.TestCase):
    def setUp(self):
        self.ledger,self.donors=read_reports()

    def audit(self, ledger=None, donors=None):
        return validate(ledger if ledger is not None else self.ledger,
                        donors if donors is not None else self.donors)

    def test_known_research_register_passes_without_certifying_product(self):
        self.assertEqual(self.audit(),[])
        self.assertEqual(self.ledger["total_observations"],28)
        self.assertEqual(self.ledger["open_unrepaired_historical"],26)
        self.assertEqual(self.donors["code_copied_into_recoveryos"],False)

    def test_missing_historical_finding_fails(self):
        x=deepcopy(self.ledger);x["items"]=[a for a in x["items"] if a["id"]!="D-01"]
        self.assertTrue(any("HISTORICAL_FINDINGS_DISAPPEARED" in s for s in self.audit(ledger=x)))

    def test_duplicates_fail(self):
        x=deepcopy(self.ledger);x["items"].append(deepcopy(x["items"][0]))
        self.assertIn("DUPLICATE_OR_INVALID_FINDING_ID",self.audit(ledger=x))

    def test_unverified_fixed_status_fails(self):
        x=deepcopy(self.ledger);x["items"][0]["remediation"]="FIXED"
        self.assertTrue(any("UNVERIFIED_FIXED_FINDING" in s for s in self.audit(ledger=x)))

    def test_unfounded_production_exploit_assertion_fails(self):
        x=deepcopy(self.ledger);x["items"][0]["production_impact"]="CONFIRMED"
        self.assertTrue(any("UNSUPPORTED_PRODUCTION_VULNERABILITY_CLAIM" in s for s in self.audit(ledger=x)))

    def test_forced_code_installation_claim_fails(self):
        y=deepcopy(self.donors);y["code_copied_into_recoveryos"]=True
        self.assertIn("UNSUPPORTED_CODE_DEPLOYMENT_CLAIM",self.audit(donors=y))

    def test_unpinned_hunt_revision_fails(self):
        y=deepcopy(self.donors);y["candidates"][0]["revision"]="main"
        self.assertTrue(any("DONOR_REVISION_NOT_PINNED" in s for s in self.audit(donors=y)))

    def test_unknown_license_fails(self):
        y=deepcopy(self.donors);y["candidates"][0]["license"]="UNKNOWN"
        self.assertTrue(any("DONOR_LICENSE_UNVERIFIED" in s for s in self.audit(donors=y)))

    def test_empty_findings_fail(self):
        x=deepcopy(self.ledger);x["items"]=[]
        self.assertEqual(self.audit(ledger=x),["CUMULATIVE_REGISTER_EMPTY"])

    def test_cluster_count_tamper_fails(self):
        x=deepcopy(self.ledger);x["cluster_counts"]["source-entitlement"]=0
        self.assertIn("ROOT_CAUSE_CLUSTER_COUNTS_DIFFER",self.audit(ledger=x))

if __name__=="__main__":unittest.main()
