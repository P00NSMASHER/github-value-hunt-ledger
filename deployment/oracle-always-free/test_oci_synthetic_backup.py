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
            self.assertEqual(self.store.put("synthetic-recovery/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.rtbk", source),
                             "OCI-TEST-ETAG")
        cmd = run.call_args.args[0]
        self.assertIn("--no-overwrite", cmd)
        self.assertIn("--verify-checksum", cmd)
        self.assertIn("--no-multipart", cmd)
        self.assertNotIn("--force", cmd)
        self.assertIn("Standard", cmd)

    def test_cli_no_overwrite_success_is_not_a_successful_put(self):
        # OCI documents exit 0 and a top-level 'output' message when the
        # object already exists and --no-overwrite skips the upload.
        source = self.root / "canary.rtbk"
        source.write_bytes(b"encrypted-fixture")
        source.chmod(0o600)
        replies = [
            '{"output":"The object already exists and was not overwritten"}',
            '{"output":null}', "",
            '{"data":{"etag":"WRONG-LEVEL"}}', "not-json",
            '{"etag":null}', '{"etag":"bad etag"}',
        ]
        for reply in replies:
            with self.subTest(reply=reply), patch.object(self.store, "cli",
                                                          return_value=reply) as cli:
                with self.assertRaises(backup.Refused):
                    self.store.put("synthetic-recovery/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.rtbk", source)
                cli.assert_called_once()

    def test_writes_are_restricted_to_exact_synthetic_key_patterns(self):
        source = self.root / "synthetic-ciphertext.rtbk"
        source.write_bytes(b"synthetic data only")
        source.chmod(0o600)
        forbidden = [
            "customer/invoices.rtbk",
            "synthetic-only/0123456789abcdef01234567.rtbk",
            "synthetic-recovery/not-a-random-key.rtbk",
            "synthetic-recovery/" + "g"*32 + ".rtbk",
            "synthetic-recovery/" + "a"*32 + ".json",
            "synthetic-recovery/" + "a"*32 + ".rtbk/../customers",
            "", None,
        ]
        with patch.object(self.store, "cli") as cli:
            for key in forbidden:
                with self.subTest(key=key):
                    with self.assertRaises(backup.Refused):
                        self.store.put(key, source)
                    with self.assertRaises(backup.Refused):
                        self.store.delete_version(key, "trusted-etag")
            cli.assert_not_called()

    def test_exact_fresh_key_delete_requires_etag(self):
        key = "synthetic-recovery/" + "c"*32 + ".rtbk"
        with patch.object(self.store, "cli", return_value="") as cli:
            with self.assertRaises(backup.Refused):
                self.store.delete_version(key, "")
            cli.assert_not_called()
            self.store.delete_version(key, "etag-frozen")
            self.assertEqual(cli.call_count, 1)
            args = cli.call_args.args
            self.assertIn("--if-match", args)
            self.assertEqual(args[args.index("--if-match") + 1], "etag-frozen")
            self.assertIn(key, args)

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
        with patch.object(self.store, "cli", side_effect=["", "0\n"]) as call:
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
            self.assertEqual(backup.cleanup_legacy(
                self.store, expected_object_name=key,
                expected_sha256=backup.sha(raw))["legacy_canary_cleaned"], True)
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
                    backup.cleanup_legacy(self.store, expected_object_name=name,
                                          expected_sha256="0" * 64)
                delete.assert_not_called()
        with patch.object(backup, "LEGACY_CLEANUP", self.orphan_receipt), \
             patch.object(self.store, "bucket_check"), \
             patch.object(self.store, "objects", return_value=[{"name": "synthetic-only/" + "b" * 24 + ".rtbk"}]), \
             patch.object(self.store, "get", return_value=b"not-the-legacy-canary"), \
             patch.object(self.store, "head", return_value={
                 "etag": "TEST-ETAG", "content-length": len(b"not-the-legacy-canary")}), \
             patch.object(self.store, "delete_version") as delete:
            with self.assertRaises(backup.Refused):
                backup.cleanup_legacy(
                    self.store,
                    expected_object_name="synthetic-only/" + "b" * 24 + ".rtbk",
                    expected_sha256=backup.sha(b"not-the-legacy-canary"))
            delete.assert_not_called()

    def test_identical_pattern_magic_and_etag_are_not_original_authority(self):
        key = "synthetic-only/0123456789abcdef01234567.rtbk"
        raw = backup.LEGACY_MAGIC + b"N" * 12 + b"authenticated-test-ciphertext"
        with patch.object(backup, "LEGACY_CLEANUP", self.orphan_receipt), \
             patch.object(self.store, "bucket_check"), \
             patch.object(self.store, "objects", return_value=[{"name": key}]), \
             patch.object(self.store, "head", return_value={
                 "etag": "KNOWN-ETAG", "content-length": len(raw)}), \
             patch.object(self.store, "get", return_value=raw), \
             patch.object(self.store, "delete_version") as delete:
            for name, expected in [
                (key, "0"*64), (key, ""), (None, backup.sha(raw)),
                ("synthetic-only/" + "f"*24 + ".rtbk", backup.sha(raw)),
            ]:
                with self.subTest(name=name, expected=expected), self.assertRaises(backup.Refused):
                    backup.cleanup_legacy(self.store, expected_object_name=name,
                                          expected_sha256=expected)
            delete.assert_not_called()
        self.assertFalse(self.orphan_receipt.exists())

    def test_inspect_is_read_only(self):
        with patch.object(self.store, "bucket_check"), \
             patch.object(self.store, "objects", side_effect=[[], []]) as listed, \
             patch.object(self.store, "put") as put, \
             patch.object(self.store, "delete_version") as delete:
            self.assertEqual(backup.inspect(self.store)["legacy_test_objects"], 0)
        self.assertEqual(listed.call_count, 2)
        put.assert_not_called()
        delete.assert_not_called()



