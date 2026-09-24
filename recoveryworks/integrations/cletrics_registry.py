"""Durable receipt registry for continuous Cletrics ingestion.

This state is deliberately separate from the Recovery Ledger. It records which
exact Cletrics+authority processing jobs completed successfully, allowing exact
repeats to be skipped without rewriting recovery case history.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from recoveryworks.models import normalize_sha256
from recoveryworks.private_io import atomic_private_write, private_file_lock


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


@dataclass(frozen=True)
class CletricsProcessingReceipt:
    job_fingerprint: str
    mode: str
    bundle_sha256: str
    manifest_sha256: str
    client_id: str
    provider: str
    billing_account_id: str
    period_start: str
    period_end: str
    exported_at: str
    authority_hashes: Mapping[str, str]
    verification_flags: Mapping[str, bool]
    scan_head_hash: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "job_fingerprint",
            normalize_sha256("job_fingerprint", self.job_fingerprint),
        )
        object.__setattr__(
            self,
            "bundle_sha256",
            normalize_sha256("bundle_sha256", self.bundle_sha256),
        )
        object.__setattr__(
            self,
            "manifest_sha256",
            normalize_sha256("manifest_sha256", self.manifest_sha256),
        )
        for name in ("mode", "client_id", "provider", "billing_account_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        normalized_hashes: dict[str, str] = {}
        for key, value in self.authority_hashes.items():
            normalized_hashes[str(key)] = normalize_sha256(
                f"authority_hashes.{key}", value
            )
        object.__setattr__(self, "authority_hashes", normalized_hashes)
        normalized_flags: dict[str, bool] = {}
        for key, value in self.verification_flags.items():
            if type(value) is not bool:
                raise ValueError(f"verification_flags.{key} must be boolean")
            normalized_flags[str(key)] = value
        object.__setattr__(self, "verification_flags", normalized_flags)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CletricsReceiptRegistry:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self.lock_path = self.path.with_name(f".{self.path.name}.lock")

    def _read(self) -> tuple[str | None, dict[str, CletricsProcessingReceipt]]:
        if not self.path.exists():
            return None, {}
        raw = self.path.read_bytes()
        try:
            envelope = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Cletrics receipt registry is not valid JSON") from exc
        if envelope.get("schema") != 1:
            raise ValueError("unsupported Cletrics receipt registry schema")
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("Cletrics receipt registry payload missing")
        state_hash = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        if envelope.get("state_hash") != state_hash:
            raise ValueError("Cletrics receipt registry hash mismatch")
        rows = payload.get("receipts", [])
        if not isinstance(rows, list):
            raise ValueError("Cletrics receipt registry receipts must be a list")
        receipts: dict[str, CletricsProcessingReceipt] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("invalid Cletrics receipt row")
            receipt = CletricsProcessingReceipt(**row)
            previous = receipts.get(receipt.job_fingerprint)
            if previous is not None and previous != receipt:
                raise ValueError("conflicting Cletrics processing receipt")
            receipts[receipt.job_fingerprint] = receipt
        return state_hash, receipts

    def state_hash(self) -> str | None:
        return self._read()[0]

    def receipts(self) -> tuple[CletricsProcessingReceipt, ...]:
        values = self._read()[1]
        return tuple(values[key] for key in sorted(values))

    def contains(self, job_fingerprint: str) -> bool:
        fingerprint = normalize_sha256("job_fingerprint", job_fingerprint)
        return fingerprint in self._read()[1]

    def record(
        self,
        receipts: Iterable[CletricsProcessingReceipt],
    ) -> str:
        incoming = tuple(receipts)
        with private_file_lock(self.lock_path):
            _, current = self._read()
            for receipt in incoming:
                previous = current.get(receipt.job_fingerprint)
                if previous is not None and previous != receipt:
                    raise ValueError(
                        "job fingerprint already has a different processing receipt"
                    )
                current[receipt.job_fingerprint] = receipt
            payload = {
                "receipts": [
                    current[key].as_dict()
                    for key in sorted(current)
                ]
            }
            state_hash = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
            envelope = {
                "schema": 1,
                "state_hash": state_hash,
                "payload": payload,
            }
            atomic_private_write(
                self.path,
                _canonical_bytes(envelope) + b"\n",
            )
            return state_hash
