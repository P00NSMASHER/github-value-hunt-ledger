import json
import unittest
from pathlib import Path

from rights.rights_registry import load_registry, stage_readiness

ROOT=Path(__file__).resolve().parents[1]


class CanonicalRightsAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=load_registry(ROOT/"rights"/"RIGHTS_REGISTRY.json")
        cls.by_key={x["subject_key"]:x for x in cls.registry["subjects"]}

    def test_owner_attestation_is_not_executed_permission(self):
        for key in (
            "emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65",
            "kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045",
        ):
            row=self.by_key[key]["scopes"]["commercial_use"]
            self.assertEqual("OWNER_ATTESTED",row["evidence_class"])
            self.assertNotEqual("EXECUTED_PERMISSION_VERIFIED",row["evidence_class"])
            self.assertEqual("READY",stage_readiness(self.by_key[key],"CONTROLLED_PILOT")["state"])

    def test_hosted_and_acquirer_scopes_fail_closed(self):
        key="emoss08/Trenova@95fcf816562025ad9af864ded4a5fce8a555bd65"
        self.assertEqual("BLOCKED",stage_readiness(self.by_key[key],"HOSTED_SAAS")["state"])
        self.assertEqual("BLOCKED",stage_readiness(self.by_key[key],"ACQUIRER_DILIGENCE")["state"])

    def test_legacy_manifest_matches_canonical_owner_attestation_sha(self):
        legacy=json.loads((ROOT/"freight"/"RIGHTS_EVIDENCE_MANIFEST.json").read_text())
        for item in legacy["entries"]:
            key=f"{item['repository']}@{item['revision']}"
            canonical=self.by_key[key]["scopes"]["commercial_use"]
            self.assertEqual(item["evidence_sha256"],canonical["evidence_sha256"])


if __name__=="__main__":
    unittest.main()
