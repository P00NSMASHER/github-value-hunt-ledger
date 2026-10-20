"""No-cloud tests for the *existing* Oracle Micro read-only release hold.

Mocking cloud replies is not evidence of a live VM or customer readiness.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "retally_existing_oci_micro_audit", HERE / "check-existing-micro.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def identity(kind):
    return "ocid1." + kind + ".oc1.test-retally-" + kind


def fixture():
    receipt = {
        "schema": 1, "phase": "vm_running",
        "tenancy_id": identity("tenancy"), "home_region": "us-ashburn-1",
        "instance_id": identity("instance"), "vcn_id": identity("vcn"),
        "subnet_id": identity("subnet"),
        "security_list_id": identity("securitylist"),
        "route_table_id": identity("routetable"),
        "internet_gateway_id": identity("internetgateway"),
        "image_id": identity("image"),
        "availability_domain": "Qxxx:US-ASHBURN-AD-1",
        "actual_shape": AUDIT.SHAPE,
        "actual_ram_gb": 1, "boot_gb_requested": 50,
        "production_certified": False, "release_status": "HOLD",
        "no_customer_data": True, "no_open_ingress": True,
    }
    return receipt


def replies(s):
    boot = identity("bootvolume")
    return {
        ("compute", "instance", "get"): {
            "id": s["instance_id"],
            "compartment-id": s["tenancy_id"],
            "display-name": AUDIT.BASE.NAME,
            "lifecycle-state": "RUNNING",
            "shape": AUDIT.SHAPE,
            "availability-domain": s["availability_domain"],
            "image-id": s["image_id"],
            "shape-config": {"memory-in-gbs": 1},
        },
        ("compute", "image", "get"): {
            "id": s["image_id"], "operating-system": "Canonical Ubuntu",
            "operating-system-version": "24.04", "lifecycle-state": "AVAILABLE",
        },
        ("network", "vcn", "get"): {
            "id": s["vcn_id"], "display-name": AUDIT.BASE.VPC_NAME,
            "lifecycle-state": "AVAILABLE",
            "cidr-blocks": [str(AUDIT.BASE.VPC_NETWORK)],
            "default-security-list-id": s["security_list_id"],
            "default-route-table-id": s["route_table_id"],
        },
        ("network", "security-list", "get"): {
            "id": s["security_list_id"], "vcn-id": s["vcn_id"],
            "ingress-security-rules": [],
        },
        ("network", "subnet", "get"): {
            "id": s["subnet_id"], "vcn-id": s["vcn_id"],
            "lifecycle-state": "AVAILABLE",
            "security-list-ids": [s["security_list_id"]],
            "cidr-block": AUDIT.BASE.SUBNET_NETWORK,
        },
        ("compute", "instance", "list-vnics"): [
            {"subnet-id": s["subnet_id"], "nsg-ids": []}
        ],
        ("network", "route-table", "get"): {
            "id": s["route_table_id"], "vcn-id": s["vcn_id"],
            "route-rules": [{
                "destination": "0.0.0.0/0",
                "network-entity-id": s["internet_gateway_id"],
            }],
        },
        ("network", "internet-gateway", "get"): {
            "id": s["internet_gateway_id"], "vcn-id": s["vcn_id"],
            "is-enabled": True,
        },
        ("compute", "boot-volume-attachment", "list"): [{
            "boot-volume-id": boot, "lifecycle-state": "ATTACHED"
        }],
        ("bv", "boot-volume", "get"): {
            "id": boot, "lifecycle-state": "AVAILABLE", "size-in-gbs": 50
        },
    }


def run(s, api):
    commands = []
    def read(*args, region=None, timeout=90):
        commands.append((args, region))
        if args[:3] not in api:
            raise AssertionError("Unexpected provider API operation: " + " ".join(args[:3]))
        return api[args[:3]]
    with patch.object(AUDIT.BASE, "home_region", return_value="us-ashburn-1"), \
         patch.object(AUDIT.BASE, "cli", side_effect=read):
        return AUDIT.inspect_running_micro(s), commands


class ExistingMicroAuditTests(unittest.TestCase):
    def setUp(self):
        self.receipt = fixture()
        self.responses = replies(self.receipt)

    def test_exact_read_only_chain_and_no_customer_release(self):
        report, called = run(self.receipt, self.responses)
        self.assertTrue(report["instance_running"])
        self.assertTrue(report["oci_security_list_zero_ingress"])
        self.assertTrue(report["vm_expected_subnet_and_vnic_verified"])
        self.assertEqual(report["vm_attached_nsg_count"], 0)
        self.assertEqual(report["boot_volume_gb"], 50)
        self.assertEqual(report["customer_release_status"], "HOLD")
        for field in ("commercial_production_certified", "guest_firewall_verified",
                      "off_device_restore_verified", "independent_reviewer_approved",
                      "account_zero_charges_verified"):
            self.assertIs(report[field], False)
        self.assertIsNone(report["app_installed"])
        self.assertEqual(len(called), len(self.responses))
        self.assertTrue(all(args[2] in {"get", "list", "list-vnics"}
                            for args, _ in called))
        self.assertTrue(all(region == "us-ashburn-1" for _, region in called))
        boot_queries = [args for args, _ in called if args[:3] ==
                        ("compute", "boot-volume-attachment", "list")]
        self.assertEqual(len(boot_queries), 1)
        self.assertIn("--availability-domain", boot_queries[0])
        self.assertIn(self.receipt["availability_domain"], boot_queries[0])
        self.assertIn("--compartment-id", boot_queries[0])
        self.assertIn(self.receipt["tenancy_id"], boot_queries[0])
        self.assertIn("--instance-id", boot_queries[0])
        self.assertIn("--all", boot_queries[0], "boot attachment audit must exhaust pages")
        serialized = json.dumps(report)
        self.assertNotIn("ocid1.", serialized)
        self.assertNotIn("10.76.", serialized)

    def test_adversarial_provider_replies_fail_closed(self):
        mutations = [
            (("compute", "instance", "get"), "shape", "VM.Standard.E2.1.Flex"),
            (("compute", "instance", "get"), "lifecycle-state", "STOPPED"),
            (("compute", "instance", "get"), "image-id", identity("image") + "-changed"),
            (("compute", "instance", "get"), "compartment-id", identity("tenancy") + "-other"),
            (("compute", "instance", "get"), "availability-domain", "other-ad"),
            (("compute", "image", "get"), "operating-system-version", "22.04"),
            (("network", "vcn", "get"), "cidr-blocks", ["0.0.0.0/0"]),
            (("network", "security-list", "get"), "ingress-security-rules",
             [{"source": "0.0.0.0/0", "protocol": "all"}]),
            (("network", "subnet", "get"), "security-list-ids", []),
            (("compute", "instance", "list-vnics"), "nsg-ids", [identity("networksecuritygroup")]),
            (("network", "route-table", "get"), "route-rules", []),
            (("network", "internet-gateway", "get"), "is-enabled", False),
            (("compute", "boot-volume-attachment", "list"), "boot-volume-id", "WRONG-BOOT"),
            (("bv", "boot-volume", "get"), "size-in-gbs", 100),
            (("bv", "boot-volume", "get"), "lifecycle-state", "DELETED"),
        ]
        for command, field, value in mutations:
            with self.subTest(command=command, field=field):
                payload = {k: json.loads(json.dumps(v)) for k, v in self.responses.items()}
                if isinstance(payload[command], list):
                    payload[command][0][field] = value
                else:
                    payload[command][field] = value
                with self.assertRaises(AUDIT.BASE.Stop):
                    run(self.receipt, payload)

    def test_two_boot_volumes_duplicate_vnics_and_missing_nsg_fail_closed(self):
        for key, replacement in [
            (("compute", "instance", "list-vnics"),
             [self.responses[("compute", "instance", "list-vnics")][0]] * 2),
            (("compute", "instance", "list-vnics"),
             [{"subnet-id": self.receipt["subnet_id"]}]),
            (("compute", "boot-volume-attachment", "list"),
             self.responses[("compute", "boot-volume-attachment", "list")] * 2),
        ]:
            with self.subTest(key=key):
                api = {k: json.loads(json.dumps(v)) for k, v in self.responses.items()}
                api[key] = replacement
                with self.assertRaises(AUDIT.BASE.Stop):
                    run(self.receipt, api)

    def test_receipt_private_owner_state_and_shape_required(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = Path(temp) / "receipt.json"
            receipt.write_text(json.dumps(self.receipt), encoding="utf-8")
            receipt.chmod(0o600)
            self.assertEqual(AUDIT._read_final_receipt(receipt), self.receipt)
            variants = [
                ("release_status", "GO"),
                ("production_certified", True),
                ("no_customer_data", False),
                ("no_open_ingress", False),
                ("actual_shape", "VM.Standard.E2.1.Flex"),
                ("boot_gb_requested", 100),
                ("phase", "subnet_created"),
                ("tenancy_id", "fake"),
                ("home_region", "invalid-region"),
            ]
            for field, value in variants:
                with self.subTest(field=field):
                    bad = dict(self.receipt)
                    bad[field] = value
                    receipt.write_text(json.dumps(bad), encoding="utf-8")
                    with self.assertRaises(AUDIT.BASE.Stop):
                        AUDIT._read_final_receipt(receipt)
            receipt.write_text(json.dumps(self.receipt), encoding="utf-8")
            receipt.chmod(0o644)
            with self.assertRaises(AUDIT.BASE.Stop):
                AUDIT._read_final_receipt(receipt)
            receipt.chmod(0o600)
            link = Path(temp) / "receipt-link.json"
            link.symlink_to(receipt)
            with self.assertRaises(AUDIT.BASE.Stop):
                AUDIT._read_final_receipt(link)

    def test_provider_inventory_or_home_region_failure_is_hold(self):
        with patch.object(AUDIT.BASE, "home_region", return_value="eu-frankfurt-1"):
            with self.assertRaises(AUDIT.BASE.Stop):
                AUDIT.inspect_running_micro(self.receipt)
        api = {k: json.loads(json.dumps(v)) for k, v in self.responses.items()}
        del api[("network", "security-list", "get")]
        with self.assertRaises(AssertionError):
            run(self.receipt, api)


if __name__ == "__main__":
    unittest.main()
