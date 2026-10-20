#!/usr/bin/env python3
"""Synthetic-only OCI Object Storage acceptance for the RETALLY workbench.

No real customer records, automatic charges, external claims, or cloud-service
provisioning. The live branch remains on HOLD. Only pre-existing private bucket
and synthetic workspace data are permitted.

Usage (from the exact reviewed repository checkout in authenticated OCI Cloud Shell):
  python deployment/oracle-always-free/oci_synthetic_backup.py --inspect
  python deployment/oracle-always-free/oci_synthetic_backup.py --cleanup-legacy-canary
  python deployment/oracle-always-free/oci_synthetic_backup.py --exercise

Secrets remain in memory, never in CLI arguments, object names, GitHub, or logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import uuid

RECEIPT_ROOT = Path.home() / ".retally-oracle"
BUCKET_RECEIPT = RECEIPT_ROOT / "sealed-backup-bucket-receipt.json"
ATTEMPT = RECEIPT_ROOT / "synthetic-backup-upload-attempt.json"
ACCEPTANCE = RECEIPT_ROOT / "synthetic-backup-acceptance.json"
LEGACY_CLEANUP = RECEIPT_ROOT / "legacy-synthetic-canary-cleanup.json"
BUCKET_NAME = "retally-synthetic-sealed-recovery"
LEGACY_MAGIC = b"RETALLY-GCM-CANARY-1"
LEGACY_OBJECT = re.compile(r"synthetic-only/[0-9a-f]{24}\.rtbk\Z")
MAX_CANARY = 4 * 1024
MAX_SEALED = 16 * 1024 * 1024  # synthetic acceptance, NOT a production snapshot allowance


class Refused(RuntimeError):
    """Fail-closed refusal that contains no secrets or OCI request dumps."""


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise Refused(message)


def _private(path: Path) -> bool:
    """No symlinks, owner-only on Unix, no ambiguous file types."""
    try:
        st = path.lstat()
    except OSError:
        return False
    return path.is_file() and not path.is_symlink() and st.st_uid == os.geteuid() and not st.st_mode & 0o077


def private_receipt(path: Path, document: dict) -> None:
    """Never replace a previous receipt; atomic O_EXCL + fsync before mutation."""
    ensure(not path.exists() and not path.is_symlink(), "Prior acceptance/attempt receipt exists; reconcile before any repeat.")
    ensure(path.parent.is_dir() and not path.parent.is_symlink(), "Private receipt directory is missing.")
    ensure(path.parent.stat().st_uid == os.geteuid() and not (path.parent.stat().st_mode & 0o077),
           "Private receipt directory must be owned by current user and inaccessible to others.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise Refused("Existing receipt blocks duplicate operation.") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(document, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_bucket_receipt(path: Path) -> dict:
    ensure(_private(path), "Bucket receipt must be a private regular file owned by this user.")
    try:
        r = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise Refused("Bucket receipt cannot be decoded.") from exc
    ensure(isinstance(r, dict) and r.get("schema") == 1, "Unsupported bucket receipt schema.")
    required = {
        "bucket": BUCKET_NAME, "status": "PRIVATE_SYNTHETIC_ONLY",
        "storage_tier": "Standard", "public_access_type": "NoPublicAccess",
        "versioning": "Disabled", "real_customer_files": False,
        "off_device_restore_verified": False,
    }
    ensure(all(type(r.get(key)) == type(value) and r[key] == value for key, value in required.items()),
           "Bucket receipt lacks mandatory synthetic-only private security settings.")
    for k in ("namespace", "region"):
        ensure(isinstance(r.get(k), str) and re.fullmatch(r"[a-zA-Z0-9_-]{2,80}", r[k]),
               "Bucket receipt has invalid provider identifiers.")
    return r


class OciStore:
    def __init__(self, r: dict):
        self.bucket = r["bucket"]
        self.namespace = r["namespace"]
        self.region = r["region"]

    def cli(self, *args: str, timeout: int = 90) -> str:
        """No implicit SDK retries, no shell, no printing OCI stderr."""
        cmd = ["oci", *args, "--region", self.region, "--output", "json", "--no-retry"]
        try:
            response = subprocess.run(cmd, text=True, capture_output=True,
                                      timeout=timeout, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise Refused("OCI CLI unavailable or timed out; operation outcome is uncertain.") from exc
        if response.returncode != 0:
            raise Refused("OCI operation failed; verify the provider resource state before retrying.")
        return response.stdout

    def data(self, *args: str, timeout: int = 90):
        raw = self.cli(*args, timeout=timeout)
        ensure(bool(raw.strip()), "OCI metadata response was empty; fail closed.")
        try:
            reply = json.loads(raw)
        except ValueError as exc:
            raise Refused("OCI returned invalid metadata JSON.") from exc
        ensure(isinstance(reply, dict) and "data" in reply,
               "OCI metadata response lacks a data field.")
        return reply["data"]

    def args(self) -> tuple[str, ...]:
        return "--namespace", self.namespace, "--bucket-name", self.bucket

    def bucket_check(self) -> None:
        b = self.data("os", "bucket", "get", *self.args())
        ensure(isinstance(b, dict) and b.get("name") == self.bucket and
               b.get("public-access-type") == "NoPublicAccess" and
               b.get("storage-tier") == "Standard" and b.get("versioning") == "Disabled" and
               b.get("object-events-enabled") in (False, None) and
               b.get("replication-enabled") in (False, None),
               "OCI bucket privacy, tier, versioning or replication state changed.")

    def objects(self, prefix: str) -> list[dict]:
        # Never treat a single OCI page as a complete remote inventory. OCI defaults
        # to 100 objects; cleanup/duplicate guards require the entire prefix.
        raw = self.data("os", "object", "list", *self.args(), "--prefix", prefix, "--all")
        # OCI 3.x returns {'data': {'objects': [...]}} on most versions,
        # and may return {'data': [...]} on some Cloud Shell releases.
        items = raw.get("objects") if isinstance(raw, dict) else raw
        ensure(isinstance(items, list) and all(isinstance(x, dict) and isinstance(x.get("name"), str)
                                               for x in items), "Unexpected OCI object list shape.")
        return items

    def get(self, name: str, destination: Path) -> bytes:
        ensure(not destination.exists() and not destination.is_symlink(), "Ciphertext download destination exists.")
        # The get CLI can return {'output': null}, not {'data': ...}.
        self.cli("os", "object", "get", *self.args(), "--name", name, "--file", str(destination),
                 "--no-multipart", timeout=120)
        ensure(_private(destination), "Downloaded ciphertext is not owner-only.")
        ensure(destination.stat().st_size <= MAX_SEALED, "Downloaded ciphertext exceeds synthetic limit.")
        return destination.read_bytes()

    def put(self, name: str, source: Path) -> None:
        ensure(_private(source) and source.stat().st_size <= MAX_SEALED,
               "Synthetic ciphertext source is not private or is oversized.")
        # CLI 'put' normally returns a *top-level* etag, with no 'data' field.
        # Command success alone is not off-device evidence; get/readback is mandatory.
        self.cli("os", "object", "put", *self.args(), "--name", name, "--file", str(source),
                 "--storage-tier", "Standard", "--no-overwrite", "--no-multipart",
                 "--verify-checksum", timeout=150)

    def head(self, name: str) -> dict:
        raw = self.cli("os", "object", "head", *self.args(), "--name", name)
        try:
            h = json.loads(raw)
        except ValueError as exc:
            raise Refused("OCI object HEAD metadata is invalid.") from exc
        # OCI object HEAD is direct JSON, not a nested data object.
        if isinstance(h, dict) and isinstance(h.get("data"), dict):
            h = h["data"]
        ensure(isinstance(h, dict) and isinstance(h.get("etag"), str) and h["etag"],
               "OCI object ETag could not be independently established.")
        return h

    def delete_version(self, name: str, etag: str) -> None:
        ensure(isinstance(etag, str) and bool(etag), "Conditional delete needs an original ETag.")
        # --if-match prevents deletion of a different object after an unknown overwrite.
        self.cli("os", "object", "delete", *self.args(), "--name", name,
                 "--if-match", etag, "--force")


def inspect(store: OciStore) -> dict:
    store.bucket_check()
    legacy = store.objects("synthetic-only/")
    recovery = store.objects("synthetic-recovery/")
    return {
        "bucket_private": True, "legacy_test_objects": len(legacy),
        "recovery_test_objects": len(recovery),
        "off_device_production_backup_verified": False,
    }


def cleanup_legacy(store: OciStore) -> dict:
    """Delete only the ONE known, unreachable 2026-10-20 synthetic canary.

    Never perform a bulk delete; require specific key syntax, verified canary
    magic + bounded length, ETag-conditional delete, and new empty inventory.
    """
    ensure(not LEGACY_CLEANUP.exists() and not LEGACY_CLEANUP.is_symlink(),
           "Legacy cleanup already recorded; refuse repeat.")
    store.bucket_check()
    items = store.objects("synthetic-only/")
    ensure(len(items) == 1, "Legacy cleanup requires exactly one candidate.")
    name = items[0]["name"]
    ensure(LEGACY_OBJECT.fullmatch(name) is not None,
           "Legacy object name is not the exact prior synthetic canary format.")
    with tempfile.TemporaryDirectory(prefix="retally-orphan-reconcile-") as home:
        target = Path(home) / "ciphertext.rtbk"
        raw = store.get(name, target)
        ensure(40 <= len(raw) <= MAX_CANARY and raw.startswith(LEGACY_MAGIC),
               "Remote object cannot be proven to be the prior small synthetic canary.")
    h = store.head(name)
    ensure(int(h.get("content-length", len(raw))) == len(raw),
           "Remote object length changed before conditional deletion.")
    store.delete_version(name, h["etag"])
    ensure(not store.objects("synthetic-only/"),
           "Legacy canary deletion was not confirmed by independent listing.")
    result = {"schema": 1, "synthetic_only": True, "remote_canary_deleted": True,
              "ciphertext_sha256": sha(raw), "production_backup_verified": False}
    private_receipt(LEGACY_CLEANUP, result)
    return {"legacy_canary_cleaned": True, "remaining": 0, "production_backup_verified": False}


def synthetic_roundtrip(store: OciStore) -> dict:
    """Exercise actual RecoveryWorks source adapters, encryption and restore."""
    ensure(not ATTEMPT.exists() and not ACCEPTANCE.exists(),
           "Prior synthetic backup attempt/result exists; reconcile before repeat.")
    store.bucket_check()
    ensure(not store.objects("synthetic-only/") and not store.objects("synthetic-recovery/"),
           "Existing synthetic objects must be reconciled before testing.")

    # Late imports: read-only inspection can run on stock OCI Cloud Shell.
    from recoveryworks.seven_branch_simulation import seed, exercise
    from recoveryworks.offsite_archive import seal_file, verify_file, unseal_bytes, restore_file
    from recoveryworks.workbench import Workspace

    with tempfile.TemporaryDirectory(prefix="retally-recovery-synthetic-") as temp:
        base = Path(temp)
        work, roles = seed(base / "synthetic")
        report = exercise(work, roles)
        ensure(report["simulation"] is True and len(report["branches"]) == 7 and
               all(v["journey"] == "PASS" for v in report["branches"].values()) and
               report["real_customers"] == report["real_recovered_cents"] == 0 and
               report["external_actions_sent"] == 0,
               "Actual workbench synthetic acceptance did not pass.")
        snapshots = list((work.root / "backups").glob("*.json"))
        ensure(len(snapshots) == 1 and _private(snapshots[0]),
               "Expected exactly one validated owner-only synthetic snapshot.")

        passphrase = secrets.token_urlsafe(48)  # SYNTHETIC test only; never persisted
        sealed = base / "sealed.rtbk"
        locally = seal_file(snapshots[0], sealed, passphrase)
        ensure(locally["verified_locally"] and not locally["off_device_verified"],
               "Local source seal verification failed.")
        ciphertext = sealed.read_bytes()
        ensure(0 < len(ciphertext) < MAX_SEALED and b"SIMULATED-CUSTOMER-ONLY" not in ciphertext,
               "Ciphertext is oversized or contains the simulated customer ID in plaintext.")
        fingerprint = sha(ciphertext)
        key = "synthetic-recovery/" + uuid.uuid4().hex + ".rtbk"
        private_receipt(ATTEMPT, {"schema": 1, "synthetic_only": True,
                                  "status": "UNCERTAIN_UNTIL_REMOTE_READBACK",
                                  "object_name": key, "sealed_sha256": fingerprint,
                                  "production_backup_verified": False})
        # If the network times out after the provider accepts PUT, the marker
        # remains and no automatic second PUT or DELETE is allowed.
        store.put(key, sealed)
        downloaded = base / "downloaded.rtbk"
        remote_raw = store.get(key, downloaded)
        ensure(sha(remote_raw) == fingerprint, "Downloaded ciphertext SHA-256 mismatch.")
        verified = verify_file(downloaded, passphrase)
        ensure(verified["restore_verified"] is True and
               verified["sealed_sha256"] == fingerprint,
               "Remote archive could not be restored by actual encryption code.")
        restored = base / "isolated-restore"
        restored_report = restore_file(downloaded, restored, passphrase)
        ensure(restored_report["restore_verified"] and restored_report["all_credentials_revoked"],
               "Restored workspace did not revoke all previous role credentials.")
        for token in roles.values():
            try:
                Workspace(restored).principal(token)
            except PermissionError:
                pass
            else:
                raise Refused("Restored workspace resurrected an original role credential.")
        altered = bytearray(remote_raw)
        altered[-1] ^= 1
        try:
            unseal_bytes(bytes(altered), passphrase)
        except ValueError:
            pass
        else:
            raise Refused("Modified ciphertext was accepted; AEAD integrity is broken.")

        h = store.head(key)
        store.delete_version(key, h["etag"])
        ensure(not store.objects("synthetic-recovery/"),
               "OCI test object deletion unverified; stop, do not re-upload.")
        result = {"schema": 1, "simulation": True, "branches_verified": 7,
                  "remote_ciphertext_sha256": fingerprint,
                  "remote_readback_verified": True, "actual_restore_verified": True,
                  "credentials_revoked": True, "tampered_archive_rejected": True,
                  "temporary_remote_object_deleted": True, "customer_files": 0,
                  "production_backup_verified": False, "separate_key_escrow_verified": False}
        private_receipt(ACCEPTANCE, result)
        return {"synthetic_off_device_restore": True, "branches": 7,
                "remote_ciphertext_verified": True, "tamper_rejected": True,
                "temporary_object_removed": True, "production_backup_verified": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--inspect", action="store_true", help="Read-only provider bucket/objects")
    actions.add_argument("--cleanup-legacy-canary", action="store_true",
                         help="Delete only the exact small synthetic orphan with conditional ETag")
    actions.add_argument("--exercise", action="store_true",
                         help="Run seven real-engine synthetic journeys and remote archive recovery")
    args = parser.parse_args(argv)
    os.umask(0o077)
    receipt = parse_bucket_receipt(BUCKET_RECEIPT)
    store = OciStore(receipt)
    if args.inspect:
        output = inspect(store)
    elif args.cleanup_legacy_canary:
        output = cleanup_legacy(store)
    else:
        output = synthetic_roundtrip(store)
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Refused as exc:
        print("STOP (synthetic acceptance not production proof):", str(exc), file=sys.stderr)
        raise SystemExit(2)
