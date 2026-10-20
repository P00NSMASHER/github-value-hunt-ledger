#!/usr/bin/env python3
"""Read-only OCI instance and zero-ingress audit for the existing RETALLY Micro.

This script runs ONLY in the authenticated owner's Oracle Cloud Shell. It does
not create, delete, modify, or start cloud resources; never upload/print secrets
or customer data; never certify off-device backups, a private application, or
customer production readiness.

A local owner-only provisioning receipt and independent OCI GET/LIST responses
must agree. The allowed shape is one fixed Always Free E2.1.Micro (eligibility
is not an account-wide zero-dollar cost certification).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

_ROOT = Path(__file__).resolve().parent
_BASE = _ROOT / "provision-cloud-shell.py"
_spec = importlib.util.spec_from_file_location("retally_oci_existing_readonly_base", _BASE)
if not _spec or not _spec.loader:
    raise RuntimeError("Reviewed OCI verification dependency is missing")
BASE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BASE)

SHAPE = "VM.Standard.E2.1.Micro"
BOOT_GB = 50
EXPECTED_RELEASE = "HOLD"
FINAL_RECEIPT = BASE.RECEIPT


def require(condition, reason):
    if not condition:
        raise BASE.Stop(reason)


def _id(value: object, resource: str) -> str:
    require(isinstance(value, str) and
            re.fullmatch(r"ocid1\." + re.escape(resource) + r"\.[a-z0-9.-]+", value) is not None,
            "Original receipt is missing an OCI " + resource + " identity")
    return value


def _data(value: object, label: str) -> dict:
    require(isinstance(value, dict), "OCI " + label + " response is not an object")
    return value


def _list(value: object, label: str) -> list[dict]:
    return BASE.data_list(value, label)


def _get(*args: str, region: str) -> dict:
    require(len(args) >= 3 and args[2] == "get",
            "Only provider GET operations are supported by this audit")
    return _data(BASE.cli(*args, region=region), " ".join(args[:2]))


def _read_final_receipt(path: Path = FINAL_RECEIPT) -> dict:
    require(path.is_file() and not path.is_symlink(),
            "Owner-only final OCI instance receipt is missing")
    meta = os.stat(path)
    require(stat.S_ISREG(meta.st_mode) and (meta.st_mode & 0o077) == 0
            and meta.st_uid == os.geteuid(),
            "OCI receipt permissions or owner are not private")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BASE.Stop("OCI instance receipt is unreadable") from None
    require(isinstance(receipt, dict), "OCI final receipt must be an object")
    require(receipt.get("schema") == 1 and receipt.get("phase") == "vm_running",
            "Original receipt is not an accepted running Micro state")
    require(receipt.get("release_status") == EXPECTED_RELEASE
            and receipt.get("production_certified") is False
            and receipt.get("no_customer_data") is True
            and receipt.get("no_open_ingress") is True,
            "The original customer/security release holds are not intact")
    require(receipt.get("actual_shape") == SHAPE
            and receipt.get("actual_ram_gb") == 1
            and receipt.get("boot_gb_requested") == BOOT_GB,
            "Receipt does not identify the fixed Always Free Micro shape")
    for field, resource in (
        ("tenancy_id", "tenancy"), ("instance_id", "instance"),
        ("vcn_id", "vcn"), ("subnet_id", "subnet"),
        ("security_list_id", "securitylist"),
        ("route_table_id", "routetable"),
        ("internet_gateway_id", "internetgateway"),
        ("image_id", "image"),
    ):
        _id(receipt.get(field), resource)
    require(isinstance(receipt.get("home_region"), str)
            and re.fullmatch(r"[a-z]{2}-[a-z-]+-\d+", receipt["home_region"]),
            "Receipt home region is invalid")
    return receipt


def inspect_running_micro(receipt: dict) -> dict:
    """Read independently from OCI; return only aggregate-safe checks."""
    tenant, region = receipt["tenancy_id"], receipt["home_region"]
    require(BASE.home_region(tenant) == region,
            "Tenancy home region changed since provisioning")
    instance = _get("compute", "instance", "get", "--instance-id",
                    receipt["instance_id"], region=region)
    require(instance.get("id") == receipt["instance_id"]
            and instance.get("compartment-id") == tenant
            and instance.get("display-name") == BASE.NAME
            and instance.get("lifecycle-state") == "RUNNING"
            and instance.get("shape") == SHAPE,
            "Running instance no longer matches the fixed RETALLY Micro")
    require(instance.get("availability-domain") == receipt.get("availability_domain"),
            "Running instance availability domain changed")
    source = instance.get("image-id") or (instance.get("source-details") or {}).get("image-id")
    require(source == receipt["image_id"], "VM original operating system image changed")
    config = instance.get("shape-config") or {}
    require(isinstance(config, dict), "VM shape configuration is unexpected")
    if "memory-in-gbs" in config:
        require(type(config["memory-in-gbs"]) in (int, float)
                and config["memory-in-gbs"] == 1,
                "VM does not have exactly the free Micro's 1 GiB RAM")

    image = _get("compute", "image", "get", "--image-id",
                 receipt["image_id"], region=region)
    require(image.get("id") == receipt["image_id"]
            and image.get("operating-system") == "Canonical Ubuntu"
            and image.get("operating-system-version") == "24.04"
            and image.get("lifecycle-state") == "AVAILABLE",
            "Operating system is not the original official Ubuntu 24.04 image")

    vcn = _get("network", "vcn", "get", "--vcn-id",
               receipt["vcn_id"], region=region)
    require(vcn.get("id") == receipt["vcn_id"]
            and vcn.get("display-name") == BASE.VPC_NAME
            and vcn.get("lifecycle-state") == "AVAILABLE"
            and vcn.get("cidr-blocks") == [str(BASE.VPC_NETWORK)]
            and vcn.get("default-security-list-id") == receipt["security_list_id"]
            and vcn.get("default-route-table-id") == receipt["route_table_id"],
            "VCN identity, routing, or default security list changed")

    rules = _get("network", "security-list", "get", "--security-list-id",
                 receipt["security_list_id"], region=region)
    require(rules.get("id") == receipt["security_list_id"]
            and rules.get("vcn-id") == receipt["vcn_id"]
            and rules.get("ingress-security-rules") == [],
            "OCI security list has unknown or nonzero inbound permissions")

    subnet = _get("network", "subnet", "get", "--subnet-id",
                  receipt["subnet_id"], region=region)
    require(subnet.get("id") == receipt["subnet_id"]
            and subnet.get("lifecycle-state") == "AVAILABLE"
            and subnet.get("vcn-id") == receipt["vcn_id"]
            and subnet.get("security-list-ids") == [receipt["security_list_id"]]
            and subnet.get("cidr-block") == BASE.SUBNET_NETWORK,
            "The VM subnet changed or references unapproved security lists")

    vnics = _list(BASE.cli("compute", "instance", "list-vnics",
                           "--instance-id", receipt["instance_id"],
                           region=region), "VM attached VNICs")
    require(len(vnics) == 1
            and vnics[0].get("subnet-id") == receipt["subnet_id"]
            and vnics[0].get("nsg-ids") in ([], None),
            "VM has unexpected VNIC or attached network security groups")
    # Empty security-list ingress AND zero attached NSGs are required
    # together. Never interpret an unattested private NSG as no ingress.
    routes = _get("network", "route-table", "get", "--rt-id",
                  receipt["route_table_id"], region=region)
    route_rules = routes.get("route-rules")
    require(routes.get("id") == receipt["route_table_id"]
            and routes.get("vcn-id") == receipt["vcn_id"]
            and isinstance(route_rules, list) and len(route_rules) == 1
            and (route_rules[0].get("destination") or route_rules[0].get("cidr-block"))
                == "0.0.0.0/0"
            and route_rules[0].get("network-entity-id") == receipt["internet_gateway_id"],
            "Outbound-only route no longer matches its recorded gateway")
    gw = _get("network", "internet-gateway", "get", "--ig-id",
              receipt["internet_gateway_id"], region=region)
    require(gw.get("id") == receipt["internet_gateway_id"]
            and gw.get("vcn-id") == receipt["vcn_id"]
            and gw.get("is-enabled") is True,
            "Outbound gateway identity or status changed")

    attached = _list(BASE.cli("compute", "boot-volume-attachment", "list",
                              "--compartment-id", tenant,
                              "--instance-id", receipt["instance_id"],
                              region=region), "instance boot attachments")
    attached = [x for x in attached if BASE.active(x)]
    require(len(attached) == 1 and
            isinstance(attached[0].get("boot-volume-id"), str),
            "Running VM must have exactly one verifiable boot volume")
    volume = _get("bv", "boot-volume", "get", "--boot-volume-id",
                  attached[0]["boot-volume-id"], region=region)
    require(volume.get("id") == attached[0]["boot-volume-id"]
            and volume.get("lifecycle-state") == "AVAILABLE"
            and type(volume.get("size-in-gbs")) in (int, float)
            and volume.get("size-in-gbs") == BOOT_GB,
            "VM boot volume does not match the reviewed 50 GiB request")
    return {
        "schema": 1,
        "scope": "READ_ONLY_CLOUD_PROVIDER_STAGING_STATE",
        "instance_running": True,
        "fixed_always_free_eligible_shape_verified": True,
        "official_ubuntu_24_04_image_verified": True,
        "boot_volume_gb": BOOT_GB,
        "vm_expected_subnet_and_vnic_verified": True,
        "oci_security_list_zero_ingress": True,
        "vm_attached_nsg_count": 0,
        "outbound_route_verified": True,
        "app_installed": None,
        "guest_firewall_verified": False,
        "off_device_restore_verified": False,
        "account_zero_charges_verified": False,
        "independent_reviewer_approved": False,
        "commercial_production_certified": False,
        "customer_release_status": EXPECTED_RELEASE,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=FINAL_RECEIPT,
                        help="owner-controlled exact OCI final receipt, read-only")
    args = parser.parse_args(argv)
    report = inspect_running_micro(_read_final_receipt(args.receipt))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BASE.Stop, ValueError, KeyError, TypeError) as exc:
        # Error details never contain input OCIDs, credentials or account IDs.
        print("HOLD: read-only OCI VM attestation failed: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
