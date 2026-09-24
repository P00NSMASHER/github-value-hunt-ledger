"""Pinned subset of aiparallel0/freight-audit used by RecoveryOS.

Only deterministic domain models, normalization, and matching rules are exposed
here. OCR, APIs, persistence, auth, billing, and outbound behavior remain outside
this adapter boundary.
"""
from .match import EngineConfig, MatchEngine
from .models import (
    CarrierInvoice,
    Finding,
    FindingType,
    LineItem,
    MatchResult,
    ProofOfDelivery,
    RateConfirmation,
    Severity,
    cents_to_str,
    to_cents,
)
from .normalize import is_same_load, normalize_category

__all__ = [
    "CarrierInvoice",
    "EngineConfig",
    "Finding",
    "FindingType",
    "LineItem",
    "MatchEngine",
    "MatchResult",
    "ProofOfDelivery",
    "RateConfirmation",
    "Severity",
    "cents_to_str",
    "is_same_load",
    "normalize_category",
    "to_cents",
]
