from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


_PREFIX = re.compile(r"^[a-z0-9-]+$")


def semantic_revision_sha256(
    source_id: str,
    payload: Mapping[str, Any],
) -> str:
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("source_id is required")
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be a mapping")
    raw = json.dumps(
        {
            "source_id": source_id,
            "payload": dict(payload),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def versioned_work_item_id(
    prefix: str,
    source_id: str,
    payload: Mapping[str, Any],
) -> tuple[str, str]:
    if not isinstance(prefix, str) or not _PREFIX.fullmatch(prefix):
        raise ValueError("prefix must match [a-z0-9-]+")
    revision = semantic_revision_sha256(source_id, payload)
    token = hashlib.sha256(
        f"{source_id}\0{revision}".encode("utf-8")
    ).hexdigest()[:12]
    return f"WORK:{prefix}:{token}", revision
