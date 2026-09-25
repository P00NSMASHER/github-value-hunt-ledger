import unittest

from portfolio_prework.detect_repository_changes import detect_changes, render_markdown


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "observed_at": "2026-09-25T00:00:00Z",
            "repositories": [
                {
                    "repo_id": "REPO-A",
                    "full_name": "acme/unchanged",
                    "default_branch": "main",
                    "head_sha": "a" * 40,
                },
                {
                    "repo_id": "REPO-B",
                    "full_name": "acme/changed",
                    "default_branch": "main",
                    "head_sha": "b" * 40,
                },
            ],
        }

    def fake_get(self, url, token):
        if url.endswith("/repos/acme/unchanged/branches/main"):
            return {"commit": {"sha": "a" * 40}}
        if url.endswith("/repos/acme/changed/branches/main"):
            return {"commit": {"sha": "c" * 40}}
        if "/repos/acme/changed/compare/" in url:
            return {
                "status": "ahead",
                "ahead_by": 2,
                "behind_by": 0,
                "total_commits": 2,
                "files": [
                    {
                        "filename": "src/app.py",
                        "status": "modified",
                        "additions": 4,
                        "deletions": 1,
                        "changes": 5,
                    }
                ],
            }
        raise AssertionError(url)

    def test_unchanged_repo_skips_compare(self):
        calls = []

        def getter(url, token):
            calls.append(url)
            return self.fake_get(url, token)

        result = detect_changes(
            {"observed_at": self.snapshot["observed_at"], "repositories": [self.snapshot["repositories"][0]]},
            observed_at="2026-09-25T01:00:00Z",
            get_json=getter,
        )
        self.assertEqual(result["unchanged_count"], 1)
        self.assertEqual(result["changed_count"], 0)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("/compare/", calls[0])
        self.assertFalse(result["repositories"][0]["requires_deep_inspection"])

    def test_changed_repo_compares_files(self):
        result = detect_changes(
            {"observed_at": self.snapshot["observed_at"], "repositories": [self.snapshot["repositories"][1]]},
            observed_at="2026-09-25T01:00:00Z",
            get_json=self.fake_get,
        )
        item = result["repositories"][0]
        self.assertEqual(item["status"], "CHANGED")
        self.assertTrue(item["requires_deep_inspection"])
        self.assertEqual(item["compare"]["changed_file_count"], 1)
        self.assertEqual(item["compare"]["changed_files"][0]["path"], "src/app.py")

    def test_changed_repo_can_skip_file_compare(self):
        calls = []

        def getter(url, token):
            calls.append(url)
            return self.fake_get(url, token)

        result = detect_changes(
            {"observed_at": self.snapshot["observed_at"], "repositories": [self.snapshot["repositories"][1]]},
            observed_at="2026-09-25T01:00:00Z",
            include_file_deltas=False,
            get_json=getter,
        )
        self.assertEqual(result["changed_count"], 1)
        self.assertIsNone(result["repositories"][0]["compare"])
        self.assertEqual(len(calls), 1)

    def test_errors_are_explicit(self):
        def broken_get(url, token):
            raise RuntimeError("boom")

        result = detect_changes(
            {"observed_at": self.snapshot["observed_at"], "repositories": [self.snapshot["repositories"][0]]},
            observed_at="2026-09-25T01:00:00Z",
            get_json=broken_get,
        )
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["repositories"], [])

    def test_markdown(self):
        delta = detect_changes(
            self.snapshot,
            observed_at="2026-09-25T01:00:00Z",
            get_json=self.fake_get,
        )
        text = render_markdown(delta)
        self.assertIn("acme/changed", text)
        self.assertIn("src/app.py", text)
        self.assertIn("Deep inspection?", text)


if __name__ == "__main__":
    unittest.main()
