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
LEGACY_DELETE_ATTEMPT = RECEIPT_ROOT / "legacy-synthetic-canary-delete-attempt.json"
LEGACY_QUARANTINE = RECEIPT_ROOT / "legacy-orphan-quarantine.json"
BUCKET_NAME = "retally-synthetic-sealed-recovery"
LEGACY_MAGIC = b"RETALLY-GCM-CANARY-1"
LEGACY_OBJECT = re.compile(r"synthetic-only/[0-9a-f]{24}\.rtbk\Z")
RECOVERY_OBJECT = re.compile(r"synthetic-recovery/[0-9a-f]{32}\.rtbk\Z")
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

    def raw_bucket(self) -> dict:
        """Read the signed OCI REST representation without older SDK field loss.

        Cloud Shell's typed bucket GET may return null/omit newly introduced
        audit or soft-delete fields. Never treat omission as 'Disabled'.
        """
        ensure(self.region == "us-ashburn-1" and self.bucket == BUCKET_NAME and
               re.fullmatch(r"[A-Za-z0-9_-]{2,80}", self.namespace) is not None,
               "Raw provider audit requires the original exact Ashburn synthetic bucket.")
        uri = ("https://objectstorage.us-ashburn-1.oraclecloud.com/n/" +
               self.namespace + "/b/" + self.bucket)
        payload = self.cli("raw-request", "--http-method", "GET", "--target-uri", uri)
        try:
            response = json.loads(payload)
        except ValueError as exc:
            raise Refused("Authenticated OCI raw bucket GET returned invalid JSON.") from exc
        ensure(isinstance(response, dict) and response.get("status") == "200 OK"
               and isinstance(response.get("data"), dict),
               "Authenticated OCI raw bucket GET was not an exact HTTP 200 data object.")
        return response["data"]

    def bucket_check(self) -> None:
        b = self.data("os", "bucket", "get", *self.args())
        ensure(isinstance(b, dict) and b.get("name") == self.bucket and
               b.get("namespace") == self.namespace and
               b.get("public-access-type") == "NoPublicAccess" and
               b.get("storage-tier") == "Standard" and b.get("versioning") == "Disabled" and
               b.get("object-events-enabled") is False and
               b.get("replication-enabled") is False and
               "auto-tiering" in b and b["auto-tiering"] in (None, "Disabled") and
               "object-lifecycle-policy-etag" in b and b["object-lifecycle-policy-etag"] is None,
               "OCI bucket privacy, tier, auto-tiering, lifecycle, events or replication state changed.")
        # The typed CLI may omit these newer properties, but may not contradict
        # the independent signed raw response (particularly a paid KMS key).
        ensure("kms-key-id" in b and b["kms-key-id"] is None and
               b.get("object-level-audit-mode") in (None, "Disabled"),
               "Typed OCI bucket reports an unapproved KMS key or audit mode.")
        typed_soft = b.get("soft-delete-policy")
        ensure(typed_soft is None or
               (isinstance(typed_soft, dict) and
                isinstance(typed_soft.get("current-policy"), dict) and
                typed_soft["current-policy"].get("soft-delete-mode") == "Disabled" and
                "next-policy" in typed_soft and typed_soft["next-policy"] is None),
               "Typed OCI bucket reports an unsafe soft-delete policy.")

        raw = self.raw_bucket()
        # ETag binding means the two provider reads describe the same exact
        # bucket configuration, not separate moments with changed policy.
        ensure(isinstance(b.get("etag"), str) and bool(b["etag"]) and
               raw.get("etag") == b["etag"] and raw.get("name") == self.bucket and
               raw.get("namespace") == self.namespace and
               raw.get("publicAccessType") == "NoPublicAccess" and
               raw.get("storageTier") == "Standard" and raw.get("versioning") == "Disabled",
               "Typed and raw OCI bucket identity, ETag or core safety fields disagree.")
        ensure("kmsKeyId" in raw and raw["kmsKeyId"] is None and
               raw.get("objectLevelAuditMode") == "Disabled" and
               raw.get("objectEventsEnabled") is False and
               raw.get("replicationEnabled") is False and
               "objectLifecyclePolicyEtag" in raw and
               raw["objectLifecyclePolicyEtag"] is None and
               "autoTiering" in raw and raw["autoTiering"] in (None, "Disabled"),
               "Raw OCI bucket has unapproved KMS, audit, tier, events, replication or lifecycle state.")
        deletion = raw.get("softDeletePolicy")
        ensure(isinstance(deletion, dict) and
               isinstance(deletion.get("currentPolicy"), dict) and
               deletion["currentPolicy"].get("softDeleteMode") == "Disabled" and
               "nextPolicy" in deletion and deletion["nextPolicy"] is None,
               "Raw OCI soft-delete is enabled, scheduled, or unknown; deletion proof is unsafe.")

    def objects(self, prefix: str) -> list[dict]:
        # Never treat a single OCI page as a complete remote inventory. OCI defaults
        # to 100 objects; cleanup/duplicate guards require the entire prefix.
        ensure(prefix in ("synthetic-only/", "synthetic-recovery/"),
               "Only known synthetic prefixes may be inspected.")
        args = ("os", "object", "list", *self.args(), "--prefix", prefix, "--all")
        raw = self.cli(*args)
        if not raw.strip():
            # Some OCI Cloud Shell CLI versions emit no JSON when a successful
            # list operation has zero entries. Treating blank stdout as [] on
            # its own would conceal an incomplete or unauthorized inventory.
            # Independently query the count across ALL pages; only an explicit
            # integer zero, reported with a successful CLI response, is enough.
            second = self.cli(*args, "--query", "length(data)")
            try:
                count = json.loads(second.strip())
            except ValueError as exc:
                raise Refused("OCI empty object population could not be independently confirmed.") from exc
            ensure(type(count) is int and count == 0,
                   "OCI object list disagrees with the independent full-population count.")
            return []
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise Refused("OCI object inventory returned invalid JSON.") from exc
        ensure(isinstance(parsed, dict) and "data" in parsed,
               "OCI object inventory lacks the data population.")
        # OCI --all must have consumed every page. A remaining continuation
        # forbids any claim of an empty prefix, safe deletion or fresh upload.
        ensure(not parsed.get("next-start-with") and not parsed.get("opc-next-page"),
               "OCI object inventory still has a continuation; full pagination unverified.")
        data = parsed["data"]
        # OCI may return either {'data': {'objects': [...]}} or
        # {'data': [...]}, depending on installed CLI version.
        items = data.get("objects") if isinstance(data, dict) else data
        ensure(isinstance(items, list) and all(isinstance(x, dict) and isinstance(x.get("name"), str)
                                               for x in items), "Unexpected OCI object list shape.")
        ensure(all(x["name"].startswith(prefix) for x in items),
               "OCI object inventory includes objects outside the requested synthetic prefix.")
        return items

    def get(self, name: str, destination: Path, *, etag: str, max_size: int = MAX_SEALED) -> bytes:
        ensure(not destination.exists() and not destination.is_symlink(), "Ciphertext download destination exists.")
        ensure(isinstance(etag, str) and
               re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", etag) is not None,
               "Download needs one verified OCI object ETag without unsafe characters.")
        ensure(type(max_size) is int and 0 < max_size <= MAX_SEALED,
               "Download size bound must be a positive synthetic-only limit.")
        # HEAD must first confirm content-length <= max_size. The If-Match
        # freezes that bounded version so a concurrent overwrite cannot
        # substitute a larger or different object during download.
        # OCI GET returns {'output': null}, not {'data': ...}.
        self.cli("os", "object", "get", *self.args(), "--name", name,
                 "--file", str(destination), "--if-match", etag,
                 "--no-multipart", timeout=120)
        ensure(_private(destination), "Downloaded ciphertext is not owner-only.")
        ensure(destination.stat().st_size <= max_size,
               "Downloaded ciphertext exceeds prevalidated HEAD size bound.")
        return destination.read_bytes()

    def put(self, name: str, source: Path) -> str:
        ensure(isinstance(name, str) and RECOVERY_OBJECT.fullmatch(name) is not None,
               "New uploads must use a 32-hex synthetic-recovery object key.")
        ensure(_private(source) and source.stat().st_size <= MAX_SEALED,
               "Synthetic ciphertext source is not private or is oversized.")
        # OCI --no-overwrite may return exit code ZERO with an "already exists"
        # output instead of uploading. Require the documented TOP-LEVEL ETag
        # before treating the PUT as positively acknowledged; never require
        # an unrelated nested 'data' field, and never retry uncertain writes.
        raw = self.cli("os", "object", "put", *self.args(), "--name", name, "--file", str(source),
                       "--storage-tier", "Standard", "--no-overwrite", "--no-multipart",
                       "--verify-checksum", timeout=150)
        try:
            reply = json.loads(raw)
        except ValueError as exc:
            raise Refused("OCI PUT lacks a verifiable acknowledgement; reconcile the attempt receipt before retry.") from exc
        ensure(isinstance(reply, dict) and isinstance(reply.get("etag"), str) and
               re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", reply["etag"]) is not None,
               "OCI PUT did not confirm a new upload ETag; object may already exist. Reconcile before retry.")
        return reply["etag"]

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
        ensure(isinstance(name, str) and
               (RECOVERY_OBJECT.fullmatch(name) is not None or
                LEGACY_OBJECT.fullmatch(name) is not None),
               "Refusing to delete an object outside the approved synthetic key formats.")
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


