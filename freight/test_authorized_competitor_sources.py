"""Synthetic visibility/privacy contract tests for authorized competitor inventory."""
import json
import unittest

from freight.authorized_competitor_sources import (
    CatalogError, inventory_competitors, summarize_visible_repositories,
)


def row(owner="TraxTechnologies", name="public-parser", *,
        visibility="public", private=None, pull=None):
    if private is None:
        private = visibility == "private"
    data = {
        "full_name": f"{owner}/{name}",
        "owner": {"login": owner},
        "private": private,
        "visibility": visibility,
    }
    if pull is not None:
        data["permissions"] = {"pull": pull}
    return data


class PrivateCompetitorCatalogTests(unittest.TestCase):
    def test_private_repos_are_counted_without_exporting_private_names(self):
        secret = "confidential-carrier-rate-engine"
        rows = [
            row(name="open-source-edi"),
            row(name=secret, visibility="private", pull=True),
            row(name="hidden-user-inventory", visibility="private", pull=False),
            row(name="internal-transfers", visibility="internal", private=True, pull=True),
            row(owner="loop-payments", name="prisma-safety"),
        ]
        report = summarize_visible_repositories(rows, ["TraxTechnologies", "loop-payments"])
        trax, loop = report["organizations"]
        self.assertEqual(trax["visible_public"], 1)
        self.assertEqual(trax["visible_private"], 2)
        self.assertEqual(trax["visible_internal"], 1)
        self.assertEqual(trax["restricted_read_permission_confirmed"], 2)
        self.assertEqual(trax["restricted_read_permission_unverified"], 1)
        self.assertEqual(loop["visible_public"], 1)
        self.assertFalse(report["private_repository_identifiers_exported"])
        self.assertFalse(report["source_code_exported"])
        encoded = json.dumps(report)
        for private_identifier in (secret, "hidden-user-inventory", "internal-transfers"):
            self.assertNotIn(private_identifier, encoded)
        self.assertIn("REUSE_NOT_AUTHORIZED", trax["restricted_source_status"])

    def test_zero_private_visible_does_not_claim_no_private_repos_exist(self):
        report = summarize_visible_repositories([row()], ["TraxTechnologies"])
        self.assertIn("NOT_PROOF_NONE_EXIST",
                      report["organizations"][0]["restricted_source_status"])

    def test_private_visibility_cannot_be_accepted_from_unauthenticated_search(self):
        with self.assertRaisesRegex(CatalogError, "token unavailable"):
            inventory_competitors(["TraxTechnologies"])

    def test_off_scope_private_names_are_never_exported_or_counted(self):
        report = summarize_visible_repositories(
            [row(owner="Unrelated", name="private-secret", visibility="private", pull=True)],
            ["TraxTechnologies"],
        )
        self.assertEqual(report["organizations"][0]["visible_private"], 0)
        self.assertNotIn("Unrelated", json.dumps(report))
        self.assertNotIn("private-secret", json.dumps(report))

    def test_owner_casefolding_matches_github_identity(self):
        report = summarize_visible_repositories(
            [row(owner="traxtechnologies", name="visible")], ["TraxTechnologies"],
        )
        self.assertEqual(report["organizations"][0]["visible_public"], 1)

    def test_missing_restricted_pull_permission_is_not_assumed(self):
        report = summarize_visible_repositories(
            [row(name="recovery-engine", visibility="private")], ["TraxTechnologies"]
        )
        self.assertEqual(report["organizations"][0]["restricted_read_permission_confirmed"], 0)
        self.assertIn("READ_ACCESS_UNVERIFIED",
                      report["organizations"][0]["restricted_source_status"])

    def test_reject_forged_privacy_visibility_conflicts(self):
        for record in (
            row(private=True, visibility="public"),
            row(private=False, visibility="private"),
            row(visibility="mystery"),
        ):
            with self.subTest(record=record["visibility"]):
                with self.assertRaisesRegex(CatalogError, "visibility"):
                    summarize_visible_repositories([record], ["TraxTechnologies"])

    def test_missing_metadata_fails_closed(self):
        for bad in (
            {"full_name": "TraxTechnologies/open", "private": False, "visibility": "public"},
            {"full_name": "Other/open", "owner": {"login": "TraxTechnologies"},
             "private": False, "visibility": "public"},
            "not-a-repository",
        ):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaises(CatalogError):
                    summarize_visible_repositories([bad], ["TraxTechnologies"])

    def test_duplicate_page_rows_are_rejected(self):
        with self.assertRaisesRegex(CatalogError, "duplicate"):
            summarize_visible_repositories([row(), row()], ["TraxTechnologies"])

    def test_empty_or_duplicate_or_invalid_target_scopes_are_blocked(self):
        for scope in ([], ["../Trax"], ["TraxTechnologies", "TRAXTECHNOLOGIES"],
                      ["Trax Technologies"]):
            with self.subTest(scope=scope):
                with self.assertRaises(CatalogError):
                    summarize_visible_repositories([], scope)

    def test_pagination_reads_every_page_until_exhausted(self):
        names = [row(name=f"p-{i}") for i in range(100)]
        calls = []
        def fetch(page):
            calls.append(page)
            return names if page == 1 else [row(name="last")]
        report = inventory_competitors(["TraxTechnologies"], fetch_page=fetch, max_pages=2)
        self.assertEqual(calls, [1, 2])
        self.assertEqual(report["organizations"][0]["visible_public"], 101)

    def test_full_last_page_requires_next_page_or_fails(self):
        names = [row(name=f"p-{i}") for i in range(100)]
        with self.assertRaisesRegex(CatalogError, "incomplete"):
            inventory_competitors(["TraxTechnologies"], fetch_page=lambda page: names,
                                  max_pages=1)

    def test_oversized_page_and_invalid_pagination_fail_closed(self):
        names = [row(name=f"p-{i}") for i in range(101)]
        with self.assertRaisesRegex(CatalogError, "oversized"):
            inventory_competitors(["TraxTechnologies"], fetch_page=lambda page: names)
        with self.assertRaisesRegex(CatalogError, "bound"):
            inventory_competitors(["TraxTechnologies"], fetch_page=lambda page: [],
                                  max_pages=0)

    def test_no_hidden_repos_can_be_inferred_from_catalog_result(self):
        report = inventory_competitors(
            ["TraxTechnologies", "loop-payments"],
            fetch_page=lambda page: [row(name="public")],
        )
        self.assertEqual(report["scope"], "AUTHENTICATED_USER_VISIBLE_REPOSITORIES_ONLY")
        self.assertIn("cannot be inferred", report["visibility_limit"])
        self.assertIn("DOES_NOT_AUTHORIZE", report["reuse_rights"])
        self.assertEqual(report["organizations"][1]["visible_public"], 0)


if __name__ == "__main__":
    unittest.main()
