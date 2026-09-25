import unittest

from build_portfolio_snapshot import build_snapshot, classify_paths, render_markdown, summarize_tree


class SnapshotTests(unittest.TestCase):
    def test_classify_paths(self):
        result = classify_paths([
            ".github/workflows/ci.yml",
            "tests/test_api.py",
            "src/widget.test.js",
            "requirements-ci.txt",
            "package.json",
            "README.md",
            "src/app.py",
        ])
        self.assertEqual(result["workflow_paths"], [".github/workflows/ci.yml"])
        self.assertIn("tests/test_api.py", result["test_paths"])
        self.assertIn("src/widget.test.js", result["test_paths"])
        self.assertEqual(
            result["dependency_manifest_paths"],
            ["package.json", "requirements-ci.txt"],
        )
        self.assertEqual(result["readme_paths"], ["README.md"])

    def test_summarize_tree(self):
        payload = {
            "truncated": False,
            "tree": [
                {"path": "README.md", "type": "blob", "size": 10},
                {"path": "src", "type": "tree"},
                {"path": "src/app.py", "type": "blob", "size": 20},
                {"path": "tests", "type": "tree"},
                {"path": "tests/test_app.py", "type": "blob", "size": 30},
            ],
        }
        result = summarize_tree(payload)
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(result["directory_count"], 2)
        self.assertEqual(result["known_blob_bytes"], 60)
        self.assertEqual(result["top_level_file_counts"], {"(root)": 1, "src": 1, "tests": 1})

    def test_build_snapshot_with_fake_api(self):
        def fake_get(url, token):
            if url.endswith("/repos/acme/demo"):
                return {
                    "default_branch": "main",
                    "visibility": "private",
                    "archived": False,
                    "language": "Python",
                    "size": 7,
                    "updated_at": "2026-09-24T00:00:00Z",
                    "pushed_at": "2026-09-24T00:00:00Z",
                }
            if url.endswith("/repos/acme/demo/branches/main"):
                return {"commit": {"sha": "a" * 40}}
            if "/git/trees/" in url:
                return {"truncated": False, "tree": [{"path": "README.md", "type": "blob", "size": 5}]}
            raise AssertionError(url)

        result = build_snapshot(
            {"repositories": [{"repo_id": "REPO-X", "full_name": "acme/demo", "project_ids": ["PRJ-X"]}]},
            observed_at="2026-09-24T00:00:00Z",
            get_json=fake_get,
        )
        self.assertEqual(result["repository_count_snapshotted"], 1)
        self.assertEqual(result["repository_count_failed"], 0)
        self.assertEqual(result["repositories"][0]["head_sha"], "a" * 40)
        self.assertEqual(result["repositories"][0]["file_count"], 1)

    def test_render_markdown(self):
        snapshot = {
            "observed_at": "2026-09-24T00:00:00Z",
            "repository_count_snapshotted": 1,
            "repository_count_requested": 1,
            "repositories": [{
                "repo_id": "REPO-X",
                "full_name": "acme/demo",
                "head_sha": "a" * 40,
                "file_count": 1,
                "workflow_paths": [],
                "test_paths": [],
                "dependency_manifest_paths": [],
            }],
            "errors": [],
        }
        text = render_markdown(snapshot)
        self.assertIn("acme/demo", text)
        self.assertIn("1 / 1", text)


if __name__ == "__main__":
    unittest.main()
