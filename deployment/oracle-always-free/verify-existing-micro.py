#!/usr/bin/env python3
"""Read-only OCI micro acceptance: independently verify an EXISTING free VM.

Does not provision, stop, start, attach, modify, expose, SSH into, or configure
any resource. Never reports a deployed application or approved customer pilot.
OCI resource identifiers and authentication tokens are deliberately not printed.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "retally_oci_live_base", HERE / "provision-cloud-shell.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Reviewed OCI preflight implementation missing")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

MICRO_SHAPE = "VM.Standard.E2.1.Micro"
EXPECTED_BOOT_GB = 50


def _match_id(receipt: dict, field: str, kind: str) -> str:
    value = receipt.get(field)
    if not isinstance(value, str) or not value.startswith(f"ocid1.{kind}."):
        raise BASE.Stop(f"Missing recorded {field}; no OCI write attempted")
    return value


def _data(value, subject: str) -> dict:
    BASE.ensure(isinstance(value, dict), f"{subject} was not an OCI object")
    return value


def _list(value, subject: str) -> list[dict]:
    return BASE.data_list(value, subject)


def audit_existing_micro(receipt: dict, *, read=None) -> dict:
    """Reconcile provider objects against the original private receipt.

    read must have the signature of BASE.cli(*args, region=). A separately
    supplied reader allows exact, offline negative tests without contacting OCI.
    All calls use ONLY GET/LIST verbs, fixed resource paths, and no retries.
    """
    if read is None:
        read = BASE.cli
    BASE.ensure(isinstance(receipt, dict) and receipt.get("schema") == 1,
                "Unsupported OCI acceptance receipt")
    BASE.ensure(receipt.get("phase") == "vm_running"
                and receipt.get("release_status") == "HOLD"
                and receipt.get("no_customer_data") is True
                and receipt.get("no_open_ingress") is True,
                "Recorded VM is not in the required non-customer release hold")
    BASE.ensure(receipt.get("actual_shape") == MICRO_SHAPE
                and receipt.get("actual_ram_gb") == 1
                and receipt.get("boot_gb_requested") == EXPECTED_BOOT_GB,
                "Recorded shape, memory or boot allocation is not the reviewed E2 Micro")
    region = receipt.get("home_region")
    ad = receipt.get("availability_domain")
    BASE.ensure(isinstance(region, str) and region
                and isinstance(ad, str) and ad, "Original OCI placement missing")

    instance_id = _match_id(receipt, "instance_id", "instance")
    tenancy_id = _match_id(receipt, "tenancy_id", "tenancy")
    vcn_id = _match_id(receipt, "vcn_id", "vcn")
    security_id = _match_id(receipt, "security_list_id", "securitylist")
    subnet_id = _match_id(receipt, "subnet_id", "subnet")

    def get(*args):
        # Explicit fail-closed guard prevents a future caller from accidentally
        # turning this verification helper into an OCI resource-mutating action.
        BASE.ensure(len(args) >= 3 and args[2] in {"get", "list", "list-vnics"},
                    "OCI acceptance allows read-only operations only")
        return read(*args, region=region)

    vm = _data(get("compute", "instance", "get",
                   "--instance-id", instance_id), "OCI instance")
    BASE.ensure(vm.get("id") == instance_id
                and vm.get("display-name") == BASE.NAME
                and vm.get("compartment-id") == tenancy_id
                and vm.get("availability-domain") == ad
                and vm.get("shape") == MICRO_SHAPE
                and vm.get("lifecycle-state") == "RUNNING",
                "Existing VM failed independent identity, free shape or RUNNING check")
    shape = vm.get("shape-config") or {}
    BASE.ensure(isinstance(shape, dict), "Invalid OCI E2 shape configuration")
    if "memory-in-gbs" in shape:
        BASE.ensure(type(shape["memory-in-gbs"]) in (int, float)
                    and float(shape["memory-in-gbs"]) == 1.0,
                    "OCI E2 instance is not a one-GiB Micro")

    vcn = _data(get("network", "vcn", "get",
                    "--vcn-id", vcn_id), "OCI VCN")
    BASE.ensure(vcn.get("id") == vcn_id
                and vcn.get("display-name") == BASE.VPC_NAME
                and vcn.get("lifecycle-state") == "AVAILABLE"
                and vcn.get("default-security-list-id") == security_id,
                "Original VCN identity changed")

    sl = _data(get("network", "security-list", "get",
                   "--security-list-id", security_id), "OCI security list")
    BASE.ensure(sl.get("id") == security_id
                and sl.get("vcn-id") == vcn_id
                and sl.get("ingress-security-rules") == [],
                "VM VCN security list has unapproved inbound rules")

    subnet = _data(get("network", "subnet", "get",
                       "--subnet-id", subnet_id), "OCI subnet")
    BASE.ensure(subnet.get("id") == subnet_id
                and subnet.get("vcn-id") == vcn_id
                and subnet.get("lifecycle-state") == "AVAILABLE"
                and subnet.get("security-list-ids") == [security_id],
                "VM subnet is not protected by the recorded zero-ingress list")

    vnics = _list(get("compute", "instance", "list-vnics",
                      "--instance-id", instance_id), "OCI VNICs")
    BASE.ensure(len(vnics) == 1
                and vnics[0].get("subnet-id") == subnet_id
                and (vnics[0].get("nsg-ids") or []) == [],
                "VM VNIC changed or gained an unapproved Network Security Group")

    attachments = _list(get("compute", "boot-volume-attachment", "list",
                            "--availability-domain", ad,
                            "--compartment-id", tenancy_id,
                            "--instance-id", instance_id), "OCI boot attachments")
    BASE.ensure(len(attachments) == 1
                and attachments[0].get("instance-id") == instance_id
                and attachments[0].get("lifecycle-state") == "ATTACHED",
                "Expected exactly one live OCI boot-volume attachment")
    volume_id = attachments[0].get("boot-volume-id")
    BASE.ensure(isinstance(volume_id, str)
                and volume_id.startswith("ocid1.bootvolume."),
                "OCI boot attachment has no valid volume identity")
    boot = _data(get("bv", "boot-volume", "get",
                     "--boot-volume-id", volume_id), "OCI boot volume")
    BASE.ensure(boot.get("id") == volume_id
                and boot.get("size-in-gbs") == EXPECTED_BOOT_GB
                and boot.get("lifecycle-state") == "AVAILABLE",
                "Boot volume is not the approved 50-GB live disk")

    return {
        "schema": 1,
        "status": "OCI_EXISTING_MICRO_NETWORK_AND_BOOT_VERIFIED",
        "shape": MICRO_SHAPE,
        "instance_running": True,
        "boot_gb": EXPECTED_BOOT_GB,
        "boot_attached": True,
        "vnic_count": 1,
        "security_list_ingress": 0,
        "vnic_nsg_count": 0,
        "oci_write_requests": 0,
        "customer_data_verified_absent": False,
        "guest_application_healthy_verified": False,
        "host_disk_encryption_verified": False,
        "off_device_backup_verified": False,
        "billing_statement_verified": False,
        "customer_production_release": "HOLD",
    }


def main() -> int:
    # The final receipt is created by the original OCI Cloud Shell provisioning
    # flow and must remain owned by this OS account with no group/world access.
    p = BASE.RECEIPT
    BASE.ensure(p.is_file() and not p.is_symlink()
                and p.stat().st_uid == os.geteuid()
                and p.stat().st_mode & 0o077 == 0,
                "Trusted owner-only final OCI receipt unavailable")
    try:
        receipt = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BASE.Stop("Existing OCI receipt is malformed") from None
    print(json.dumps(audit_existing_micro(receipt), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BASE.Stop, ValueError):
        # Never put tenancy IDs, network objects, credentials or provider
        # response bodies into operator-facing reports or public CI logs.
        print("HOLD: Oracle live micro acceptance failed; no resources changed")
        raise SystemExit(2)
