"""Adverse controls for public catalog truth, identity safety and preview output."""

import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from ai_business_os.retally_group import (
    CATALOG_PATH, GroupCatalogError, build_group_view, identity_candidates,
    load_catalog, main, validate_catalog,
)
from ai_business_os.ceo_command_center import CommandCenterOperator
from ai_business_os.production_bridge import ProductionReadBridge
from ai_business_os.test_ceo_command_center import FakeProduction


def _catalog_with_private_source():
    catalog = load_catalog()
    entry = next(row for row in catalog["entries"] if row["id"] == "rehabsignal")
    entry.update({
        "name": "Synthetic private artifact",
        "evidence_status": "PRIVATE_ARTIFACT_DOCUMENTED",
        "sources": [],
        "private_source_refs": [{
            "record_key": "retally-src-20261020-synthetic-handoff",
            "label": 'Synthetic <review> & "handoff"',
            "source_as_of": catalog["as_of"],
            "reviewed_on": catalog["as_of"],
        }],
    })
    return catalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()

    def test_catalog_has_one_recovery_business_and_separate_product_families(self):
        view = build_group_view(self.catalog)
        self.assertEqual(7, view["totals"]["initial_recovery_services"])
        self.assertEqual(11, view["totals"]["expansion_recovery_services"])
        self.assertEqual(1, sum(e["id"] == "retally-recovery" for e in view["entries"]))
        self.assertEqual({"sheetharbor", "app-factory-products", "x402-services"},
                         {e["id"] for e in view["entries"] if e["kind"] == "product_family"})

    def test_no_internal_human_reviews_keeps_automated_quality_and_no_authority(self):
        quality = next(v for v in self.catalog["workflow"] if v["id"] == "quality-reviewed")
        self.assertEqual("AUTOMATED_QUALITY_GATE", quality["owner_role"])
        self.assertTrue(any("automated" in v.lower() for v in quality["required_evidence"]))
        self.assertTrue(any("source" in v.lower() for v in quality["required_evidence"]))
        self.assertIs(self.catalog["authority"]["internal_human_review_required"], False)
        self.assertEqual("AUTOMATED_EVIDENCE_QA",
                         self.catalog["authority"]["internal_quality_gate"])
        self.assertFalse(self.catalog["authority"]["production_state_mutation_authorized"])

    def test_current_and_future_human_review_requirement_rejected(self):
        for role, evidence in (
            ("INDEPENDENT_REVIEWER", ["Owner acceptance", "Independent approval"]),
            ("OWNER_QUALITY_ASSURANCE", ["Current source version", "Resolved material defects"]),
            ("AUTOMATED_QUALITY_GATE", ["Owner acceptance required", "Automated tests"]),
            ("AUTOMATED_QUALITY_GATE", ["Independent reviewer approval", "Automated tests"]),
        ):
            with self.subTest(role=role, evidence=evidence):
                changed = copy.deepcopy(self.catalog)
                quality = next(v for v in changed["workflow"] if v["id"] == "quality-reviewed")
                quality["owner_role"], quality["required_evidence"] = role, evidence
                with self.assertRaises(GroupCatalogError):
                    validate_catalog(changed)

    def test_automatic_review_policy_cannot_be_weakened(self):
        for field, value in (
            ("internal_human_review_required", True),
            ("internal_human_review_required", "false"),
            ("internal_human_review_required", None),
            ("internal_quality_gate", "HUMAN_QA"),
            ("internal_quality_gate", None),
        ):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.catalog)
                changed["authority"][field] = value
                with self.assertRaises(GroupCatalogError):
                    validate_catalog(changed)

    def test_unconnected_metrics_stay_unknown(self):
        view = build_group_view(self.catalog)
        self.assertTrue(all(v is None for v in view["financial_metrics"].values()))
        for forged in (0, 100, "0", False, {"USD": 0}):
            with self.subTest(forged=forged):
                changed = copy.deepcopy(self.catalog)
                changed["financial_metrics"]["cash_collected"] = forged
                with self.assertRaisesRegex(GroupCatalogError, "must be null"):
                    build_group_view(changed)

    def test_authority_flags_require_false_booleans(self):
        for forged in ("false", 0, None, [], True):
            with self.subTest(forged=forged):
                changed = copy.deepcopy(self.catalog)
                changed["authority"]["external_actions_authorized"] = forged
                with self.assertRaises(GroupCatalogError):
                    validate_catalog(changed)

    def test_preview_cannot_claim_live_finance_registration_or_rebrand(self):
        for section, key, value in (
            ("boundaries", "live_customer_state", "CONNECTED"),
            ("boundaries", "legal_identity", "VERIFIED"),
            ("boundaries", "public_brand_rollout", "LIVE"),
            ("boundaries", "new_external_spend_cents", 1),
            ("boundaries", "new_external_spend_cents", False),
            ("authority", "production_state_mutation_authorized", True),
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.catalog)
                changed[section][key] = value
                with self.assertRaises(GroupCatalogError):
                    validate_catalog(changed)

    def test_duplicate_business_ids_and_cross_business_aliases_are_rejected(self):
        changed = copy.deepcopy(self.catalog)
        changed["entries"].append(copy.deepcopy(changed["entries"][0]))
        with self.assertRaisesRegex(GroupCatalogError, "duplicate entry"):
            validate_catalog(changed)
        changed = copy.deepcopy(self.catalog)
        changed["entries"][1]["candidate_production_slugs"].append("retally")
        with self.assertRaisesRegex(GroupCatalogError, "multiple catalog entries"):
            validate_catalog(changed)

    def test_missing_source_and_future_source_cannot_be_repository_evidence(self):
        changed = copy.deepcopy(self.catalog)
        changed["entries"][0]["sources"] = []
        with self.assertRaisesRegex(GroupCatalogError, "needs a source"):
            validate_catalog(changed)
        changed = copy.deepcopy(self.catalog)
        changed["entries"][0]["sources"][0]["observed_on"] = "2099-01-01"
        with self.assertRaisesRegex(GroupCatalogError, "later than"):
            validate_catalog(changed)

    def test_source_url_does_not_allow_script_credentials_or_other_hosts(self):
        for url in ("javascript:alert(1)", "http://github.com/P00NSMASHER/test",
                    "https://github.com.evil.invalid/P00NSMASHER/test",
                    "https://user@github.com/P00NSMASHER/test",
                    "https://github.com/P00NSMASHER/\\evil",
                    "https://github.com/P00NSMASHER/test\n"):
            with self.subTest(url=url):
                changed = copy.deepcopy(self.catalog)
                changed["entries"][0]["sources"][0]["url"] = url
                with self.assertRaises(GroupCatalogError):
                    validate_catalog(changed)

    def test_string_false_cannot_promote_recovery_expansion_service(self):
        changed = copy.deepcopy(self.catalog)
        changed["services"][-1]["initial_rollout"] = "false"
        with self.assertRaisesRegex(GroupCatalogError, "Boolean"):
            validate_catalog(changed)

    def test_recovery_services_do_not_become_ready_from_catalog_entry(self):
        changed = copy.deepcopy(self.catalog)
        changed["services"][0]["commercial_readiness"] = "READY"
        with self.assertRaisesRegex(GroupCatalogError, "readiness"):
            validate_catalog(changed)

    def test_future_work_cannot_self_declare_complete(self):
        changed = copy.deepcopy(self.catalog)
        changed["priorities"][0]["status"] = "COMPLETE"
        with self.assertRaisesRegex(GroupCatalogError, "self-declare"):
            validate_catalog(changed)

    def test_critical_quality_delivery_stages_cannot_be_removed(self):
        changed = copy.deepcopy(self.catalog)
        changed["workflow"] = [w for w in changed["workflow"] if w["id"] != "quality-reviewed"]
        with self.assertRaisesRegex(GroupCatalogError, "stages"):
            validate_catalog(changed)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"catalog_version": 1, "catalog_version": 2}')
            with self.assertRaisesRegex(GroupCatalogError, "duplicate JSON key"):
                load_catalog(path)

    def test_view_is_detached_and_repeatable(self):
        original = copy.deepcopy(self.catalog)
        a, b = build_group_view(self.catalog), build_group_view(self.catalog)
        self.assertEqual(a, b)
        a["entries"][0]["name"] = "changed output"
        self.assertEqual(original, self.catalog)

    def test_public_projection_rejects_unexpected_private_payloads_at_every_level(self):
        targets = (
            (), ("entries", 0), ("entries", 0, "sources", 0), ("divisions", 0),
            ("services", 0), ("shared_systems", 0), ("workflow", 0),
            ("priorities", 0), ("boundaries",), ("authority",), ("exclusions", 0),
        )
        for path in targets:
            with self.subTest(path=path):
                changed = copy.deepcopy(self.catalog)
                target = changed
                for part in path:
                    target = target[part]
                target["private_customer_records"] = [{"private_contact_ref": "private:example"}]
                with self.assertRaisesRegex(GroupCatalogError, "unexpected fields"):
                    build_group_view(changed)


