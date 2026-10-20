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
PRIVATE_SSH_RECEIPT = BASE.RESOURCE_DIR / "temporary-private-ssh.json"


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




def _read_private_ssh_receipt(path: Path = PRIVATE_SSH_RECEIPT) -> dict:
    """Private filesystem record is a pointer; OCI remains the truth source."""
    require(path.is_file() and not path.is_symlink(), "Private SSH NSG receipt is missing")
    meta = os.stat(path)
    require(stat.S_ISREG(meta.st_mode) and (meta.st_mode & 0o077) == 0
            and meta.st_uid == os.geteuid(),
            "Private SSH NSG receipt owner or permissions are not verified")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BASE.Stop("Private SSH NSG receipt is unreadable") from None
    require(isinstance(data, dict), "Private SSH NSG receipt is not an object")
    _id(data.get("nsg_id"), "networksecuritygroup")
    _id(data.get("vnic_id"), "vnic")
    require(isinstance(data.get("rule_id"), str)
            and re.fullmatch(r"[A-Za-z0-9_-]{4,128}", data["rule_id"]),
            "Private SSH NSG receipt has no exact rule identity")
    return data


def _verify_vnic_nsg(receipt: dict, vnic: dict,
                     private_ssh_receipt: dict | None, region: str) -> int:
    """Attest *all* NSG rules: no NSG, or one exact private-only SSH rule."""
    attached = vnic.get("nsg-ids")
    require(isinstance(attached, list), "VNIC network security groups unknown")
    if attached == []:
        require(private_ssh_receipt is None, "Stale private SSH NSG receipt")
        return 0
    require(len(attached) == 1 and isinstance(private_ssh_receipt, dict),
            "Unrecognized or multiple VM network security groups")
    nsg_id = _id(private_ssh_receipt.get("nsg_id"), "networksecuritygroup")
    vnic_id = _id(private_ssh_receipt.get("vnic_id"), "vnic")
    require(attached == [nsg_id] and vnic.get("id") == vnic_id,
            "Private SSH NSG receipt not bound to the actual VM VNIC")
    group = _get("network", "nsg", "get", "--nsg-id", nsg_id, region=region)
    require(group.get("id") == nsg_id and group.get("vcn-id") == receipt["vcn_id"]
            and group.get("lifecycle-state") == "AVAILABLE",
            "Attached NSG no longer belongs to the approved VCN")
    # Read ALL pages without filtering directions. Missing information is HOLD.
    rules = _list(BASE.cli("network", "nsg", "rules", "list",
                           "--nsg-id", nsg_id, "--all", region=region),
                  "complete management NSG rules")
    require(len(rules) == 1, "Management NSG has additional or missing rules")
    rule = rules[0]
    require(rule.get("id") == private_ssh_receipt.get("rule_id")
            and rule.get("direction") == "INGRESS"
            and rule.get("source-type") == "CIDR_BLOCK"
            and rule.get("source") == BASE.SUBNET_NETWORK
            and rule.get("protocol") == "6"
            and rule.get("is-stateless") is False,
            "Management NSG source, protocol, or exact rule identity changed")
    tcp = rule.get("tcp-options")
    require(isinstance(tcp, dict)
            and tcp.get("destination-port-range") == {"min": 22, "max": 22}
            and type((tcp.get("destination-port-range") or {}).get("min")) is int
            and type((tcp.get("destination-port-range") or {}).get("max")) is int
            and tcp.get("source-port-range") is None,
            "Management NSG is not strictly scoped to TCP/22")
    return 1

def inspect_running_micro(receipt: dict, *, private_ssh_receipt: dict | None = None) -> dict:
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
    require(len(vnics) == 1 and vnics[0].get("subnet-id") == receipt["subnet_id"],
            "VM has unexpected VNIC or unapproved subnet")
    management_nsg_count = _verify_vnic_nsg(
        receipt, vnics[0], private_ssh_receipt, region)
    # A separately attested private-only SSH management rule is NEVER
    # reported as zero total ingress. The original security list remains closed.
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
                              "--availability-domain", receipt["availability_domain"],
                              "--compartment-id", tenant,
                              "--instance-id", receipt["instance_id"],
                              "--all", region=region), "instance boot attachments")
    attached = [x for x in attached if BASE.active(x)]
    require(len(attached) == 1
            and attached[0].get("lifecycle-state") == "ATTACHED"
            and isinstance(attached[0].get("boot-volume-id"), str),
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
        "vm_attached_nsg_count": management_nsg_count,
        "private_management_ssh_rule_verified": management_nsg_count == 1,
        "no_public_ingress_rules_verified": True,
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
    parser.add_argument("--private-ssh-receipt", type=Path,
                        default=PRIVATE_SSH_RECEIPT,
                        help="optional owner-only private SSH NSG receipt")
    args = parser.parse_args(argv)
    private_proof = None
    if args.private_ssh_receipt.exists() or args.private_ssh_receipt.is_symlink():
        private_proof = _read_private_ssh_receipt(args.private_ssh_receipt)
    report = inspect_running_micro(_read_final_receipt(args.receipt),
                                   private_ssh_receipt=private_proof)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BASE.Stop, ValueError, KeyError, TypeError) as exc:
        # Error details never contain input OCIDs, credentials or account IDs.
        print("HOLD: read-only OCI VM attestation failed: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