def cleanup_legacy(store: OciStore, *, expected_object_name: str,
                   expected_sha256: str) -> dict:
    """Delete only the ONE known, unreachable 2026-10-20 synthetic canary.

    Never perform a bulk delete; require specific key syntax, verified canary
    magic + bounded length, ETag-conditional delete, and new empty inventory.
    """
    ensure(not LEGACY_CLEANUP.exists() and not LEGACY_CLEANUP.is_symlink() and
           not LEGACY_DELETE_ATTEMPT.exists() and not LEGACY_DELETE_ATTEMPT.is_symlink(),
           "Legacy cleanup or uncertain delete attempt already recorded; refuse repeat.")
    # The current object name/magic cannot independently establish the
    # ORIGINAL uploaded ciphertext identity. Require a separately frozen
    # approved exact name and SHA-256 before any provider deletion.
    ensure(isinstance(expected_object_name, str)
           and LEGACY_OBJECT.fullmatch(expected_object_name) is not None,
           "Legacy deletion requires the preapproved original exact object key.")
    ensure(isinstance(expected_sha256, str)
           and re.fullmatch(r"[a-f0-9]{64}", expected_sha256) is not None,
           "Legacy deletion requires a preapproved original ciphertext SHA-256.")
    store.bucket_check()
    items = store.objects("synthetic-only/")
    ensure(len(items) == 1, "Legacy cleanup requires exactly one candidate.")
    name = items[0]["name"]
    ensure(name == expected_object_name,
           "Provider object key changed since the original independent approval.")
    ensure(LEGACY_OBJECT.fullmatch(name) is not None,
           "Legacy object name is not the exact prior synthetic canary format.")
    h = store.head(name)
    try:
        expected_length = int(h["content-length"])
    except (KeyError, TypeError, ValueError) as exc:
        raise Refused("Legacy object's HEAD size is missing or invalid.") from exc
    ensure(40 <= expected_length <= MAX_CANARY,
           "Legacy object is not a bounded small synthetic canary.")
    if "size" in items[0]:
        ensure(items[0]["size"] == expected_length,
               "Legacy list size disagrees with remote HEAD size.")
    with tempfile.TemporaryDirectory(prefix="retally-orphan-reconcile-") as home:
        target = Path(home) / "ciphertext.rtbk"
        raw = store.get(name, target, etag=h["etag"], max_size=MAX_CANARY)
        ensure(len(raw) == expected_length and raw.startswith(LEGACY_MAGIC),
               "Remote object cannot be proven to be the prior small synthetic canary.")
    ensure(sha(raw) == expected_sha256,
           "Remote ciphertext SHA-256 differs from the previously approved original.")
    # Persist exact deletion intent BEFORE the provider request: a connection
    # timeout can mean the conditional DELETE succeeded remotely. Never retry
    # an uncertain deletion or replace its immutable evidence automatically.
    private_receipt(LEGACY_DELETE_ATTEMPT, {
        "schema": 1, "synthetic_only": True, "object_name": name,
        "original_ciphertext_sha256": expected_sha256, "frozen_etag": h["etag"],
        "status": "DELETE_OUTCOME_UNCERTAIN_UNTIL_REMOTE_RECONCILIATION",
        "production_backup_verified": False,
    })
    store.delete_version(name, h["etag"])
    ensure(not store.objects("synthetic-only/"),
           "Legacy canary deletion was not confirmed by independent listing.")
    result = {"schema": 1, "synthetic_only": True, "remote_canary_deleted": True,
              "ciphertext_sha256": sha(raw), "production_backup_verified": False}
    private_receipt(LEGACY_CLEANUP, result)
    return {"legacy_canary_cleaned": True, "remaining": 0, "production_backup_verified": False}


