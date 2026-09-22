from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping, Sequence


RECEIPT_SCHEMA_VERSION = 1
PARTITION_METHOD = "hmac-sha256-v1"
PRECOMMIT_METHOD = "precommit-train-only-v1"
KEY_COMMITMENT_METHOD = "sha256-secret-commitment-v1"
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


def key_commitment_sha256(secret: str) -> str:
    if not secret:
        raise ValueError("blind partition secret is required")
    return hashlib.sha256(
        ("hunter-split-key-v1\0" + secret).encode("utf-8")
    ).hexdigest()


def _ledger_prefix_sha256(
    search_runs: Sequence[Mapping[str, Any]],
    count: int,
) -> str:
    if count < 0 or count > len(search_runs):
        raise ValueError("invalid activation run count")
    rows = [
        {
            "search_run_id": str(run.get("search_run_id") or ""),
            "execution_claim_id": str(run.get("execution_claim_id") or ""),
        }
        for run in search_runs[:count]
    ]
    payload = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_key_commitment(
    search_runs: Sequence[Mapping[str, Any]],
    existing: Mapping[str, Any] | None,
    *,
    secret: str | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if existing:
        commitment = dict(existing)
        if commitment.get("schema_version") != 1:
            errors.append("key_commitment_schema_mismatch")
        if commitment.get("commitment_method") != KEY_COMMITMENT_METHOD:
            errors.append("key_commitment_method_mismatch")
        count = commitment.get("activation_run_count")
        if not isinstance(count, int) or not 0 <= count <= len(search_runs):
            errors.append("key_commitment_invalid_run_count")
        else:
            expected_prefix = _ledger_prefix_sha256(search_runs, count)
            if commitment.get("activation_prefix_sha256") != expected_prefix:
                errors.append("key_commitment_ledger_prefix_mismatch")
        key_hash = str(commitment.get("key_commitment_sha256") or "")
        if (
            len(key_hash) != 64
            or any(ch not in "0123456789abcdef" for ch in key_hash.lower())
        ):
            errors.append("key_commitment_invalid_sha256")
        elif secret and key_hash != key_commitment_sha256(secret):
            errors.append("configured_split_key_does_not_match_commitment")
        return commitment, sorted(set(errors))

    if not secret:
        return None, []
    count = len(search_runs)
    return {
        "schema_version": 1,
        "commitment_method": KEY_COMMITMENT_METHOD,
        "key_commitment_sha256": key_commitment_sha256(secret),
        "activation_run_count": count,
        "activation_prefix_sha256": _ledger_prefix_sha256(
            search_runs,
            count,
        ),
        "rule": (
            "canonical runs before activation_run_count are permanently "
            "precommit train-only; only later appended trusted generated "
            "runs may receive HMAC train/confirm partitions"
        ),
    }, []


def _precommit_receipt(
    run: Mapping[str, Any],
    *,
    activation_prefix_sha256: str,
) -> dict[str, Any]:
    claim_id = str(run.get("execution_claim_id") or "")
    run_id = str(run.get("search_run_id") or "")
    commitment = hashlib.sha256(
        (
            "precommit-train-only-v1\0"
            + activation_prefix_sha256
            + "\0"
            + claim_id
            + "\0"
            + run_id
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "execution_claim_id": claim_id,
        "search_run_id": run_id,
        "partition": "train",
        "partition_method": PRECOMMIT_METHOD,
        "confirm_modulus": None,
        "confirm_bucket": None,
        "commitment_sha256": commitment,
    }


def build_partition_receipts(
    search_runs: Sequence[Mapping[str, Any]],
    existing_receipts: Sequence[Mapping[str, Any]],
    *,
    secret: str | None,
    key_commitment: Mapping[str, Any] | None = None,
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

    activation_count = (
        key_commitment.get("activation_run_count")
        if key_commitment
        else None
    )
    activation_prefix = (
        str(key_commitment.get("activation_prefix_sha256") or "")
        if key_commitment
        else ""
    )

    for index, run in enumerate(search_runs):
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

        if (
            isinstance(activation_count, int)
            and index < activation_count
        ):
            receipts[claim_id] = _precommit_receipt(
                run,
                activation_prefix_sha256=activation_prefix,
            )
            continue

        if key_commitment is None:
            issues.append(
                {
                    "reason": "split_key_commitment_unavailable",
                    "execution_claim_id": claim_id,
                    "search_run_id": run_id,
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
