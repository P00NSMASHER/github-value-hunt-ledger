"""Offline tests for fail-closed OCI synthetic-only encrypted backup transport."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).with_name("oci_synthetic_backup.py")
spec = importlib.util.spec_from_file_location("retally_oci_synthetic_backup", MODULE)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class OciBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="retally-oci-object-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.receipt = self.root / "sealed-backup-bucket-receipt.json"
        self.acceptance = self.root / "accepted.json"
        self.attempt = self.root / "attempt.json"
        self.orphan_receipt = self.root / "legacy-cleanup.json"
        self.info = {
            "schema": 1, "bucket": backup.BUCKET_NAME,
            "status": "PRIVATE_SYNTHETIC_ONLY", "storage_tier": "Standard",
            "public_access_type": "NoPublicAccess", "versioning": "Disabled",
            "real_customer_files": False, "off_device_restore_verified": False,
            "namespace": "syntheticnamespace", "region": "us-ashburn-1",
        }
        self._write_receipt(self.info)
        self.store = backup.OciStore(self.info)

    def _write_receipt(self, doc):
        self.receipt.write_text(json.dumps(doc), encoding="utf-8")
        self.receipt.chmod(0o600)

    def test_exact_bucket_receipt_and_owner_permissions(self):
        self.assertEqual(backup.parse_bucket_receipt(self.receipt)["bucket"], backup.BUCKET_NAME)
        for change in ({"storage_tier": "InfrequentAccess"}, {"public_access_type": "ObjectRead"},
                       {"versioning": "Enabled"}, {"status": "REAL_CUSTOMER"},
                       {"real_customer_files": True}, {"off_device_restore_verified": True}):
            with self.subTest(change=change):
                self._write_receipt({**self.info, **change})
                with self.assertRaises(backup.Refused):
                    backup.parse_bucket_receipt(self.receipt)
        self._write_receipt(self.info)
        self.receipt.chmod(0o644)
        with self.assertRaises(backup.Refused):
            backup.parse_bucket_receipt(self.receipt)

    def test_receipt_no_overwrite_and_symlink_refused(self):
        one = self.root / "attempt.json"
        backup.private_receipt(one, {"synthetic": True})
        self.assertEqual(one.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(backup.Refused):
            backup.private_receipt(one, {"synthetic": False})
        other = self.root / "alias.json"
        other.symlink_to(one)
        with self.assertRaises(backup.Refused):
            backup.private_receipt(other, {"new": True})

    def test_oci_cli_does_not_retry_or_log_provider_errors(self):
        denied = subprocess.CompletedProcess(["oci"], 1, "", "secret-account-id: Unauthorized")
        with patch.object(backup.subprocess, "run", return_value=denied) as run:
            with self.assertRaises(backup.Refused) as exc:
                self.store.cli("os", "object", "put", "--name", "synthetic")
        self.assertNotIn("secret-account-id", str(exc.exception))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0].count("--no-retry"), 1)
        self.assertEqual(run.call_args.args[0].count("--region"), 1)

    def test_top_level_object_put_response_is_accepted(self):
        source = self.root / "synthetic.rtbk"
        source.write_bytes(b"synthetic ciphertext only")
        source.chmod(0o600)
        response = subprocess.CompletedProcess(["oci"], 0, '{"etag":"OCI-TEST-ETAG"}\n', "")
        with patch.object(backup.subprocess, "run", return_value=response) as run:
            self.store.put("synthetic-recovery/test.rtbk", source)
        cmd = run.call_args.args[0]
        self.assertIn("--no-overwrite", cmd)
        self.assertIn("--verify-checksum", cmd)
        self.assertIn("--no-multipart", cmd)
        self.assertNotIn("--force", cmd)
        self.assertIn("Standard", cmd)

    def test_object_metadata_expected_vs_unsupported_response_shapes(self):
        expected = [{"name": "synthetic-only/a"}]
        with patch.object(self.store, "cli", return_value=json.dumps({"data": {"objects": expected}})):
            self.assertEqual(self.store.objects("synthetic-only/"), expected)
        with patch.object(self.store, "cli", return_value=json.dumps({"data": expected})):
            self.assertEqual(self.store.objects("synthetic-only/"), expected)
        with patch.object(self.store, "cli", return_value='{"data":{"unexpected":[]}}'):
            with self.assertRaises(backup.Refused):
                self.store.objects("synthetic-only/")
        with patch.object(self.store, "cli", return_value='{"etag":"ETAG-TOP-LEVEL"}'):
            self.assertEqual(self.store.head("test")["etag"], "ETAG-TOP-LEVEL")
        with patch.object(self.store, "cli", return_value='{"data":{"etag":"NESTED"}}'):
            self.assertEqual(self.store.head("test")["etag"], "NESTED")

    def test_empty_object_list_requires_second_full_count_query(self):
        # The authenticated OCI Cloud Shell CLI has returned successful empty
        # list stdout on some operations; never interpret blank as absence alone.
        with patch.object(self.store, "cli", side_effect=["", "0\\n"]) as call:
            self.assertEqual(self.store.objects("synthetic-only/"), [])
        self.assertEqual(call.call_count, 2)
        a, b = [q.args for q in call.call_args_list]
        self.assertIn("--all", a)
        self.assertIn("--all", b)
        self.assertEqual(b[-2:], ("--query", "length(data)"))

    def test_inconsistent_blank_list_does_not_authorize_cleanup_or_upload(self):
        for count in ("1", "-1", '"zero"', "null", "true", '{"data":[]}', "", "not-json"):
            with self.subTest(count=count), patch.object(self.store, "cli", side_effect=["", count]):
                with self.assertRaises(backup.Refused):
                    self.store.objects("synthetic-only/")
        with patch.object(self.store, "cli", return_value='{"data":[{"name":"customer/secret.rtbk"}]}'):
            with self.assertRaises(backup.Refused):
                self.store.objects("synthetic-only/")

    def test_explicit_empty_json_is_accepted_without_fallback(self):
        with patch.object(self.store, "cli", return_value='{"data":[]}') as call:
            self.assertEqual(self.store.objects("synthetic-recovery/"), [])
        call.assert_called_once()

    def test_full_object_inventory_paginated_before_cleanup_or_repeat(self):
        # OCI defaults object list to 100 entries. Refuse to mistake page 1
        # for a complete object population when gating deletions and uploads.
        first = {"data": [{"name": "synthetic-only/a"}]}
        with patch.object(self.store, "cli", return_value=json.dumps(first)) as call:
            self.assertEqual(self.store.objects("synthetic-only/"), first["data"])
        args = call.call_args.args
        self.assertIn("--all", args)
        self.assertIn("--prefix", args)
        self.assertEqual(args[args.index("--prefix") + 1], "synthetic-only/")
        self.assertNotIn("--limit", args)

    def test_full_object_inventory_rejects_non_json_or_incomplete_structure(self):
        with patch.object(self.store, "cli", return_value=""):
            with self.assertRaises(backup.Refused):
                self.store.objects("synthetic-only/")
        with patch.object(self.store, "cli", return_value='{"data":{"prefixes":["synthetic-only/"]}}'):
            with self.assertRaises(backup.Refused):
                self.store.objects("synthetic-only/")

    def test_download_requires_etag_and_bounded_private_ciphertext(self):
        filename = self.root / "remote-ciphertext.rtbk"
        raw = b"bounded test ciphertext"
        def fake_get(*args, **kwargs):
            self.assertIn("--if-match", args)
            self.assertEqual(args[args.index("--if-match") + 1], "KNOWN-ETAG")
            self.assertIn("--no-multipart", args)
            filename.write_bytes(raw)
            filename.chmod(0o600)
            return '{"output": null}'
        with patch.object(self.store, "cli", side_effect=fake_get) as downloaded:
            self.assertEqual(self.store.get("synthetic-only/test.rtbk", filename,
                                            etag="KNOWN-ETAG", max_size=len(raw)), raw)
        downloaded.assert_called_once()
        for bad in ("", "bad etag", "bad\\netag"):
            with self.subTest(etag=bad), patch.object(self.store, "cli") as download:
                with self.assertRaises(backup.Refused):
                    self.store.get("synthetic-only/test.rtbk", self.root / "new.rtbk",
                                   etag=bad, max_size=256)
                download.assert_not_called()

    def test_download_refuses_excess_of_prevalidated_head_size(self):
        target = self.root / "oversized.rtbk"
        def write_large(*args, **kwargs):
            target.write_bytes(b"a" * 21)
            target.chmod(0o600)
            return '{"output": null}'
        with patch.object(self.store, "cli", side_effect=write_large):
            with self.assertRaisesRegex(backup.Refused, "prevalidated HEAD size"):
                self.store.get("synthetic-only/test.rtbk", target,
                               etag="KNOWN-ETAG", max_size=20)

    def test_bucket_privacy_fails_closed(self):
        valid = {"name": backup.BUCKET_NAME, "public-access-type": "NoPublicAccess",
                 "storage-tier": "Standard", "versioning": "Disabled",
                 "object-events-enabled": False, "replication-enabled": False}
        with patch.object(self.store, "data", return_value=valid):
            self.store.bucket_check()
        for field, value in (("public-access-type", "ObjectRead"),
                             ("storage-tier", "Archive"), ("versioning", "Enabled"),
                             ("object-events-enabled", True)):
            with self.subTest(field=field), patch.object(self.store, "data", return_value={**valid, field: value}):
                with self.assertRaises(backup.Refused):
                    self.store.bucket_check()

    def test_cleanup_only_exact_legacy_synthetic_canary_with_etag(self):
        key = "synthetic-only/0123456789abcdef01234567.rtbk"
        raw = backup.LEGACY_MAGIC + b"N" * 12 + b"authenticated-test-ciphertext"
        calls = []
        with patch.object(backup, "LEGACY_CLEANUP", self.orphan_receipt), \
             patch.object(self.store, "bucket_check"), \
             patch.object(self.store, "objects", side_effect=[[{"name": key}], []]), \
             patch.object(self.store, "get", return_value=raw), \
             patch.object(self.store, "head", return_value={"etag": "KNOWN-ETAG", "content-length": len(raw)}), \
             patch.object(self.store, "delete_version", side_effect=lambda *args: calls.append(args)):
            self.assertEqual(backup.cleanup_legacy(self.store)["legacy_canary_cleaned"], True)
        self.assertEqual(calls, [(key, "KNOWN-ETAG")])
        self.assertEqual(self.orphan_receipt.stat().st_mode & 0o777, 0o600)
        self.assertTrue(json.loads(self.orphan_receipt.read_text())["remote_canary_deleted"])

    def test_cleanup_rejects_unrelated_or_changed_objects(self):
        wrong_names = ["synthetic-only/secret.rtbk", "customer/invoices.rtbk",
                       "synthetic-only/" + "a" * 24 + ".json"]
        for name in wrong_names:
            with self.subTest(name=name), patch.object(backup, "LEGACY_CLEANUP", self.orphan_receipt), \
                 patch.object(self.store, "bucket_check"), \
                 patch.object(self.store, "objects", return_value=[{"name": name}]), \
                 patch.object(self.store, "delete_version") as delete:
                with self.assertRaises(backup.Refused):
                    backup.cleanup_legacy(self.store)
                delete.assert_not_called()
        with patch.object(backup, "LEGACY_CLEANUP", self.orphan_receipt), \
             patch.object(self.store, "bucket_check"), \
             patch.object(self.store, "objects", return_value=[{"name": "synthetic-only/" + "b" * 24 + ".rtbk"}]), \
             patch.object(self.store, "get", return_value=b"not-the-legacy-canary"), \
             patch.object(self.store, "head", return_value={
                 "etag": "TEST-ETAG", "content-length": len(b"not-the-legacy-canary")}), \
             patch.object(self.store, "delete_version") as delete:
            with self.assertRaises(backup.Refused):
                backup.cleanup_legacy(self.store)
            delete.assert_not_called()

    def test_inspect_is_read_only(self):
        with patch.object(self.store, "bucket_check"), \
             patch.object(self.store, "objects", side_effect=[[], []]) as listed, \
             patch.object(self.store, "put") as put, \
             patch.object(self.store, "delete_version") as delete:
            self.assertEqual(backup.inspect(self.store)["legacy_test_objects"], 0)
        self.assertEqual(listed.call_count, 2)
        put.assert_not_called()
        delete.assert_not_called()


class RealEnginesOfflineTest(unittest.TestCase):
    """Uses the real seven-branch simulation + encryption, fake remote object APIs."""

    def test_seven_branch_recovery_from_remote_ciphertext(self):
        from importlib.util import find_spec
        if find_spec("cryptography") is None or find_spec("recoveryworks") is None:
            self.skipTest("requires checked-out RecoveryWorks source and optional cryptography")
        with tempfile.TemporaryDirectory(prefix="retally-oci-fake-store-") as d:
            root = Path(d)
            root.chmod(0o700)
            attempt, result = root / "attempt.json", root / "accepted.json"
            bucket = backup.OciStore({"bucket": backup.BUCKET_NAME, "namespace": "example", "region": "us-ashburn-1"})
            objects = {}

            def put(key, source):
                self.assertNotIn(key, objects)
                objects[key] = source.read_bytes()

            def get(key, path, *, etag, max_size):
                self.assertEqual(etag, "frozen-etag")
                self.assertEqual(max_size, len(objects[key]))
                raw = objects[key]
                path.write_bytes(raw)
                path.chmod(0o600)
                return raw

            def head(key):
                return {"etag": "frozen-etag", "content-length": len(objects[key])}

            def delete(key, etag):
                self.assertEqual(etag, "frozen-etag")
                del objects[key]

            with patch.object(backup, "ATTEMPT", attempt), \
                 patch.object(backup, "ACCEPTANCE", result), \
                 patch.object(bucket, "bucket_check"), \
                 patch.object(bucket, "objects", side_effect=lambda prefix: [
                     {"name": key} for key in objects if key.startswith(prefix)]), \
                 patch.object(bucket, "put", side_effect=put), \
                 patch.object(bucket, "get", side_effect=get), \
                 patch.object(bucket, "head", side_effect=head), \
                 patch.object(bucket, "delete_version", side_effect=delete):
                out = backup.synthetic_roundtrip(bucket)
            self.assertTrue(out["synthetic_off_device_restore"])
            self.assertEqual(out["branches"], 7)
            self.assertEqual(objects, {})
            self.assertTrue(attempt.is_file())
            self.assertTrue(result.is_file())
            self.assertTrue(json.loads(result.read_text())["credentials_revoked"])
            self.assertFalse(json.loads(result.read_text())["production_backup_verified"])
            with self.assertRaises(backup.Refused):
                backup.private_receipt(attempt, {"should": "never overwrite"})


if __name__ == "__main__":
    unittest.main()