def quarantine_legacy_orphan(store: OciStore, items: list[dict]) -> dict:
    """Preserve one bounded historical synthetic canary, without deleting it.

    The remote-observed hash is NOT independent evidence of the original
    upload. This permits a separate new-object restore experiment only;
    the historical orphan remains unresolved and is never used as a source.
    """
    ensure(not LEGACY_QUARANTINE.exists() and not LEGACY_QUARANTINE.is_symlink(),
           "Historical synthetic orphan was already quarantined; manual review is required.")
    ensure(len(items) == 1 and isinstance(items[0], dict),
           "Expected exactly one separately isolated historical synthetic canary.")
    name = items[0].get("name")
    ensure(isinstance(name, str) and LEGACY_OBJECT.fullmatch(name) is not None,
           "Unexpected legacy object name; refuse any new recovery upload.")
    metadata = store.head(name)
    try:
        length = int(metadata["content-length"])
    except (TypeError, ValueError, KeyError) as exc:
        raise Refused("Historical object HEAD length is unavailable.") from exc
    ensure(40 <= length <= MAX_CANARY, "Historical object is not a bounded synthetic canary.")
    ensure("storage-tier" not in metadata or metadata["storage-tier"] == "Standard",
           "Historical object storage tier differs from free Standard.")
    if "size" in items[0]:
        ensure(type(items[0]["size"]) is int and items[0]["size"] == length,
               "Legacy list and HEAD content length disagree.")
    with tempfile.TemporaryDirectory(prefix="retally-legacy-quarantine-") as home:
        downloaded = Path(home) / "sealed-legacy.rtbk"
        raw = store.get(name, downloaded, etag=metadata["etag"], max_size=MAX_CANARY)
        ensure(len(raw) == length and raw.startswith(LEGACY_MAGIC),
               "Historical object is not the expected small synthetic canary format.")
        observed = sha(raw)
    # Recheck inventory after remote readback; never delete the historic object.
    refreshed = store.objects("synthetic-only/")
    ensure(len(refreshed) == 1 and refreshed[0].get("name") == name,
           "Legacy object inventory changed during quarantine.")
    private_receipt(LEGACY_QUARANTINE, {
        "schema": 1, "legacy_object_name": name,
        "remote_observed_sha256": observed,
        "remote_observed_length": length, "synthetic_format_candidate": True,
        "original_upload_identity_independently_verified": False,
        "legacy_object_deleted": False,
        "production_backup_verified": False,
        "status": "QUARANTINED_UNRESOLVED_DO_NOT_DELETE",
    })
    return {"legacy_orphan_quarantined": True, "legacy_orphan_deleted": False,
            "_name": name, "_etag": metadata["etag"],
            "_length": length, "_sha256": observed}


