"""Fully offline adversarial tests for read-only live OCI E2 Micro acceptance."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "retally_verified_running_micro", ROOT / "verify-existing-micro.py")
LIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIVE)


def oid(name):
    return "ocid1." + name + ".oc1.synthetic"


class ExistingMicroAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.receipt = {
            "schema": 1, "phase": "vm_running", "release_status": "HOLD",
            "no_customer_data": True, "no_open_ingress": True,
            "actual_shape": "VM.Standard.E2.1.Micro",
            "actual_ram_gb": 1, "boot_gb_requested": 50,
            "home_region": "us-ashburn-1", "availability_domain": "SYNTHETIC:AD-1",
            "instance_id": oid("instance"), "tenancy_id": oid("tenancy"),
            "vcn_id": oid("vcn"), "security_list_id": oid("securitylist"),
            "subnet_id": oid("subnet"),
        }
        r = self.receipt
        self.provider = {
            ("compute", "instance", "get"): {
                "id": r["instance_id"], "display-name": LIVE.BASE.NAME,
                "shape": LIVE.MICRO_SHAPE, "lifecycle-state": "RUNNING",
                "compartment-id": r["tenancy_id"],
                "availability-domain": r["availability_domain"],
                "shape-config": {"memory-in-gbs": 1},
            },
            ("network", "vcn", "get"): {
                "id": r["vcn_id"], "display-name": LIVE.BASE.VPC_NAME,
                "lifecycle-state": "AVAILABLE",
                "default-security-list-id": r["security_list_id"],
            },
            ("network", "security-list", "get"): {
                "id": r["security_list_id"], "vcn-id": r["vcn_id"],
                "ingress-security-rules": [],
            },
            ("network", "subnet", "get"): {
                "id": r["subnet_id"], "vcn-id": r["vcn_id"],
                "lifecycle-state": "AVAILABLE",
                "security-list-ids": [r["security_list_id"]],
            },
            ("compute", "instance", "list-vnics"): [
                {"subnet-id": r["subnet_id"], "nsg-ids": []},
            ],
            ("compute", "boot-volume-attachment", "list"): [
                {"instance-id": r["instance_id"],
                 "boot-volume-id": oid("bootvolume"),
                 "lifecycle-state": "ATTACHED"},
            ],
            ("bv", "boot-volume", "get"): {
                "id": oid("bootvolume"), "size-in-gbs": 50,
                "lifecycle-state": "AVAILABLE",
            },
        }
        self.calls = []

    def read(self, *args, region=None):
        self.calls.append((args, region))
        key = tuple(args[:3])
        if key not in self.provider:
            raise AssertionError("Unexpected OCI operation " + str(key))
        return deepcopy(self.provider[key])

    def check(self):
        return LIVE.audit_existing_micro(deepcopy(self.receipt), read=self.read)

    def test_exact_realistic_micro_passes_but_never_certifies_customer(self):
        result = self.check()
        self.assertEqual(result["status"],
                         "OCI_EXISTING_MICRO_NETWORK_AND_BOOT_VERIFIED")
        self.assertEqual(result["shape"], "VM.Standard.E2.1.Micro")
        self.assertEqual(result["boot_gb"], 50)
        self.assertEqual(result["oci_write_requests"], 0)
        self.assertEqual(result["security_list_ingress"], 0)
        self.assertEqual(result["vnic_nsg_count"], 0)
        self.assertEqual(result["customer_production_release"], "HOLD")
        for flag in ("customer_data_verified_absent",
                     "guest_application_healthy_verified",
                     "host_disk_encryption_verified",
                     "off_device_backup_verified",
                     "billing_statement_verified"):
            self.assertIs(result[flag], False)
        self.assertEqual(len(self.calls), 7)
        for args, region in self.calls:
            self.assertIn(args[2], {"get", "list", "list-vnics"})
            self.assertEqual(region, "us-ashburn-1")

    def test_forged_approval_or_different_shape_is_rejected(self):
        for field, value in (
            ("schema", 2), ("phase", "finished"), ("release_status", "GO"),
            ("no_customer_data", False), ("no_open_ingress", False),
            ("actual_shape", "VM.Standard.E2.1"), ("actual_ram_gb", 8),
            ("boot_gb_requested", 100), ("instance_id", "fake"),
            ("availability_domain", ""), ("tenancy_id", None),
        ):
            with self.subTest(field=field, value=value):
                self.receipt[field] = value
                with self.assertRaises(LIVE.BASE.Stop):
                    self.check()
                self.setUp()

    def test_running_instance_and_resource_identity_required(self):
        mutations = (
            (("compute", "instance", "get"), "shape", "VM.Standard.E3.Flex"),
            (("compute", "instance", "get"), "lifecycle-state", "STOPPED"),
            (("compute", "instance", "get"), "compartment-id", oid("other")),
            (("compute", "instance", "get"), "availability-domain", "elsewhere"),
            (("compute", "instance", "get"), "display-name", "another"),
            (("network", "vcn", "get"), "id", oid("other")),
            (("network", "security-list", "get"), "id", oid("other")),
            (("network", "subnet", "get"), "vcn-id", oid("other")),
            (("bv", "boot-volume", "get"), "size-in-gbs", 60),
            (("bv", "boot-volume", "get"), "lifecycle-state", "FAULTY"),
        )
        for key, field, value in mutations:
            with self.subTest(key=key, field=field):
                self.provider[key][field] = value
                with self.assertRaises(LIVE.BASE.Stop):
                    self.check()
                self.setUp()

    def test_network_or_disk_changes_fail_closed(self):
        for key, change in (
            (("network", "security-list", "get"),
             lambda o: o["ingress-security-rules"].append({"source": "0.0.0.0/0"})),
            (("network", "subnet", "get"),
             lambda o: o["security-list-ids"].append(oid("securitylist2"))),
            (("compute", "instance", "list-vnics"),
             lambda o: o[0]["nsg-ids"].append(oid("networksecuritygroup"))),
            (("compute", "instance", "list-vnics"),
             lambda o: o[0].update({"subnet-id": oid("subnet2")})),
            (("compute", "boot-volume-attachment", "list"),
             lambda o: o.append(deepcopy(o[0]))),
            (("compute", "boot-volume-attachment", "list"),
             lambda o: o[0].update({"lifecycle-state": "DETACHED"})),
            (("bv", "boot-volume", "get"),
             lambda o: o.update({"id": oid("wrongboot")})),
        ):
            with self.subTest(key=key):
                change(self.provider[key])
                with self.assertRaises(LIVE.BASE.Stop):
                    self.check()
                self.setUp()

    def test_wrong_datatypes_and_empty_collections_fail_closed(self):
        for key, changed in (
            (("compute", "instance", "list-vnics"), []),
            (("compute", "instance", "list-vnics"), {}),
            (("compute", "boot-volume-attachment", "list"), []),
            (("network", "security-list", "get"), []),
        ):
            with self.subTest(key=key):
                self.provider[key] = changed
                with self.assertRaises(LIVE.BASE.Stop):
                    self.check()
                self.setUp()


if __name__ == "__main__":
    unittest.main()
