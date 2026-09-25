import json
import unittest
from pathlib import Path
from rights.rights_registry import load_registry,stage_readiness,validate_registry

ROOT=Path(__file__).resolve().parents[1]

class CanonicalRightsRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_registry(ROOT/"rights"/"RIGHTS_REGISTRY.json")
        cls.by_key={x["subject_key"]:x for x in cls.data["subjects"]}

    def test_registry_valid(self):
        self.assertEqual([],validate_registry(self.data))

    def test_standing_hunter_assertion_never_auto_resolves_scopes(self):
        self.assertTrue(self.data["global_assertions"])
        self.assertTrue(all(a["automatic_scope_effect"] is False for a in self.data["global_assertions"]))

    def test_owner_attestation_does_not_become_executed_permission(self):
        key="emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65"
        row=self.by_key[key]["scopes"]["commercial_use"]
        self.assertEqual("OWNER_ATTESTED",row["evidence_class"])
        self.assertNotEqual("EXECUTED_PERMISSION_VERIFIED",row["evidence_class"])
        self.assertEqual("READY",stage_readiness(self.by_key[key],"CONTROLLED_PILOT")["state"])
        self.assertEqual("BLOCKED",stage_readiness(self.by_key[key],"HOSTED_SAAS")["state"])

    def test_agpl_is_conditional_not_unrestricted(self):
        key="fleetbase/fleetbase@4ff6980c6db6f3e8103b3ec425a089aa6d251af4"
        self.assertEqual("CONDITIONAL",stage_readiness(self.by_key[key],"CONTROLLED_PILOT")["state"])

    def test_freight_manifest_owner_attestations_match_canonical_registry(self):
        legacy=json.loads((ROOT/"freight"/"RIGHTS_EVIDENCE_MANIFEST.json").read_text())
        for entry in legacy["entries"]:
            key=f"{entry['repository']}@{entry['revision']}"
            canonical=self.by_key[key]["scopes"]["commercial_use"]
            self.assertEqual("OWNER_ATTESTED",canonical["evidence_class"])
            self.assertEqual("ALLOWED",canonical["status"])
            self.assertEqual(entry["evidence_sha256"],canonical["evidence_sha256"])

if __name__=="__main__":
    unittest.main()
