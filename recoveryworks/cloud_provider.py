"""Canonical cloud-provider identity for FOCUS and pilot boundaries."""
from __future__ import annotations

from typing import Any


_PROVIDER_ALIASES = {
    "aws": "aws",
    "amazon web services": "aws",
    "amazon web services, inc.": "aws",
    "azure": "azure",
    "microsoft": "azure",
    "microsoft azure": "azure",
    "microsoft corporation": "azure",
    "gcp": "gcp",
    "google": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "google llc": "gcp",
}


def canonical_cloud_provider(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("cloud provider is required")
    normalized = " ".join(value.strip().lower().split())
    provider = _PROVIDER_ALIASES.get(normalized)
    if provider is None:
        raise ValueError(f"unsupported cloud provider identity: {value!r}")
    return provider
