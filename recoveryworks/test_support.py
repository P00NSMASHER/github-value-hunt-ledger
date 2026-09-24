"""Small deterministic helpers shared by RecoveryWorks test fixtures."""
from __future__ import annotations

import hashlib


def source_hash(label: object) -> str:
    """Create a real SHA-256 digest for a human-readable fixture label."""
    return hashlib.sha256(str(label).encode("utf-8")).hexdigest()