class PrivateSourceTests(unittest.TestCase):
    def setUp(self):
        self.catalog = _catalog_with_private_source()
        self.entry = next(row for row in self.catalog["entries"] if row["id"] == "rehabsignal")

    def test_private_evidence_needs_a_nonempty_reference_list(self):
        for refs in (None, [], "private-file", {}):
            with self.subTest(refs=refs):
                changed = copy.deepcopy(self.catalog)
                entry = next(row for row in changed["entries"] if row["id"] == "rehabsignal")
                if refs is None:
                    entry.pop("private_source_refs")
                else:
                    entry["private_source_refs"] = refs
                with self.assertRaises(GroupCatalogError):
                    validate_catalog(changed)

    def test_private_reference_dates_are_ordered_and_canonical(self):
        for source_date, review_date, message in (
            ("2000-01-02", "2000-01-01", "later than its review"),
            (self.catalog["as_of"], "2099-01-01", "catalog snapshot"),
            ("not-a-date", self.catalog["as_of"], "ISO date"),
            (self.catalog["as_of"], "20990101", "YYYY-MM-DD"),
        ):
            with self.subTest(source_date=source_date, review_date=review_date):
                self.entry["private_source_refs"][0].update({
                    "source_as_of": source_date, "reviewed_on": review_date,
                })
                with self.assertRaisesRegex(GroupCatalogError, message):
                    validate_catalog(self.catalog)

    def test_private_record_keys_are_bounded_public_review_keys(self):
        prefix = "retally-src-20261020-"
        for key in ("file-private-123", "https://private.invalid/file",
                    "retally-src-2026102-handoff", "retally-src-20261020-Handoff",
                    prefix, prefix + "a" * (101 - len(prefix))):
            with self.subTest(key=key):
                self.entry["private_source_refs"][0]["record_key"] = key
                with self.assertRaisesRegex(GroupCatalogError, "record key"):
                    validate_catalog(self.catalog)
        self.entry["private_source_refs"][0]["record_key"] = prefix + "a" * (100 - len(prefix))
        validate_catalog(self.catalog)

    def test_private_labels_require_nonempty_printable_text(self):
        for label in ("", " ", "handoff\nprivate-data", "handoff\x00", "handoff\u202e"):
            with self.subTest(label=label):
                self.entry["private_source_refs"][0]["label"] = label
                with self.assertRaisesRegex(GroupCatalogError, "label"):
                    validate_catalog(self.catalog)

    def test_private_references_reject_provider_ids_urls_and_missing_fields(self):
        for field, value in (
            ("file_id", "file-private-123"), ("private_id", "provider-private-123"),
            ("url", "https://private.invalid/file"), ("uri", "private://file/123"),
        ):
            with self.subTest(field=field):
                ref = self.entry["private_source_refs"][0]
                ref[field] = value
                with self.assertRaisesRegex(GroupCatalogError, "unexpected fields"):
                    validate_catalog(self.catalog)
                ref.pop(field)
        self.entry["private_source_refs"][0].pop("label")
        with self.assertRaisesRegex(GroupCatalogError, "missing required fields"):
            validate_catalog(self.catalog)

    def test_private_record_keys_are_unique_within_and_across_entries(self):
        ref = self.entry["private_source_refs"][0]
        self.entry["private_source_refs"].append(copy.deepcopy(ref))
        with self.assertRaisesRegex(GroupCatalogError, "duplicate private source record key"):
            validate_catalog(self.catalog)
        self.entry["private_source_refs"].pop()
        self.catalog["entries"][0]["private_source_refs"] = [copy.deepcopy(ref)]
        with self.assertRaisesRegex(GroupCatalogError, "duplicate private source record key"):
            validate_catalog(self.catalog)

    def test_context_only_cannot_carry_even_empty_private_references(self):
        self.entry["evidence_status"] = "CONTEXT_ONLY"
        for refs in (self.entry["private_source_refs"], []):
            with self.subTest(refs=refs):
                self.entry["private_source_refs"] = refs
                with self.assertRaisesRegex(GroupCatalogError, "context-only"):
                    validate_catalog(self.catalog)

    def test_private_evidence_preserves_public_url_and_authority_boundaries(self):
        view = build_group_view(self.catalog)
        self.assertTrue(all(value is None for value in view["financial_metrics"].values()))
        self.assertEqual([], self.entry["sources"])
        for path, value in (
            (("financial_metrics", "cash_collected"), 0),
            (("boundaries", "legal_identity"), "VERIFIED"),
            (("boundaries", "live_customer_state"), "CONNECTED"),
            (("authority", "external_actions_authorized"), True),
            (("authority", "production_state_mutation_authorized"), True),
        ):
            with self.subTest(path=path):
                changed = copy.deepcopy(self.catalog)
                changed[path[0]][path[1]] = value
                with self.assertRaises(GroupCatalogError):
                    validate_catalog(changed)
        self.entry["sources"] = [{
            "label": "Unapproved external reference", "url": "https://private.invalid/source",
            "observed_on": self.catalog["as_of"],
        }]
        with self.assertRaisesRegex(GroupCatalogError, "public owner GitHub"):
            validate_catalog(self.catalog)

    def test_private_evidence_does_not_change_identity_candidates_or_authorize_mutation(self):
        rows = [{"id": "synthetic-business", "slug": "rehabsignal", "name": "private customer name"}]
        original = copy.deepcopy(rows)
        result = identity_candidates(rows, self.catalog)
        self.entry["evidence_status"] = "CONTEXT_ONLY"
        self.entry.pop("private_source_refs")
        self.assertEqual(result, identity_candidates(rows, self.catalog))
        self.assertEqual(original, rows)
        self.assertFalse(result["identity_mutation_authorized"])
        self.assertFalse(result["commercial_readiness_assessed"])
        self.assertNotIn("private customer name", json.dumps(result))

    def test_private_source_rendering_is_escaped_nonclickable_and_not_pending(self):
        from ai_business_os.retally_group_dashboard import render_dashboard
        html = render_dashboard(build_group_view(self.catalog))
        card = html.split("<h3>Synthetic private artifact</h3>", 1)[1].split("</article>", 1)[0]
        self.assertIn("Private source reviewed", card)
        self.assertIn("Synthetic &lt;review&gt; &amp; &quot;handoff&quot;", card)
        self.assertIn("Record retally-src-20261020-synthetic-handoff", card)
        self.assertIn(f'Source as of {self.catalog["as_of"]}', card)
        self.assertIn(f'Reviewed {self.catalog["as_of"]}', card)
        self.assertNotIn("<a ", card)
        self.assertNotIn("Source binding pending", card)

    def test_renderer_escapes_private_keys_and_dates_even_after_projection_tampering(self):
        from ai_business_os.retally_group_dashboard import render_dashboard
        view = build_group_view(self.catalog)
        entry = next(row for row in view["entries"] if row["id"] == "rehabsignal")
        for key in ("record_key", "source_as_of", "reviewed_on"):
            entry["private_source_refs"][0][key] = '<img src=x onerror="bad()">'
        html = render_dashboard(view)
        self.assertNotIn("<img src=x", html)
        self.assertEqual(3, html.count("&lt;img src=x onerror=&quot;bad()&quot;&gt;"))
        for field, value in (("cash_collected", 10), ("paying_customers", 1)):
            view["financial_metrics"][field] = value
            with self.assertRaisesRegex(ValueError, "financial or customer"):
                render_dashboard(view)
            view["financial_metrics"][field] = None
        view["boundaries"]["legal_identity"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "legal, brand, or spending"):
            render_dashboard(view)


