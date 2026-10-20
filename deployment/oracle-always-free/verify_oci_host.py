#!/usr/bin/env python3
"""Fail-closed, read-only identity check for the actual OCI staging VM.

Use from the reviewed installer and the on-host health checker. The OCI v2
instance-metadata endpoint is link-local, never proxied and never redirected.
The returned instance identifiers are validated without being printed.
This code cannot launch instances, change networking, or accept customer data.
"""
from __future__ import annotations

import argparse
import json
import platform
from urllib.request import Request, ProxyHandler, HTTPRedirectHandler, build_opener

METADATA_URL = "http://169.254.169.254/opc/v2/instance/"
MAX_METADATA_BYTES = 131072
SHAPE_CONFIG_URL = METADATA_URL + "shapeConfig"
HOST_TYPES = {
    "a1": ("aarch64", "VM.Standard.A1.Flex"),
    "micro": ("x86_64", "VM.Standard.E2.1.Micro"),
}


class DenyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("OCI instance metadata redirect forbidden")


def read_metadata(url: str = METADATA_URL) -> dict:
    if url not in {METADATA_URL, SHAPE_CONFIG_URL}:
        raise ValueError("Unapproved OCI metadata endpoint")
    request = Request(url, headers={"Authorization": "Bearer Oracle"},
                      method="GET")
    opener = build_opener(ProxyHandler({}), DenyRedirect())
    try:
        with opener.open(request, timeout=6) as response:
            if response.geturl() != url:
                raise ValueError("OCI instance metadata source changed")
            raw = response.read(MAX_METADATA_BYTES + 1)
    except (OSError, ValueError) as exc:
        raise ValueError("Cannot authenticate OCI v2 instance metadata") from None
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError("OCI instance metadata exceeds safe size")
    try:
        data = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, ValueError):
        raise ValueError("OCI v2 instance metadata is invalid") from None
    if not isinstance(data, dict):
        raise ValueError("OCI v2 instance metadata is not an object")
    return data


def read_shape_config() -> dict:
    """Read the separate official OCI IMDSv2 allocation endpoint, fail closed."""
    return read_metadata(SHAPE_CONFIG_URL)


def verify_instance_metadata(data: dict, architecture: str, flavor: str,
                             *, shape_config: dict | None = None) -> None:
    if flavor not in HOST_TYPES or not isinstance(data, dict):
        raise ValueError("Unsupported OCI host type")
    expected_arch, expected_shape = HOST_TYPES[flavor]
    if architecture != expected_arch:
        raise ValueError("OCI host architecture does not match free shape")
    if data.get("shape") != expected_shape:
        raise ValueError("OCI host is not the exact approved free shape")
    if not isinstance(data.get("id"), str) or not data["id"].startswith("ocid1.instance."):
        raise ValueError("OCI instance identity missing")
    config = shape_config if shape_config is not None else data.get("shapeConfig")
    if flavor == "a1":
        # A1.Flex can exceed the Always Free allocation; the nominal shape
        # name alone is NOT sufficient. Our reviewed staging profile explicitly
        # requests 2 OCPUs and 12 GiB, and missing IMDS shapeConfig is a HOLD.
        if not isinstance(config, dict):
            raise ValueError("OCI A1 allocation is missing; free quota not proved")
        for key, expected in (("ocpus", 2), ("memoryInGBs", 12)):
            value = config.get(key)
            if type(value) not in {int, float} or value != expected:
                raise ValueError("OCI A1 allocation differs from 2 OCPU / 12 GiB")
    elif config is not None:
        if not isinstance(config, dict):
            raise ValueError("OCI shape configuration must be an object")
        if "memoryInGBs" in config and (
            type(config["memoryInGBs"]) not in {int, float}
            or config["memoryInGBs"] != 1
        ):
            raise ValueError("OCI Micro is not the fixed one-GiB shape")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--a1", action="store_true",
                       help="verify the reviewed Always Free A1 Arm host")
    group.add_argument("--micro", action="store_true",
                       help="verify the reviewed Always Free E2.1.Micro x86 host")
    args = parser.parse_args(argv)
    flavor = "micro" if args.micro else "a1"
    identity = read_metadata()
    allocation = read_shape_config() if flavor == "a1" else None
    verify_instance_metadata(identity, platform.machine(), flavor,
                             shape_config=allocation)
    print("PASS: exact OCI staging host shape attested; production/customer approval NOT granted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
