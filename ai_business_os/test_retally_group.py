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


class IdentityTests(unittest.TestCase):
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
