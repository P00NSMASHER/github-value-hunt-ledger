"""Offline negative tests for actual OCI v2 host attestation."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "verify_oci_host.py"
SPEC = importlib.util.spec_from_file_location("retally_oci_host_attestation", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(self, obj, *, url=None, raw=None):
        self.url = url or MODULE.METADATA_URL
        self.raw = json.dumps(obj).encode() if raw is None else raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return None
    def geturl(self):
        return self.url
    def read(self, size=-1):
        return self.raw[:size]


class HostAttestationTests(unittest.TestCase):
    def setUp(self):
        self.arm = {"id": "ocid1.instance.oc1.synthetic-A1", "shape": "VM.Standard.A1.Flex"}
        self.micro = {"id": "ocid1.instance.oc1.synthetic-MICRO",
                      "shape": "VM.Standard.E2.1.Micro",
                      "shapeConfig": {"memoryInGBs": 1}}

    def test_exact_arm_and_micro_are_accepted(self):
        MODULE.verify_instance_metadata(self.arm, "aarch64", "a1")
        MODULE.verify_instance_metadata(self.micro, "x86_64", "micro")

    def test_unreviewed_architecture_or_shape_is_rejected(self):
        for data, machine, flavor in [
            (self.arm, "x86_64", "a1"),
            (self.micro, "aarch64", "micro"),
            (self.arm, "aarch64", "micro"),
            (self.micro, "x86_64", "a1"),
            ({**self.micro, "shape": "VM.Standard.E2.1"}, "x86_64", "micro"),
            ({**self.micro, "shape": "VM.Standard.E2.1.Flex"}, "x86_64", "micro"),
            ({**self.micro, "shapeConfig": {"memoryInGBs": 2}}, "x86_64", "micro"),
            ({**self.micro, "shapeConfig": {"memoryInGBs": True}}, "x86_64", "micro"),
            ({**self.arm, "id": "untrusted"}, "aarch64", "a1"),
            ({**self.micro, "id": None}, "x86_64", "micro"),
        ]:
            with self.subTest(data=data, machine=machine, flavor=flavor):
                with self.assertRaises(ValueError):
                    MODULE.verify_instance_metadata(data, machine, flavor)

    def test_cli_reads_metadata_without_network_when_mocked(self):
        for data, arch, arg in [(self.arm, "aarch64", "--a1"),
                                (self.micro, "x86_64", "--micro")]:
            with self.subTest(arg=arg), patch.object(MODULE, "read_metadata", return_value=data), \
                    patch.object(MODULE.platform, "machine", return_value=arch):
                self.assertEqual(MODULE.main([arg]), 0)

    def test_linklocal_metadata_request_uses_no_proxy_and_no_redirect(self):
        class FakeOpener:
            def open(self, request, timeout):
                self.request, self.timeout = request, timeout
                return FakeResponse(self_data)
        self_data = self.micro
        opener = FakeOpener()
        with patch.object(MODULE, "build_opener", return_value=opener) as mock:
            self.assertEqual(MODULE.read_metadata(), self.micro)
            self.assertEqual(opener.request.full_url, MODULE.METADATA_URL)
            self.assertEqual(opener.request.get_header("Authorization"), "Bearer Oracle")
            self.assertEqual(opener.timeout, 6)
            self.assertTrue(any(isinstance(h, MODULE.ProxyHandler) and h.proxies == {}
                                for h in mock.call_args.args))
            self.assertTrue(any(isinstance(h, MODULE.DenyRedirect)
                                for h in mock.call_args.args))
        with self.assertRaises(ValueError):
            MODULE.DenyRedirect().redirect_request(None, None, 301, "", {}, "http://evil.invalid")

    def test_redirect_oversize_and_malformed_fail_closed(self):
        responses = [
            FakeResponse(self.micro, url="https://evil.invalid/"),
            FakeResponse(self.micro, raw=b"Z"*(MODULE.MAX_METADATA_BYTES+1)),
            FakeResponse(self.micro, raw=b"\xff"),
            FakeResponse(self.micro, raw=b"[]"),
        ]
        for resp in responses:
            with self.subTest(response=resp.url, length=len(resp.raw)):
                with patch.object(MODULE, "build_opener") as mocked:
                    mocked.return_value.open.return_value = resp
                    with self.assertRaises(ValueError):
                        MODULE.read_metadata()


if __name__ == "__main__":
    unittest.main()
