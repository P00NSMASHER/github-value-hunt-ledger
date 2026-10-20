#!/usr/bin/env python3
"""Safely inspect or provision one OCI Always Free E2 Micro in EXISTING RETALLY network.

No network creation, no billable shape fallback, no external outreach, no app
deployment, no inbound ports. Requires a verified original partial network and
a separate independently reviewed source checkout. Cloud Shell only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

BASE_PATH = Path(__file__).with_name("provision-cloud-shell.py")
spec = importlib.util.spec_from_file_location("retally_original_oci_provision", BASE_PATH)
if not spec or not spec.loader:
    raise RuntimeError("original A1 OCI safety implementation is unavailable")
BASE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BASE)

MICRO_SHAPE = "VM.Standard.E2.1.Micro"
MICRO_MEMORY_GB = 1
MICRO_BOOT_GB = 50
MAX_FREE_MICRO_INSTANCES = 2
MICRO_RECEIPT_ARCHIVE = BASE.RESOURCE_DIR / "original-partial-after-micro.json"


def inventory(tenancy: str, region: str, state: dict) -> dict:
    """Reconcile all compartments and the already locked-down private network."""
    BASE.verify_partial_network(state, tenancy, region)
    original = BASE.read_inventory(tenancy, region,
                                   existing_vcn_id=state["vcn_id"])
    compartments = BASE.compartments(tenancy, region)
    micro_count = 0
    existing_name_count = 0
    for compartment in compartments:
        instances = BASE.data_list(
            BASE.cli("compute", "instance", "list", "--compartment-id",
                     compartment, "--all", region=region), "micro instance inventory")
        for instance in instances:
            if not BASE.active(instance):
                continue
            if instance.get("shape") == MICRO_SHAPE:
                micro_count += 1
            if instance.get("display-name") == BASE.NAME:
                existing_name_count += 1
    BASE.ensure(micro_count < MAX_FREE_MICRO_INSTANCES,
                "Always Free E2 Micro two-instance allowance is already used.")
    BASE.ensure(existing_name_count == 0,
                "RETALLY staging instance already exists; refusing duplicate.")
    BASE.ensure(original["block_volume_gb_in_use"] + MICRO_BOOT_GB <=
                BASE.MAX_BLOCK_STORAGE_GB,
                "Always Free 200 GB block storage allowance would be exceeded.")
    BASE.ensure(original["existing_instances"] >= micro_count,
                "Compute inventory is internally inconsistent.")

    # Oracle's E2 Micro is eligible in ONE AD only. Shape availability is not
    # a guarantee of host capacity, so OCI launch errors must still fail closed.
    ads = BASE.data_list(BASE.cli("iam", "availability-domain", "list",
                                  "--compartment-id", tenancy, region=region),
                         "availability domains")
    offered = []
    for entry in ads:
        ad = entry.get("name")
        if not ad:
            continue
        shapes = BASE.data_list(
            BASE.cli("compute", "shape", "list", "--compartment-id", tenancy,
                     "--availability-domain", ad,
                     "--shape", MICRO_SHAPE, region=region),
            "E2 Micro availability-domain shape offerings")
        if any(shape.get("shape") == MICRO_SHAPE for shape in shapes):
            offered.append(ad)
    BASE.ensure(len(offered) == 1,
                "Expected exactly one home-region AD with E2 Micro; no substitute shape.")

    images = BASE.data_list(
        BASE.cli("compute", "image", "list", "--compartment-id", tenancy,
                 "--operating-system", "Canonical Ubuntu",
                 "--operating-system-version", "24.04",
                 "--shape", MICRO_SHAPE,
                 "--sort-by", "TIMECREATED", "--sort-order", "DESC",
                 region=region),
        "E2 Micro Ubuntu 24.04 images")
    eligible = [image for image in images
                if image.get("operating-system") == "Canonical Ubuntu"
                and image.get("operating-system-version") == "24.04"
                and image.get("lifecycle-state") == "AVAILABLE"
                and str(image.get("id", "")).startswith("ocid1.image.")]
    BASE.ensure(bool(eligible),
                "No approved official Ubuntu 24.04 image fits the E2 Micro shape.")
    return {
        "tenancy": tenancy, "home_region": region,
        "ad": offered[0], "image_id": eligible[0]["id"],
        "image_name": eligible[0].get("display-name"),
        "micro_instances_in_use": micro_count,
        "total_instances_in_use": original["existing_instances"],
        "block_gb_in_use": original["block_volume_gb_in_use"],
        "vcn_id": state["vcn_id"], "subnet_id": state["subnet_id"],
    }


def launch_single_micro(plan: dict, state: dict) -> dict:
    BASE.ensure(state.get("phase") == "subnet_created" and not state.get("instance_id"),
                "Cannot launch into a completed or unknown original network.")
    BASE.ensure(BASE.PARTIAL.exists() and not BASE.RECEIPT.exists(),
                "Original partial receipt changed before launch.")
    # Exact fixed Always Free E2 Micro shape; DO NOT pass A1 flex shape-config.
    instance = BASE.cli(
        "compute", "instance", "launch",
        "--availability-domain", plan["ad"],
        "--compartment-id", plan["tenancy"],
        "--subnet-id", state["subnet_id"],
        "--display-name", BASE.NAME,
        "--shape", MICRO_SHAPE,
        "--image-id", plan["image_id"],
        "--boot-volume-size-in-gbs", str(MICRO_BOOT_GB),
        "--ssh-authorized-keys-file", str(BASE.PUBLIC_KEY),
        "--assign-public-ip", "true",
        "--wait-for-state", "RUNNING",
        "--max-wait-seconds", "900",
        region=plan["home_region"], timeout=1000)
    BASE.ensure(isinstance(instance, dict) and
                str(instance.get("id", "")).startswith("ocid1.instance."),
                "Micro launch result is incomplete; DO NOT automatically retry.")
    remote = BASE.cli("compute", "instance", "get",
                      "--instance-id", instance["id"],
                      region=plan["home_region"])
    BASE.ensure(remote.get("id") == instance["id"]
                and remote.get("display-name") == BASE.NAME
                and remote.get("shape") == MICRO_SHAPE
                and remote.get("lifecycle-state") == "RUNNING"
                and remote.get("availability-domain") == plan["ad"]
                and remote.get("compartment-id") == plan["tenancy"],
                "Micro instance identity, lifecycle, or free shape verification failed.")
    config = remote.get("shape-config") or {}
    if "memory-in-gbs" in config:
        BASE.ensure(float(config["memory-in-gbs"]) == MICRO_MEMORY_GB,
                    "Micro instance memory allocation is not the 1 GiB free shape.")

    state.update({"instance_id": instance["id"],
                  "phase": "vm_running",
                  "actual_shape": MICRO_SHAPE,
                  "actual_ram_gb": MICRO_MEMORY_GB,
                  "image_id": plan["image_id"],
                  "availability_domain": plan["ad"],
                  "boot_gb_requested": MICRO_BOOT_GB,
                  "production_certified": False,
                  "no_customer_data": True, "release_status": "HOLD"})
    return state


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true",
                        help="Create EXACT free E2 Micro after new interactive confirmation")
    args = parser.parse_args(argv)
    os.umask(0o077)
    BASE.ensure(not BASE.RECEIPT.exists() and BASE.PARTIAL.exists(),
                "A partial OCI network receipt is required; do not create duplicate network.")
    try:
        state = json.loads(BASE.PARTIAL.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BASE.Stop("Original partial OCI receipt is unreadable.") from exc
    tenancy = BASE.read_tenancy(None)
    region = BASE.home_region(tenancy)
    plan = inventory(tenancy, region, state)
    print(json.dumps({
        "status": "E2_MICRO_READONLY_PREFLIGHT_PASS",
        "region": region, "shape": MICRO_SHAPE,
        "memory_gb": MICRO_MEMORY_GB,
        "boot_volume_gb": MICRO_BOOT_GB,
        "availability_domain": plan["ad"],
        "official_image": plan["image_name"],
        "micro_instances_in_use": plan["micro_instances_in_use"],
        "combined_block_gb_in_use": plan["block_gb_in_use"],
        "network_reused": True, "incoming": "DENY_ALL",
        "real_customer_data": False, "release_hold": True,
        "zero_spend_target": "Always Free shape; not a billing hard cap",
    }, sort_keys=True))
    if not args.create:
        print("READ ONLY; no resources created. Free host capacity not guaranteed.")
        return 0

    BASE.ensure(sys.stdin.isatty(),
                "Creation requires interactive confirmation in Oracle Cloud Shell.")
    print("This requests ONE fixed E2.1.Micro, 1 GB RAM, official Ubuntu, 50 GB boot.")
    print("No new network, no paid alternative, no inbound ports, no live customer data.")
    phrase = input("Type CREATE ONE RETALLY FREE MICRO: ").strip()
    BASE.ensure(phrase == "CREATE ONE RETALLY FREE MICRO",
                "Confirmation not received; no new resources created.")
    # TOCTOU defense: reevaluate account inventory and complete network twice.
    BASE.ensure(not MICRO_RECEIPT_ARCHIVE.exists(),
                "An earlier completed micro archive exists; refusing duplicate launch.")
    state = json.loads(BASE.PARTIAL.read_text(encoding="utf-8"))
    plan = inventory(tenancy, region, state)
    try:
        state = launch_single_micro(plan, state)
    except BASE.Stop:
        print("Original network receipt preserved; NEVER run original --apply.",
              file=sys.stderr)
        raise
    # The successful VM was read back from Oracle before a final receipt.
    # Keep partial evidence until the final receipt exists. An uncertain
    # write outcome blocks any later launch by both scripts.
    final_path = BASE.safe_receipt(state, partial=False)
    BASE.PARTIAL.rename(MICRO_RECEIPT_ARCHIVE)
    os.chmod(MICRO_RECEIPT_ARCHIVE, 0o600)
    print("VERIFIED: OCI fixed Always Free E2 Micro is RUNNING; customer release HOLD.")
    print("Receipt:", final_path)
    print("No RETALLY app installed and no external connection enabled.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BASE.Stop, ValueError) as exc:
        print("STOP (never substitute a paid shape):", str(exc), file=sys.stderr)
        raise SystemExit(2)
