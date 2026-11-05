import base64
import hashlib
import unittest
from pathlib import Path

from tools.hunter_source_inspection import (
    InspectionError, eligible_path, inspect_candidate, inspect_worker,
)

REV = "a" * 40
TREE = "b" * 40
EXPECTED_CRONS = [
    "7 2,14 * * *", "15 2,14 * * *", "23 2,14 * * *", "31 2,14 * * *",
    "39 2,14 * * *", "47 2,14 * * *", "55 2,14 * * *", "3 3,15 * * *",
    "11 3,15 * * *", "19 3,15 * * *", "27 3,15 * * *", "35 3,15 * * *",
    "43 3,15 * * *", "51 3,15 * * *", "7 4,16 * * *",
]


def blob_id(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class FakeAPI:
    def __init__(self, response):
        self.response = response

    def get(self, path):
        if path not in self.response:
            raise InspectionError("Unexpected source request " + path)
        return self.response[path]


class InspectTests(unittest.TestCase):
    def candidate(self, license_id="MIT"):
        return {"repository": "example/good", "exact_revision": REV,
                "published_license_spdx": license_id,
                "status": "PRE_VERIFICATION_CANDIDATE", "triage_score": 50}

    def api(self, tamper=False):
        src, test = b"def method(x): return x\n", b"def test_method(): assert True\n"
        s, t = blob_id(src), blob_id(test)
        def record(content, sha):
            return {"sha": sha, "encoding": "base64",
                    "content": base64.b64encode(content).decode()}
        return FakeAPI({
            "/repos/example/good/git/commits/" + REV:
                {"sha": REV, "tree": {"sha": TREE}},
            "/repos/example/good/git/trees/" + TREE + "?recursive=1":
                {"sha": TREE, "truncated": False, "tree": [
                    {"path": "src/code.py", "type": "blob", "sha": s, "size": len(src)},
                    {"path": "tests/test_code.py", "type": "blob", "sha": t, "size": len(test)}]},
            "/repos/example/good/git/blobs/" + s:
                record(b"bad bytes" if tamper else src, s),
            "/repos/example/good/git/blobs/" + t: record(test, t),
        })

    def test_real_git_object_hashes_without_code_execution(self):
        evidence = inspect_candidate(self.candidate(), self.api())
        self.assertEqual(evidence["state"], "SOURCE_INSPECTED_NOT_TESTED")
        self.assertEqual(evidence["source_file"]["content_sha256"],
                         hashlib.sha256(b"def method(x): return x\n").hexdigest())
        self.assertFalse(evidence["source_code_executed"])
        self.assertEqual(evidence["measured_result"], "UNKNOWN")

    def test_bad_license_or_source_integrity_fails_closed(self):
        with self.assertRaises(InspectionError):
            inspect_candidate(self.candidate("UNKNOWN"), self.api())
        with self.assertRaises(InspectionError):
            inspect_candidate(self.candidate(), self.api(tamper=True))
        with self.assertRaises(InspectionError):
            inspect_candidate({**self.candidate(), "repository": "https://bad.com"},
                              self.api())

    def test_unsafe_paths_rejected(self):
        self.assertTrue(eligible_path("tests/test_code.py", True))
        self.assertTrue(eligible_path("src/code.py", False))
        self.assertFalse(eligible_path("../secrets.py", False))
        self.assertFalse(eligible_path("vendor/src/tool.py", False))

    def test_worker_cannot_mislabel_candidate_as_completed_work(self):
        worker = {"id": "HUNTER-01", "project": "trading", "mission": "bounded",
                  "target_repository": "owner/target", "evidence_gate": "source"}
        q = {**{"worker_id": worker["id"], "candidate_count": 0, "candidates": []},
             **{k: worker[k] for k in ("project", "mission",
                                      "target_repository", "evidence_gate")}}
        self.assertEqual(inspect_worker(worker, q, self.api())["state"], "NO_CANDIDATES")
        self.assertEqual(inspect_worker(worker, {**q, "mission": "changed"},
                                        self.api())["state"], "INVALID_QUEUE_BINDING")

    def test_all_fifteen_original_cron_expressions_unchanged(self):
        import re
        workflow = Path(".github/workflows/public-repo-hunter.yml").read_text()
        self.assertEqual(re.findall(r'- cron: "([^"]+)"', workflow), EXPECTED_CRONS)
        self.assertIn("candidate-inspection:", workflow)
        self.assertIn("READ_ONLY_INSPECTION_NOT_V16_CLAIM",
                      Path("tools/hunter_source_inspection.py").read_text())


if __name__ == "__main__":
    unittest.main()
