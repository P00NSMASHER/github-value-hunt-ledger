"""Durable receipt registry for continuous Cletrics ingestion.

This state is deliberately separate from the Recovery Ledger. It records which
exact Cletrics+authority processing jobs completed successfully, allowing exact
repeats to be skipped without rewriting recovery case history.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from recoveryworks.models import freeze_json, normalize_sha256, normalize_utc_timestamp
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

        mode = str(self.mode).strip()
        if mode not in {"cloud", "cloud_discount", "cloud_commitment"}:
            raise ValueError("unsupported Cletrics processing mode")
        object.__setattr__(self, "mode", mode)

        for name in ("client_id", "provider", "billing_account_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            normalized = value.strip()
            if any(ord(character) < 32 for character in normalized):
                raise ValueError(f"{name} cannot contain control characters")
            object.__setattr__(self, name, normalized)

        try:
            start = date.fromisoformat(str(self.period_start).strip()).isoformat()
            end = date.fromisoformat(str(self.period_end).strip()).isoformat()
        except ValueError as exc:
            raise ValueError("receipt periods must be YYYY-MM-DD") from exc
        if end < start:
            raise ValueError("period_end cannot predate period_start")
        object.__setattr__(self, "period_start", start)
        object.__setattr__(self, "period_end", end)
        object.__setattr__(
            self,
            "exported_at",
            normalize_utc_timestamp("exported_at", self.exported_at),
        )
        if self.scan_head_hash is not None:
            object.__setattr__(
                self,
                "scan_head_hash",
                normalize_sha256("scan_head_hash", self.scan_head_hash),
            )

        if not isinstance(self.authority_hashes, Mapping):
            raise ValueError("authority_hashes must be an object")
        normalized_hashes: dict[str, str] = {}
        for key, value in self.authority_hashes.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                raise ValueError("authority_hashes keys must be non-empty")
            normalized_hashes[normalized_key] = normalize_sha256(
                f"authority_hashes.{normalized_key}", value
            )
        object.__setattr__(
            self,
            "authority_hashes",
            freeze_json(normalized_hashes, name="authority_hashes"),
        )

        if not isinstance(self.verification_flags, Mapping):
            raise ValueError("verification_flags must be an object")
        normalized_flags: dict[str, bool] = {}
        for key, value in self.verification_flags.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                raise ValueError("verification_flags keys must be non-empty")
            if type(value) is not bool:
                raise ValueError(
                    f"verification_flags.{normalized_key} must be boolean"
                )
            normalized_flags[normalized_key] = value
        object.__setattr__(
            self,
            "verification_flags",
            freeze_json(normalized_flags, name="verification_flags"),
        )

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

    def replace(
        self,
        *,
        prior_job_fingerprint: str,
        replacement: CletricsProcessingReceipt,
    ) -> str:
        prior = normalize_sha256("prior_job_fingerprint", prior_job_fingerprint)
        with private_file_lock(self.lock_path):
            _, current = self._read()
            if prior not in current:
                raise ValueError("prior Cletrics processing receipt is missing")
            if replacement.job_fingerprint in current and replacement.job_fingerprint != prior:
                raise ValueError("replacement processing receipt already exists")
            del current[prior]
            current[replacement.job_fingerprint] = replacement
            payload = {
                "receipts": [current[key].as_dict() for key in sorted(current)]
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