class IdentityTests(unittest.TestCase):
    def test_business_identity_scope_reaches_command_center_without_cross_namespace_inference(self):
        result = identity_candidates([
            {"id": "b1", "slug": "capturebrief"},
            {"id": "b2", "slug": "market-surveillance-research"},
            {"id": "b3", "slug": "supplier-desk"},
        ])
        self.assertEqual("ai_business_os_prod.businesses", result["identity_namespace"])
        self.assertEqual("EXACT_CANDIDATE_PRODUCTION_SLUG", result["identity_match_basis"])
        self.assertEqual([{"catalog_id": "capturebrief", "private_record_ids": ["b1"],
                           "reconciliation_required": False}], result["matches"])
        self.assertEqual(2, result["unmapped_record_count"])
        prod = FakeProduction()
        operator = CommandCenterOperator(ProductionReadBridge(prod.read), expected_schema_fingerprint="a" * 64)
        dashboard = operator.dashboard()
        observed = dashboard["retally_group"]["identity_candidates"]
        self.assertEqual(result["identity_namespace"], observed["identity_namespace"])
        self.assertEqual(result["identity_match_basis"], observed["identity_match_basis"])
        self.assertIsNone(dashboard["retally_group"]["private_observation"])
        self.assertNotIn("catalog_source_provenance", observed)
        self.assertEqual([], prod.writes)

    def test_legacy_identity_overlap_requires_reconciliation_and_preserves_ids(self):
        rows = [{"id": "b1", "slug": "freightrecovery", "name": "private name"},
                {"id": "b2", "slug": "recoveryworks", "name": "another private name"}]
        original = copy.deepcopy(rows)
        result = identity_candidates(rows)
        self.assertEqual(original, rows)
        self.assertEqual(["b1", "b2"], result["matches"][0]["private_record_ids"])
        self.assertTrue(result["matches"][0]["reconciliation_required"])
        self.assertFalse(result["identity_mutation_authorized"])
        self.assertNotIn("private name", json.dumps(result))

    def test_unmapped_records_are_counted_without_leaking_private_names(self):
        result = identity_candidates([{"id": "b9", "slug": "unmapped-project", "name": "private-person"}])
        self.assertEqual(1, result["unmapped_record_count"])
        self.assertEqual([], result["matches"])
        self.assertNotIn("private-person", json.dumps(result))
        self.assertNotIn("unmapped-project", json.dumps(result))

    def test_duplicate_private_ids_or_slugs_fail(self):
        for rows in (
            [{"id": "same", "slug": "capturebrief"}, {"id": "same", "slug": "permitplate"}],
            [{"id": "one", "slug": "capturebrief"}, {"id": "two", "slug": "capturebrief"}],
        ):
            with self.assertRaisesRegex(GroupCatalogError, "duplicate private"):
                identity_candidates(rows)

    def test_existing_ceo_dashboard_gains_group_view_without_writes(self):
        prod = FakeProduction()
        operator = CommandCenterOperator(ProductionReadBridge(prod.read), expected_schema_fingerprint="a" * 64)
        result = operator.dashboard()
        self.assertEqual("PLANNING_PREVIEW", result["retally_group"]["catalog"]["mode"])
        matches = result["retally_group"]["identity_candidates"]["matches"]
        self.assertEqual("capturebrief", matches[0]["catalog_id"])
        self.assertEqual(["b2"], matches[0]["private_record_ids"])
        self.assertEqual([], prod.writes)
        self.assertFalse(result["retally_group"]["identity_candidates"]["commercial_readiness_assessed"])


