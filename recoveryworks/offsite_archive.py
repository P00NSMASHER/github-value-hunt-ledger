"""Encrypt RecoveryWorks snapshots before approved off-device transport.

This tool does not establish drive encryption, authorization to use a workstation,
cloud retention, remote-sync success, or independent code release approval.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
from pathlib import Path
import secrets
import struct
import tempfile
import zlib

from .private_io import atomic_private_write, private_permissions_verified

MAGIC = b"RETALLY-BK1\x00"
MAX_PLAINTEXT = 64 * 1024 * 1024
MAX_HEADER = 1024
SCRYPT_N = 1 << 16
SCRYPT_R = 8
SCRYPT_P = 1


def _key(password: str, salt: bytes) -> bytes:
    # The API deliberately does not accept secrets via CLI arguments or environment.
    if not isinstance(password, str) or len(password) < 20:
        raise ValueError("a recovery passphrase of at least 20 characters is required")
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P).derive(password.encode("utf-8"))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _restore_checked(raw: bytes):
    """Use the actual source, ledger, and credential-invalidation restore verifier."""
    if len(raw) > MAX_PLAINTEXT:
        raise ValueError("snapshot exceeds pilot archive size limit")
    snapshot = json.loads(raw.decode("utf-8"))
    if not isinstance(snapshot, dict) or snapshot.get("schema") != 1:
        raise ValueError("not a supported RecoveryWorks snapshot")
    if not isinstance(snapshot.get("files"), dict) or "credentials.json" in snapshot["files"]:
        raise ValueError("snapshot includes unsupported or secret files")
    from .workbench import Workspace
    with tempfile.TemporaryDirectory(prefix="retally-sealed-restore-") as temp:
        restored = Workspace.restore_snapshot(snapshot, Path(temp) / "restored")
        if restored.meta.get("tokens"):
            raise ValueError("restored role keys were not invalidated")
    return snapshot


def seal_bytes(snapshot_bytes: bytes, passphrase: str) -> bytes:
    """Return authenticated ciphertext; never print the password or cleartext."""
    _restore_checked(snapshot_bytes)
    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    header = {
        "version": 1,
        "cipher": "AES-256-GCM",
        "kdf": "scrypt",
        "n": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
        "salt": salt.hex(),
        "nonce": nonce.hex(),
        "compression": "zlib",
        "snapshot_sha256": _digest(snapshot_bytes),
    }
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("ascii")
    if len(header_bytes) > MAX_HEADER:
        raise ValueError("archive header too large")
    aad = MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return aad + AESGCM(_key(passphrase, salt)).encrypt(nonce, zlib.compress(snapshot_bytes, 9), aad)


def unseal_bytes(archive_bytes: bytes, passphrase: str) -> bytes:
    """Reject format substitution, truncation, tampering, and decompression bombs."""
    if len(archive_bytes) > MAX_PLAINTEXT + MAX_HEADER + 1024 or not archive_bytes.startswith(MAGIC):
        raise ValueError("unsupported or oversized sealed archive")
    offset = len(MAGIC)
    if len(archive_bytes) < offset + 4:
        raise ValueError("truncated sealed archive")
    header_size = struct.unpack(">I", archive_bytes[offset:offset + 4])[0]
    end = offset + 4 + header_size
    if not 0 < header_size <= MAX_HEADER or len(archive_bytes) < end + 16:
        raise ValueError("invalid archive header length")
    try:
        header = json.loads(archive_bytes[offset + 4:end].decode("ascii"))
        required = {"version": 1, "cipher": "AES-256-GCM", "kdf": "scrypt",
                    "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P, "compression": "zlib"}
        if not isinstance(header, dict) or any(header.get(k) != v for k, v in required.items()):
            raise ValueError("unsupported archive cryptography")
        salt, nonce = bytes.fromhex(header["salt"]), bytes.fromhex(header["nonce"])
        if len(salt) != 16 or len(nonce) != 12:
            raise ValueError("invalid archive salt or nonce")
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid sealed archive header") from exc
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag
    try:
        plaintext_compressed = AESGCM(_key(passphrase, salt)).decrypt(
            nonce, archive_bytes[end:], archive_bytes[:end]
        )
    except InvalidTag as exc:
        raise ValueError("incorrect recovery passphrase or modified archive") from exc
    decompressor = zlib.decompressobj()
    try:
        plaintext = decompressor.decompress(plaintext_compressed, MAX_PLAINTEXT + 1)
    except zlib.error as exc:
        raise ValueError("corrupt compressed backup") from exc
    if (len(plaintext) > MAX_PLAINTEXT or decompressor.unconsumed_tail
            or decompressor.unused_data or not decompressor.eof):
        raise ValueError("invalid or oversized decompressed backup")
    if _digest(plaintext) != header.get("snapshot_sha256"):
        raise ValueError("snapshot integrity verification failed")
    _restore_checked(plaintext)
    return plaintext


def seal_file(snapshot_path: Path, destination: Path, passphrase: str) -> dict:
    if snapshot_path.is_symlink() or destination.is_symlink() or destination.exists():
        raise ValueError("unsafe or existing backup path")
    if not snapshot_path.is_file() or not private_permissions_verified(snapshot_path):
        raise PermissionError("snapshot source requires verified owner-only permissions")
    if snapshot_path.resolve() == destination.resolve():
        raise ValueError("source and destination cannot match")
    ciphertext = seal_bytes(snapshot_path.read_bytes(), passphrase)
    atomic_private_write(destination, ciphertext)
    if not private_permissions_verified(destination) or _digest(destination.read_bytes()) != _digest(ciphertext):
        raise PermissionError("encrypted archive writeback verification failed")
    return {"sealed_sha256": _digest(ciphertext), "sealed_size": len(ciphertext),
            "verified_locally": True, "off_device_verified": False}


def verify_file(source: Path, passphrase: str) -> dict:
    # Hash the exact ciphertext bytes that were authenticated and restored.
    # A second disk read could report a digest for different, unverified bytes.
    sealed = source.read_bytes()
    raw = unseal_bytes(sealed, passphrase)
    return {"sealed_sha256": _digest(sealed),
            "snapshot_sha256": _digest(raw), "restore_verified": True,
            "off_device_verified": False}


def restore_file(source: Path, destination: Path, passphrase: str) -> dict:
    # Workbench restores disable all role keys; issue new keys locally after review.
    raw = unseal_bytes(source.read_bytes(), passphrase)
    if destination.is_symlink() or destination.exists():
        raise ValueError("restore destination must be a new private directory")
    from .workbench import Workspace
    restored = Workspace.restore_snapshot(json.loads(raw.decode("utf-8")), destination)
    return {"restore_verified": True, "all_credentials_revoked": not bool(restored.meta["tokens"]),
            "off_device_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    seal = sub.add_parser("seal"); seal.add_argument("--snapshot", type=Path, required=True)
    seal.add_argument("--archive", type=Path, required=True)
    verify = sub.add_parser("verify"); verify.add_argument("--archive", type=Path, required=True)
    restore = sub.add_parser("restore"); restore.add_argument("--archive", type=Path, required=True)
    restore.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    passphrase = getpass.getpass("Recovery passphrase (not stored): ")
    if args.command == "seal":
        if passphrase != getpass.getpass("Confirm recovery passphrase: "):
            raise ValueError("passphrases did not match")
        result = seal_file(args.snapshot, args.archive, passphrase)
    elif args.command == "verify":
        result = verify_file(args.archive, passphrase)
    else:
        result = restore_file(args.archive, args.destination, passphrase)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())