def confirm_legacy_orphan_unchanged(store: OciStore, state: dict, destination: Path) -> None:
    """Verify the quarantined old object still exists, unchanged, after the new test."""
    current = store.objects("synthetic-only/")
    ensure(len(current) == 1 and current[0].get("name") == state["_name"],
           "Quarantined legacy object no longer has its original isolated inventory.")
    h = store.head(state["_name"])
    ensure(h.get("etag") == state["_etag"],
           "Quarantined legacy object ETag changed during the synthetic exercise.")
    try:
        length = int(h["content-length"])
    except (KeyError, ValueError, TypeError) as exc:
        raise Refused("Quarantined legacy object length could not be rechecked.") from exc
    ensure(length == state["_length"],
           "Quarantined legacy object length changed during the synthetic exercise.")
    if "size" in current[0]:
        ensure(type(current[0]["size"]) is int and current[0]["size"] == length,
               "Quarantined legacy object inventory disagrees with HEAD.")
    raw = store.get(state["_name"], destination, etag=state["_etag"], max_size=MAX_CANARY)
    ensure(len(raw) == length and sha(raw) == state["_sha256"],
           "Quarantined legacy object's remote ciphertext changed during the exercise.")


def synthetic_roundtrip(store: OciStore, *, preserve_legacy_orphan: bool = False) -> dict:
    """Exercise actual RecoveryWorks source adapters, encryption and restore."""
    ensure(not ATTEMPT.exists() and not ACCEPTANCE.exists(),
           "Prior synthetic backup attempt/result exists; reconcile before repeat.")
    store.bucket_check()
    legacy = store.objects("synthetic-only/")
    current = store.objects("synthetic-recovery/")
    ensure(not current, "Existing recovery objects must be reconciled before any new test.")
    quarantined = False
    legacy_state = None
    if legacy:
        ensure(type(preserve_legacy_orphan) is bool and preserve_legacy_orphan,
               "Historical synthetic orphan unresolved: explicit quarantine needed.")
        # Quarantine the old canary into an owner-only receipt. The new test
        # exclusively uses the separate synthetic-recovery/ prefix and cannot
        # delete any object in synthetic-only/.
        legacy_state = quarantine_legacy_orphan(store, legacy)
        quarantined = True
    else:
        ensure(not preserve_legacy_orphan,
               "Explicit quarantine requested but no legacy synthetic object exists.")

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
        put_etag = store.put(key, sealed)
        h = store.head(key)
        ensure(h["etag"] == put_etag,
               "OCI HEAD ETag differs from the positively acknowledged upload; do not delete.")
        try:
            remote_length = int(h["content-length"])
        except (KeyError, TypeError, ValueError) as exc:
            raise Refused("New ciphertext object's HEAD size is invalid.") from exc
        ensure(remote_length == len(ciphertext) and remote_length <= MAX_SEALED,
               "Remote ciphertext HEAD size does not match the sealed original.")
        downloaded = base / "downloaded.rtbk"
        remote_raw = store.get(key, downloaded, etag=h["etag"], max_size=remote_length)
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

        store.delete_version(key, h["etag"])
        ensure(not store.objects("synthetic-recovery/"),
               "OCI test object deletion unverified; stop, do not re-upload.")
        if legacy_state is not None:
            confirm_legacy_orphan_unchanged(
                store, legacy_state, base / "legacy-preservation-confirm.rtbk")
        result = {"schema": 1, "simulation": True, "branches_verified": 7,
                  "remote_ciphertext_sha256": fingerprint,
                  "remote_readback_verified": True, "actual_restore_verified": True,
                  "credentials_revoked": True, "tampered_archive_rejected": True,
                  "temporary_remote_object_deleted": True, "customer_files": 0,
                  "legacy_orphan_quarantined": quarantined,
                  "legacy_orphan_deleted": False,
                  "production_backup_verified": False, "separate_key_escrow_verified": False}
        private_receipt(ACCEPTANCE, result)
        return {"synthetic_off_device_restore": True, "branches": 7,
                "remote_ciphertext_verified": True, "tamper_rejected": True,
                "temporary_object_removed": True,
                "legacy_orphan_quarantined": quarantined,
                "legacy_orphan_deleted": False,
                "production_backup_verified": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--inspect", action="store_true", help="Read-only provider bucket/objects")
    actions.add_argument("--cleanup-legacy-canary", action="store_true",
                         help="Delete only the exact small synthetic orphan with conditional ETag")
    actions.add_argument("--exercise", action="store_true",
                         help="Run seven real-engine synthetic journeys and remote archive recovery")
    parser.add_argument("--expected-legacy-object-name",
                        help="separately verified original synthetic object name")
    parser.add_argument("--expected-legacy-ciphertext-sha256",
                        help="independently recorded original synthetic ciphertext hash")
    parser.add_argument("--preserve-legacy-orphan", action="store_true",
                        help="explicitly quarantine one historic synthetic canary without deleting it; exercise only")
    args = parser.parse_args(argv)
    os.umask(0o077)
    ensure(not args.preserve_legacy_orphan or args.exercise,
           "Preserving an orphan is only supported for a new isolated exercise.")
    receipt = parse_bucket_receipt(BUCKET_RECEIPT)
    store = OciStore(receipt)
    if args.inspect:
        output = inspect(store)
    elif args.cleanup_legacy_canary:
        output = cleanup_legacy(store,
                                expected_object_name=args.expected_legacy_object_name,
                                expected_sha256=args.expected_legacy_ciphertext_sha256)
    else:
        output = synthetic_roundtrip(store,
                                     preserve_legacy_orphan=args.preserve_legacy_orphan)
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Refused as exc:
        print("STOP (synthetic acceptance not production proof):", str(exc), file=sys.stderr)
        raise SystemExit(2)
