from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping, Sequence


RECEIPT_SCHEMA_VERSION = 1
PARTITION_METHOD = "hmac-sha256-v1"
DEFAULT_CONFIRM_MODULUS = 5
DEFAULT_CONFIRM_BUCKET = 0


def trusted_claim_id(run: Mapping[str, Any]) -> str | None:
    """Return the pre-hunt generated claim identity eligible for blind split."""
    version = int(run.get("schema_version") or 0)
    claim_id = run.get("execution_claim_id")
    if (
        version >= 14
        and run.get("allocation_mode") == "generated"
        and run.get("routing_mode") == "generated"
        and isinstance(claim_id, str)
        and claim_id.startswith("CLAIM:")
    ):
        return claim_id
    return None


def _digest(claim_id: str, secret: str) -> bytes:
    if not claim_id:
        raise ValueError("claim_id is required")
    if not secret:
        raise ValueError("blind partition secret is required")
    return hmac.new(
        secret.encode("utf-8"),
        ("hunter-confirm-v1\0" + claim_id).encode("utf-8"),
        hashlib.sha256,
    ).digest()


def assign_partition(
    claim_id: str,
    secret: str,
    *,
    confirm_modulus: int = DEFAULT_CONFIRM_MODULUS,
    confirm_bucket: int = DEFAULT_CONFIRM_BUCKET,
) -> tuple[str, str]:
    if confirm_modulus < 2:
        raise ValueError("confirm_modulus must be >= 2")
    if not 0 <= confirm_bucket < confirm_modulus:
        raise ValueError("confirm_bucket must be within modulus")
    digest = _digest(claim_id, secret)
    bucket = int.from_bytes(digest[:8], "big") % confirm_modulus
    partition = "confirm" if bucket == confirm_bucket else "train"
    return partition, digest.hex()


def build_partition_receipts(
    search_runs: Sequence[Mapping[str, Any]],
    existing_receipts: Sequence[Mapping[str, Any]],
    *,
    secret: str | None,
    confirm_modulus: int = DEFAULT_CONFIRM_MODULUS,
    confirm_bucket: int = DEFAULT_CONFIRM_BUCKET,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    receipts: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    for row in existing_receipts:
        claim_id = str(row.get("execution_claim_id") or "")
        if not claim_id:
            issues.append({"reason": "receipt_missing_claim_id"})
            continue
        if claim_id in receipts:
            issues.append(
                {
                    "reason": "duplicate_partition_receipt",
                    "execution_claim_id": claim_id,
                }
            )
            continue
        receipts[claim_id] = dict(row)

    for run in search_runs:
        claim_id = trusted_claim_id(run)
        if not claim_id or claim_id in receipts:
            continue
        run_id = str(run.get("search_run_id") or "")
        if not run_id:
            issues.append(
                {
                    "reason": "trusted_run_missing_run_id",
                    "execution_claim_id": claim_id,
                }
            )
            continue
        if not secret:
            issues.append(
                {
                    "reason": "blind_partition_secret_unavailable",
                    "execution_claim_id": claim_id,
                    "search_run_id": run_id,
                }
            )
            continue
        partition, commitment = assign_partition(
            claim_id,
            secret,
            confirm_modulus=confirm_modulus,
            confirm_bucket=confirm_bucket,
        )
        receipts[claim_id] = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "execution_claim_id": claim_id,
            "search_run_id": run_id,
            "partition": partition,
            "partition_method": PARTITION_METHOD,
            "confirm_modulus": confirm_modulus,
            "confirm_bucket": confirm_bucket,
            "commitment_sha256": commitment,
        }

    return (
        sorted(
            receipts.values(),
            key=lambda row: (
                str(row.get("execution_claim_id") or ""),
                str(row.get("search_run_id") or ""),
            ),
        ),
        sorted(
            issues,
            key=lambda row: (
                str(row.get("execution_claim_id") or ""),
                str(row.get("reason") or ""),
            ),
        ),
    )


def validate_partition_receipts(
    receipts: Sequence[Mapping[str, Any]],
    search_runs: Sequence[Mapping[str, Any]],
    *,
    secret: str | None = None,
) -> list[str]:
    errors: list[str] = []
    runs_by_claim: dict[str, Mapping[str, Any]] = {}
    for run in search_runs:
        claim_id = trusted_claim_id(run)
        if claim_id:
            if claim_id in runs_by_claim:
                errors.append(f"duplicate_trusted_claim_run:{claim_id}")
            else:
                runs_by_claim[claim_id] = run

    seen: set[str] = set()
    for row in receipts:
        claim_id = str(row.get("execution_claim_id") or "")
        run_id = str(row.get("search_run_id") or "")
        if not claim_id:
            errors.append("receipt_missing_claim_id")
            continue
        if claim_id in seen:
            errors.append(f"duplicate_partition_receipt:{claim_id}")
            continue
        seen.add(claim_id)

        run = runs_by_claim.get(claim_id)
        if run is None:
            errors.append(f"receipt_unknown_trusted_claim:{claim_id}")
            continue
        if run_id != str(run.get("search_run_id") or ""):
            errors.append(f"receipt_run_id_mismatch:{claim_id}")

        if row.get("schema_version") != RECEIPT_SCHEMA_VERSION:
            errors.append(f"receipt_schema_mismatch:{claim_id}")
        if row.get("partition_method") != PARTITION_METHOD:
            errors.append(f"receipt_method_mismatch:{claim_id}")
        partition = row.get("partition")
        if partition not in {"train", "confirm"}:
            errors.append(f"receipt_invalid_partition:{claim_id}")
        modulus = row.get("confirm_modulus")
        bucket = row.get("confirm_bucket")
        if not isinstance(modulus, int) or modulus < 2:
            errors.append(f"receipt_invalid_modulus:{claim_id}")
        if (
            not isinstance(bucket, int)
            or not isinstance(modulus, int)
            or not 0 <= bucket < modulus
        ):
            errors.append(f"receipt_invalid_bucket:{claim_id}")
        commitment = str(row.get("commitment_sha256") or "").lower()
        if (
            len(commitment) != 64
            or any(ch not in "0123456789abcdef" for ch in commitment)
        ):
            errors.append(f"receipt_invalid_commitment:{claim_id}")
            continue

        if secret and isinstance(modulus, int) and isinstance(bucket, int):
            expected_partition, expected_commitment = assign_partition(
                claim_id,
                secret,
                confirm_modulus=modulus,
                confirm_bucket=bucket,
            )
            if partition != expected_partition:
                errors.append(f"receipt_partition_mismatch:{claim_id}")
            if commitment != expected_commitment:
                errors.append(f"receipt_commitment_mismatch:{claim_id}")

    return sorted(set(errors))


def receipt_partition_map(
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in receipts:
        claim_id = row.get("execution_claim_id")
        partition = row.get("partition")
        if (
            isinstance(claim_id, str)
            and claim_id
            and partition in {"train", "confirm"}
        ):
            out[claim_id] = str(partition)
    return out