class LegacyOrphanIsolationTests(unittest.TestCase):
    """A historical unverified orphan must never be silently deleted or reused."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="retally-orphan-quarantine-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o700)
        self.receipt = self.root / "quarantine.json"
        self.store = backup.OciStore({
            "bucket": backup.BUCKET_NAME,
            "namespace": "syntheticnamespace",
            "region": "us-ashburn-1",
        })
        self.key = "synthetic-only/0123456789abcdef01234567.rtbk"
        self.raw = backup.LEGACY_MAGIC + b"N" * 12 + b"historical-synthetic-ciphertext-test"

    def test_verifiable_small_orphan_preserved_with_private_untrusted_receipt(self):
        objects = [{"name": self.key, "size": len(self.raw)}]

        def fetch(key, path, *, etag, max_size):
            self.assertEqual((key, etag, max_size),
                             (self.key, "etag-legacy", backup.MAX_CANARY))
            path.write_bytes(self.raw)
            path.chmod(0o600)
            return self.raw

        with (patch.object(backup, "LEGACY_QUARANTINE", self.receipt),
              patch.object(self.store, "head",
                           return_value={"etag": "etag-legacy", "content-length": str(len(self.raw)),
                                         "storage-tier": "Standard"}),
              patch.object(self.store, "get", side_effect=fetch) as get,
              patch.object(self.store, "objects", return_value=objects),
              patch.object(self.store, "delete_version") as delete):
            result = backup.quarantine_legacy_orphan(self.store, objects)
        self.assertTrue(result["legacy_orphan_quarantined"])
        self.assertFalse(result["legacy_orphan_deleted"])
        self.assertEqual(get.call_count, 1)
        delete.assert_not_called()
        self.assertEqual(self.receipt.stat().st_mode & 0o777, 0o600)
        report = json.loads(self.receipt.read_text())
        self.assertEqual(report["remote_observed_sha256"], backup.sha(self.raw))
        self.assertFalse(report["original_upload_identity_independently_verified"])
        self.assertFalse(report["legacy_object_deleted"])
        self.assertEqual(report["status"], "QUARANTINED_UNRESOLVED_DO_NOT_DELETE")

    def test_multiple_or_wrong_named_orphans_are_never_quarantined(self):
        for items in ([{"name": self.key}, {"name": "synthetic-only/" + "b"*24 + ".rtbk"}],
                      [{"name": "customers/invoices.rtbk"}],
                      [{"name": "synthetic-only/not-hex.rtbk"}], []):
            with (self.subTest(items=items),
                  patch.object(backup, "LEGACY_QUARANTINE", self.receipt),
                  patch.object(self.store, "get") as get,
                  patch.object(self.store, "delete_version") as delete):
                with self.assertRaises(backup.Refused):
                    backup.quarantine_legacy_orphan(self.store, items)
                get.assert_not_called()
                delete.assert_not_called()
        self.assertFalse(self.receipt.exists())

    def test_changed_remote_size_or_wrong_magic_fails_closed(self):
        items = [{"name": self.key, "size": len(self.raw)}]
        for size, content in ((backup.MAX_CANARY + 1, self.raw),
                              (len(self.raw), b"WRONG-MAGIC" + self.raw),
                              (len(self.raw), self.raw[:-1])):
            with (self.subTest(size=size, contentlen=len(content)),
                  patch.object(backup, "LEGACY_QUARANTINE", self.receipt),
                  patch.object(self.store, "head", return_value={
                      "etag": "etag-legacy", "content-length": str(size),
                      "storage-tier": "Standard"}),
                  patch.object(self.store, "get", return_value=content),
                  patch.object(self.store, "delete_version") as delete):
                with self.assertRaises(backup.Refused):
                    backup.quarantine_legacy_orphan(self.store, items)
                delete.assert_not_called()
        self.assertFalse(self.receipt.exists())

    def test_final_legacy_preservation_refuses_changed_etag_or_ciphertext(self):
        original = {"_name": self.key, "_etag": "etag-legacy",
                    "_length": len(self.raw), "_sha256": backup.sha(self.raw)}
        objects = [{"name": self.key, "size": len(self.raw)}]
        with (patch.object(self.store, "objects", return_value=objects),
              patch.object(self.store, "head", return_value={
                  "etag": "changed-etag", "content-length": len(self.raw)}),
              patch.object(self.store, "get") as get):
            with self.assertRaisesRegex(backup.Refused, "ETag changed"):
                backup.confirm_legacy_orphan_unchanged(
                    self.store, original, self.root / "final-check.rtbk")
            get.assert_not_called()
        with (patch.object(self.store, "objects", return_value=objects),
              patch.object(self.store, "head", return_value={
                  "etag": "etag-legacy", "content-length": len(self.raw)}),
              patch.object(self.store, "get", return_value=b"X" + self.raw[1:])):
            with self.assertRaisesRegex(backup.Refused, "ciphertext changed"):
                backup.confirm_legacy_orphan_unchanged(
                    self.store, original, self.root / "final-check.rtbk")

    def test_existing_quarantine_blocks_repeated_acceptance(self):
        self.receipt.write_text('{"previous":true}', encoding="ascii")
        with (patch.object(backup, "LEGACY_QUARANTINE", self.receipt),
              patch.object(self.store, "get") as get,
              patch.object(self.store, "delete_version") as delete):
            with self.assertRaises(backup.Refused):
                backup.quarantine_legacy_orphan(self.store, [{"name": self.key}])
            get.assert_not_called()
            delete.assert_not_called()

    def test_unapproved_orphan_blocks_new_upload(self):
        with (patch.object(self.store, "bucket_check"),
              patch.object(self.store, "objects",
                           side_effect=[[{"name": self.key}], []]),
              patch.object(self.store, "put") as put):
            with self.assertRaisesRegex(backup.Refused, "explicit quarantine"):
                backup.synthetic_roundtrip(self.store)
            put.assert_not_called()

    def test_orphan_preservation_flag_only_allowed_with_exercise(self):
        with self.assertRaisesRegex(backup.Refused, "only supported"):
            backup.main(["--inspect", "--preserve-legacy-orphan"])

    def test_quarantine_flag_requires_a_real_historical_orphan(self):
        with (patch.object(self.store, "bucket_check"),
              patch.object(self.store, "objects", side_effect=[[], []]),
              patch.object(self.store, "put") as put):
            with self.assertRaisesRegex(backup.Refused, "no legacy"):
                backup.synthetic_roundtrip(self.store, preserve_legacy_orphan=True)
            put.assert_not_called()


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
                return "frozen-etag"

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


    def test_mismatched_provider_upload_and_head_etag_refuses_restore(self):
        from importlib.util import find_spec
        if find_spec("cryptography") is None or find_spec("recoveryworks") is None:
            self.skipTest("requires actual workbench and optional encryption module")
        with tempfile.TemporaryDirectory(prefix="retally-oci-head-mismatch-") as folder:
            root = Path(folder)
            root.chmod(0o700)
            store = backup.OciStore({
                "bucket": backup.BUCKET_NAME, "namespace": "example", "region": "us-ashburn-1"
            })
            with (patch.object(backup, "ATTEMPT", root / "attempt.json"),
                  patch.object(backup, "ACCEPTANCE", root / "acceptance.json"),
                  patch.object(store, "bucket_check"),
                  patch.object(store, "objects", return_value=[]),
                  patch.object(store, "put", return_value="etag-uploaded"),
                  patch.object(store, "head", return_value={"etag": "etag-changed"}),
                  patch.object(store, "get") as get,
                  patch.object(store, "delete_version") as delete):
                with self.assertRaisesRegex(backup.Refused, "ETag differs"):
                    backup.synthetic_roundtrip(store)
                get.assert_not_called()
                delete.assert_not_called()
            self.assertTrue((root / "attempt.json").is_file())
            self.assertFalse((root / "acceptance.json").exists())

    def test_real_seven_branch_roundtrip_leaves_unverified_orphan_intact(self):
        from importlib.util import find_spec
        if find_spec("cryptography") is None or find_spec("recoveryworks") is None:
            self.skipTest("requires source and optional cryptography")
        with tempfile.TemporaryDirectory(prefix="retally-oci-quarantined-seven-branch-") as folder:
            home = Path(folder)
            home.chmod(0o700)
            attempt = home / "attempt.json"
            acceptance = home / "acceptance.json"
            quarantine = home / "untrusted-legacy.json"
            legacy_key = "synthetic-only/1234567890abcdef12345678.rtbk"
            historical = backup.LEGACY_MAGIC + b"N" * 12 + b"synthetic-old-gcm-canary-do-not-delete"
            objects = {legacy_key: historical}
            actions = []
            store = backup.OciStore({
                "bucket": backup.BUCKET_NAME, "namespace": "example", "region": "us-ashburn-1"
            })

            def listing(prefix):
                return [{"name": key, "size": len(value)}
                        for key, value in objects.items() if key.startswith(prefix)]

            def put(key, source):
                self.assertTrue(key.startswith("synthetic-recovery/"))
                self.assertNotIn(key, objects)
                objects[key] = source.read_bytes()
                actions.append(("put", key))
                return "frozen-etag"

            def get(key, destination, *, etag, max_size):
                self.assertEqual(etag, "frozen-etag")
                raw = objects[key]
                self.assertLessEqual(len(raw), max_size)
                destination.write_bytes(raw)
                destination.chmod(0o600)
                actions.append(("get", key))
                return raw

            def head(key):
                return {"etag": "frozen-etag", "content-length": len(objects[key]),
                        "storage-tier": "Standard"}

            def delete(key, etag):
                self.assertTrue(key.startswith("synthetic-recovery/"))
                self.assertEqual(etag, "frozen-etag")
                actions.append(("delete", key))
                del objects[key]

            with (patch.object(backup, "ATTEMPT", attempt),
                  patch.object(backup, "ACCEPTANCE", acceptance),
                  patch.object(backup, "LEGACY_QUARANTINE", quarantine),
                  patch.object(store, "bucket_check"),
                  patch.object(store, "objects", side_effect=listing),
                  patch.object(store, "put", side_effect=put),
                  patch.object(store, "get", side_effect=get),
                  patch.object(store, "head", side_effect=head),
                  patch.object(store, "delete_version", side_effect=delete)):
                result = backup.synthetic_roundtrip(
                    store, preserve_legacy_orphan=True)
            self.assertTrue(result["synthetic_off_device_restore"])
            self.assertTrue(result["legacy_orphan_quarantined"])
            self.assertFalse(result["legacy_orphan_deleted"])
            self.assertEqual(objects, {legacy_key: historical})
            self.assertEqual(len([a for a in actions if a[0] == "put"]), 1)
            self.assertEqual(len([a for a in actions if a[0] == "delete"]), 1)
            self.assertEqual(len([a for a in actions if a[0] == "get"]), 3)
            self.assertEqual([a[1].split("/")[0] for a in actions if a[0] == "get"],
                             ["synthetic-only", "synthetic-recovery", "synthetic-only"])
            self.assertTrue(quarantine.exists())
            self.assertEqual(quarantine.stat().st_mode & 0o777, 0o600)
            untrusted = json.loads(quarantine.read_text())
            self.assertEqual(untrusted["legacy_object_name"], legacy_key)
            self.assertFalse(untrusted["original_upload_identity_independently_verified"])
            restored = json.loads(acceptance.read_text())
            self.assertTrue(restored["credentials_revoked"])
            self.assertTrue(restored["legacy_orphan_quarantined"])
            self.assertFalse(restored["legacy_orphan_deleted"])
            self.assertFalse(restored["production_backup_verified"])


if __name__ == "__main__":
    unittest.main()
