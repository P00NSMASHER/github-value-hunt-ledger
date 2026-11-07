"""Offline proof for the proposed (NOT applied) RETALLY Pages watch paths.

Source: https://developers.cloudflare.com/pages/configuration/build-watch-paths/
This reproduces the documented per-path exclude-before-include decision;
Cloudflare, not this file, is the authoritative implementation. It cannot
establish a live production change or deployment outcome.
"""

from fnmatch import fnmatchcase
import json
from pathlib import Path
import unittest

CANDIDATE = Path(__file__).with_name("cloudflare_build_watch_paths.json")


def would_build(paths, *, commits=1, includes=("*",), excludes=()):
    """Model Cloudflare Pages' documented build-watch decision for test cases.

    Empty file deltas, 3000+ changed files, and 20+ commits bypass path filters.
    The documented '*' wildcard matches path separators, as fnmatchcase does.
    """
    if not paths or len(paths) >= 3000 or commits >= 20:
        return True
    return any(
        not any(fnmatchcase(path, pattern) for pattern in excludes)
        and any(fnmatchcase(path, pattern) for pattern in includes)
        for path in paths
    )


class RetallyWatchPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(CANDIDATE.read_text(encoding="utf-8"))

    def candidate(self, paths, *, commits=1):
        return would_build(
            paths,
            commits=commits,
            includes=self.policy["path_includes"],
            excludes=self.policy["path_excludes"],
        )

    def test_candidate_is_minimal_and_does_not_exclude_unknown_source(self):
        self.assertEqual(self.policy["path_includes"], ["*"])
        self.assertEqual(
            self.policy["path_excludes"],
            ["automation/HUNTER_EFFECTIVENESS.md", "intelligence/scout_queue/*"],
        )
        self.assertEqual(len(self.policy), 2)

    def test_source_verified_hunter_only_delta_would_skip_build(self):
        # Files confirmed by native compare of 6086324...e901cf7, 2026-11-06.
        delta = [
            "automation/HUNTER_EFFECTIVENESS.md",
            "intelligence/scout_queue/HUNTER-02.json",
            "intelligence/scout_queue/HUNTER-03.json",
        ]
        self.assertTrue(would_build(delta), "Current default triggers redundant builds")
        self.assertFalse(self.candidate(delta), "Candidate must skip research-only changes")

    def test_build_sources_and_functions_remain_watched(self):
        protected = [
            "freight/site/index.html", "freight/site/cloudflare_build.py",
            "freight/commercial_terms.py", "freight/synthetic_pilot_bundle.py",
            "recoveryworks/site/build.py", "recoveryworks/site/index.html",
            "functions/api/inquiry.js", "functions/api/internal/inquiry-case.js",
            "company_sites/group/enquiry.js", "production/requirements-ci.txt",
            "unexpected/new-dependency.py", "README.md",
        ]
        for path in protected:
            with self.subTest(path=path):
                self.assertTrue(self.candidate([path]))

    def test_mixed_research_and_site_code_changes_still_build(self):
        self.assertTrue(self.candidate([
            "intelligence/scout_queue/HUNTER-01.json",
            "functions/api/inquiry.js",
        ]))
        self.assertTrue(self.candidate([
            "automation/HUNTER_EFFECTIVENESS.md",
            "freight/site/cloudflare_build.py",
        ]))

    def test_unrelated_automation_is_not_hidden(self):
        self.assertTrue(self.candidate(["automation/new_runtime.py"]))
        self.assertTrue(self.candidate(["intelligence/renderer.py"]))

    def test_vendor_bypass_guards_do_not_silently_skip(self):
        self.assertTrue(self.candidate([]))
        self.assertTrue(self.candidate(["intelligence/scout_queue/HUNTER-01.json"], commits=20))
        self.assertTrue(self.candidate(["intelligence/scout_queue/HUNTER-01.json"] * 3000))
        self.assertFalse(self.candidate(["intelligence/scout_queue/HUNTER-01.json"], commits=1))


if __name__ == "__main__":
    unittest.main()