class PreviewTests(unittest.TestCase):
    def test_preview_rejects_non_preview_and_unsupported_financial_numbers(self):
        from ai_business_os.retally_group_dashboard import render_dashboard
        for mutation in ("mode", "metric"):
            view = build_group_view()
            if mutation == "mode":
                view["mode"] = "LIVE"
            else:
                view["financial_metrics"]["cash_collected"] = 9000
            with self.assertRaises(ValueError):
                render_dashboard(view)

    def test_renderer_escapes_text_and_untrusted_source_links(self):
        from ai_business_os.retally_group_dashboard import render_dashboard
        view = build_group_view()
        view["entries"][0]["name"] = '<img src=x onerror="bad()">'
        view["entries"][0]["sources"][0]["url"] = "javascript:bad()"
        html = render_dashboard(view)
        self.assertNotIn('<img src=x', html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn("&lt;img", html)

    def test_versioned_preview_matches_current_catalog_and_renderer(self):
        from ai_business_os.retally_group_dashboard import render_dashboard
        html = render_dashboard(build_group_view())
        tracked = CATALOG_PATH.with_name("RETALLY_GROUP_DASHBOARD.html").read_bytes()
        self.assertEqual(html.encode("utf-8"), tracked)
        self.assertIn("Automated quality gate", html)
        self.assertNotIn("Owner quality assurance", html)

    def test_render_cli_writes_offline_preview_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview.html"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, main(["render", "--output", str(output)]))
            text = output.read_text(encoding="utf-8")
            self.assertIn("RETALLY", text)
            self.assertNotIn('<script src="http', text)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                main(["render", "--output", str(output)])
            self.assertEqual(before, output.read_bytes())

    def test_empty_register_has_no_customers_or_mutable_provider_state(self):
        folder = CATALOG_PATH.parent
        template = json.loads((folder / "RETALLY_GROUP_CUSTOMER_REGISTER.empty.json").read_text())
        self.assertEqual([], template["accounts"])
        self.assertEqual([], template["engagements"])
        self.assertEqual([], template["referrals"])
        self.assertEqual("ai_business_os_prod_and_approved_private_service_stores", template["storage_authority"])
        schema = json.loads((folder / "RETALLY_GROUP_CUSTOMER_REGISTER.schema.json").read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("payment_status", schema["$defs"]["engagement"]["properties"]["stage"]["enum"])


if __name__ == "__main__":
    unittest.main()
