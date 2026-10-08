"""Check historical D-07 offline evidence integrity without claiming CI reran it.

The archived 4.4MB original Unified Lab is in the user's existing Library,
NOT in this repository or CI. These tests check honest metadata boundaries.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).parent


class OriginalD07EvidenceBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads((ROOT/"phase5d_d07_offline_receipt.json").read_text())

    def test_patch_hash_is_exact(self):
        r=self.receipt
        patch=ROOT/"phase5d_d07_original.patch"
        self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(),r["patch_sha256"])
        self.assertIn("previous['actor']==actor",patch.read_text())
        self.assertIn("SELECT kind,payload_json,actor",patch.read_text())

    def test_original_archive_provenance_preserved(self):
        r=self.receipt
        self.assertEqual(r["finding"],"D-07")
        self.assertEqual(r["original_staging_source_sha256"],
                         "36960d9ca245cdd43b61423718aa763102c901cdb8784cd46e5189d9ff7e983c")
        self.assertEqual(r["source_archive_sha256"],
                         "2dcfd16296454689a391fb76ac57e4a9282091c25d85134334b3c7eeeeafc93b")
        self.assertEqual(r["before"]["cross_actor_retry"],
                         "FAILED: unauthorized replay accepted")
        self.assertEqual(r["after"]["cross_actor_retry"],
                         "PASS: IDEMPOTENCY_CONFLICT")
        self.assertEqual(r["legacy_original_suite_on_patched_code"],"62/62 PASS")

    def test_historical_closure_not_overstated(self):
        r=self.receipt
        self.assertEqual(r["status"],"REPAIRED_IN_OFFLINE_RESEARCH_ONLY")
        self.assertEqual(r["original_historical_register_status"],"OPEN_UNVERIFIED")
        self.assertFalse(r["product_handler_production_certified"])
        self.assertFalse(r["external_actor_identity_verified"])
        history=json.loads((ROOT.parent/"research"/"LAB_FINDINGS_CUMULATIVE.json").read_text())
        original=next(x for x in history["entries"] if x["id"]=="D-07")
        self.assertEqual(original["remediation"],"OPEN_UNVERIFIED")
        self.assertEqual(sum(x["remediation"]=="OPEN_UNVERIFIED" for x in history["entries"]),26)


if __name__=="__main__":
    unittest.main()
