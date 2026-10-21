"""Compatibility verifier MUST use complete provider and attachment evidence.

Regression: a previously available 7-GET lightweight Micro checker could
declare zero network ingress after looking at only one VNIC API page and not
examining a second in-flight VNIC attachment. These mock-only tests prove this
entry point can no longer bypass the complete existing checker.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def _module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("required source-locked test module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LIVE = _module("retally_compat_existing_micro", "verify-existing-micro.py")
CASES = _module("retally_strict_micro_fixtures", "test_existing_micro.py")


class CompleteMicroAcceptanceCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.receipt = CASES.fixture()
        self.responses = CASES.replies(self.receipt)
        self.called = []

    def run_checker(self, *, receipt=None):
        def read(*args, region=None, timeout=90):
            self.called.append((args, region))
            if tuple(args[:3]) not in self.responses:
                raise AssertionError("Unknown provider read in strict audit")
            return deepcopy(self.responses[tuple(args[:3])])
        with patch.object(LIVE.STRICT.BASE, "home_region",
                          return_value=self.receipt["home_region"]), \\
             patch.object(LIVE.STRICT.BASE, "cli", side_effect=read):
            return LIVE.audit_existing_micro(
                self.receipt if receipt is None else receipt)

    def test_strict_provider_chain_preserves_legacy_report_with_release_hold(self):
        report = self.run_checker()
        self.assertEqual(report["status"],
                         "OCI_EXISTING_MICRO_NETWORK_AND_BOOT_VERIFIED")
        self.assertEqual(report["boot_gb"], 50)
        self.assertTrue(report["full_placement_and_attachment_audit"])
        self.assertEqual(report["vnic_nsg_count"], 0)
        self.assertEqual(report["oci_write_requests"], 0)
        self.assertIs(report["guest_application_healthy_verified"], False)
        self.assertIs(report["off_device_backup_verified"], False)
        self.assertIs(report["billing_statement_verified"], False)
        self.assertEqual(report["customer_production_release"], "HOLD")
        self.assertEqual(len(self.called), len(self.responses))
        for family in (
            ("compute", "instance", "list-vnics"),
            ("compute", "vnic-attachment", "list"),
            ("compute", "boot-volume-attachment", "list"),
        ):
            queries = [args for args, _ in self.called
                       if tuple(args[:3]) == family]
            self.assertEqual(len(queries), 1, family)
            self.assertIn("--all", queries[0], family)
        for args, region in self.called:
            self.assertIn(args[2], {"get", "list", "list-vnics"})
            self.assertEqual(region, self.receipt["home_region"])

    def test_missing_second_page_or_in_flight_vnic_is_not_certified(self):
        primary = self.responses[("compute", "vnic-attachment", "list")][0]
        for state in ("ATTACHING", "DETACHING", "ATTACHED"):
            with self.subTest(state=state):
                key = ("compute", "vnic-attachment", "list")
                self.responses[key] = [primary, {
                    **primary,
                    "id": "ocid1.vnicattachment.oc1.hidden-second",
                    "vnic-id": "ocid1.vnic.oc1.hidden-second",
                    "lifecycle-state": state,
                }]
                with self.assertRaises(LIVE.BASE.Stop):
                    self.run_checker()
        self.responses[("compute", "vnic-attachment", "list")] = [primary]
        vnics = self.responses[("compute", "instance", "list-vnics")]
        self.responses[("compute", "instance", "list-vnics")] = vnics + [
            {**vnics[0], "id": "ocid1.vnic.oc1.second"}]
        with self.assertRaises(LIVE.BASE.Stop):
            self.run_checker()

    def test_missing_or_modified_full_provider_evidence_fails_closed(self):
        for key, field, value in (
            (("compute", "image", "get"), "operating-system-version", "22.04"),
            (("compute", "instance", "get"), "image-id", "ocid1.image.oc1.other"),
            (("network", "route-table", "get"), "route-rules", []),
            (("network", "internet-gateway", "get"), "is-enabled", False),
            (("network", "security-list", "get"), "ingress-security-rules",
             [{"source": "0.0.0.0/0", "protocol": "all"}]),
        ):
            with self.subTest(key=key, field=field):
                self.responses = CASES.replies(self.receipt)
                self.responses[key][field] = value
                with self.assertRaises(LIVE.BASE.Stop):
                    self.run_checker()

    def test_forged_customer_release_or_missing_full_receipt_is_rejected(self):
        for field, val in (
            ("release_status", "READY"),
            ("production_certified", True),
            ("no_customer_data", False),
            ("no_open_ingress", False),
            ("schema", 0),
        ):
            with self.subTest(field=field):
                changed = {**self.receipt, field: val}
                with self.assertRaises(LIVE.BASE.Stop):
                    self.run_checker(receipt=changed)
        self.assertRaises(ValueError, LIVE.audit_existing_micro,
                          self.receipt, read=lambda *a, **kw: {})

    def test_legacy_verifier_has_no_short_path_bypassing_strict_audit(self):
        with patch.object(LIVE.STRICT, "inspect_running_micro",
                          side_effect=LIVE.BASE.Stop("independent evidence absent")):
            with self.assertRaises(LIVE.BASE.Stop):
                LIVE.audit_existing_micro(self.receipt)


if __name__ == "__main__":
    unittest.main()
