"""Atomic private-state bundle storage for RecoveryWorks.

This store is intentionally local-filesystem only and contains no GitHub write
path. Deployments can mount a private encrypted volume or replace this adapter
with a database/object-store implementation while preserving the same bundle
contract.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .durable_ledger import DurableRecoveryLedger


class StoreConflictError(RuntimeError):
    """Raised when optimistic concurrency detects a stale writer."""


class BundleIntegrityError(ValueError):
    """Raised when persisted bytes do not match their integrity hash."""


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


class LocalBundleStore:
    """Persist one RecoveryWorks ledger bundle atomically.

    The file is written with mode 0600, fsynced, and atomically replaced.
    expected_head_hash provides compare-and-swap semantics so two workers cannot
    silently overwrite each other's accepted lifecycle events.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    def _read_envelope(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        raw = self.path.read_bytes()
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleIntegrityError("stored bundle is not valid JSON") from exc
        if envelope.get("schema") != 1:
            raise BundleIntegrityError("unsupported store envelope schema")
        bundle = envelope.get("bundle")
        if not isinstance(bundle, dict):
            raise BundleIntegrityError("store envelope missing bundle")
        digest = hashlib.sha256(_canonical_bytes(bundle)).hexdigest()
        if envelope.get("bundle_hash") != digest:
            raise BundleIntegrityError("stored bundle hash mismatch")
        return envelope

    def load(self) -> DurableRecoveryLedger | None:
        envelope = self._read_envelope()
        if envelope is None:
            return None
        return DurableRecoveryLedger.from_bundle(envelope["bundle"])

    def current_head_hash(self) -> str | None:
        envelope = self._read_envelope()
        if envelope is None:
            return None
        return envelope["bundle"]["journal"].get("head_hash")

    def save(
        self,
        ledger: DurableRecoveryLedger,
        *,
        expected_head_hash: str | None = None,
    ) -> str | None:
        existing_head = self.current_head_hash()
        if expected_head_hash is not None and existing_head != expected_head_hash:
            raise StoreConflictError(
                f"stale ledger writer: expected {expected_head_hash!r}, "
                f"found {existing_head!r}"
            )

        bundle = ledger.export_bundle()
        envelope = {
            "schema": 1,
            "bundle_hash": hashlib.sha256(_canonical_bytes(bundle)).hexdigest(),
            "bundle": bundle,
        }
        raw = _canonical_bytes(envelope) + b"\n"

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return bundle["journal"].get("head_hash")
