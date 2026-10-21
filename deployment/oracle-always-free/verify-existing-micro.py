#!/usr/bin/env python3
"""Compatibility entry point for the FULL read-only OCI Micro acceptance audit.

The older lightweight verifier did not exhaust paginated VNIC inventory or
independently detect ATTACHING / DETACHING interfaces. Never certify isolation
using a weaker partial snapshot. Always delegate to the source-locked full
auditor in check-existing-micro.py, including strict final-receipt custody,
provider home region, original Ubuntu image, VCN/route/gateway, *all* VNICs
and attachment lifecycle, exact boot-volume, and zero ingress/NSGs.

No OCI writes, SSH, installation, customer access, or billing mutations.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "retally_strict_micro_audit", HERE / "check-existing-micro.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Reviewed full OCI Micro auditor is unavailable")
STRICT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STRICT)
BASE = STRICT.BASE
MICRO_SHAPE = STRICT.SHAPE
EXPECTED_BOOT_GB = STRICT.BOOT_GB


def audit_existing_micro(receipt: dict, *, read=None) -> dict:
    """Keep old aggregate report shape, but REQUIRE the strict full audit.

    Alternate provider readers are intentionally unsupported here: injection
    could sidestep full inventory and host checks. Offline tests patch the
    strong auditor's read-only provider boundary instead.
    """
    if read is not None:
        raise ValueError("Alternate reader forbidden; run full read-only provider audit")
    BASE.ensure(
        isinstance(receipt, dict)
        and receipt.get("schema") == 1
        and receipt.get("phase") == "vm_running"
        and receipt.get("release_status") == "HOLD"
        and receipt.get("production_certified") is False
        and receipt.get("no_customer_data") is True
        and receipt.get("no_open_ingress") is True,
        "Original receipt's independent customer and network holds are invalid",
    )
    verified = STRICT.inspect_running_micro(receipt)
    BASE.ensure(
        verified["instance_running"] is True
        and verified["oci_security_list_zero_ingress"] is True
        and verified["vm_expected_subnet_and_vnic_verified"] is True
        and verified["vm_attached_nsg_count"] == 0
        and verified["boot_volume_gb"] == EXPECTED_BOOT_GB
        and verified["official_ubuntu_24_04_image_verified"] is True
        and verified["outbound_route_verified"] is True
        and verified["customer_release_status"] == "HOLD",
        "The complete Oracle Micro acceptance audit did not pass",
    )
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
        "full_placement_and_attachment_audit": True,
        "customer_data_verified_absent": False,
        "guest_application_healthy_verified": False,
        "host_disk_encryption_verified": False,
        "off_device_backup_verified": False,
        "billing_statement_verified": False,
        "customer_production_release": "HOLD",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=STRICT.FINAL_RECEIPT)
    args = parser.parse_args(argv)
    # Full auditor enforces owner-only private receipt and immutable holds.
    receipt = STRICT._read_final_receipt(args.receipt)
    print(json.dumps(audit_existing_micro(receipt), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BASE.Stop, ValueError, TypeError, KeyError):
        # Never leak private OCIDs, account metadata or cloud provider errors.
        print("HOLD: complete Oracle Micro acceptance failed; no resources changed")
        raise SystemExit(2)
