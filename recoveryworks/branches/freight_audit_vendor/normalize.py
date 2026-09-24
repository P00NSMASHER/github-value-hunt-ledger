"""Standard-library normalization shim for the vendored freight-audit engine.

The upstream engine uses RapidFuzz plus a data-driven vocabulary. RecoveryOS keeps
its foundation dependency-light, so this shim preserves the upstream fallback
vocabulary, canonical categories, lenient load-ID comparison, and the same 86%
/ 92% fuzzy thresholds using difflib.SequenceMatcher.
"""
from __future__ import annotations

from difflib import SequenceMatcher

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "linehaul":  ["linehaul", "line haul", "freight charge", "base rate", "transportation", "flat rate"],
    "fuel":      ["fuel", "fsc", "fuel surcharge"],
    "detention": ["detention", "det ", "det.", "driver wait", "wait time", "waiting", "demurrage"],
    "layover":   ["layover", "lay over", "overnight"],
    "lumper":    ["lumper", "unloading", "loading fee", "load/unload", "handling"],
    "liftgate":  ["liftgate", "lift gate", "lift-gate"],
    "reweigh":   ["reweigh", "re-weigh", "reweighing", "scale"],
    "tonu":      ["tonu", "truck order not used", "dry run", "dead head", "deadhead"],
    "stopoff":   ["stop off", "stop-off", "extra stop", "multi-stop", "additional stop"],
    "residential": ["residential", "resi "],
}

_FUZZ_THRESHOLD = 0.86


def normalize_category(description: str) -> str:
    text = str(description or "").strip().lower()
    if not text:
        return "other"
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category

    best_category = "other"
    best_ratio = 0.0
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            ratio = SequenceMatcher(None, text, keyword.strip()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_category = category
    return best_category if best_ratio >= _FUZZ_THRESHOLD else "other"


def is_same_load(id_a: str, id_b: str) -> bool:
    def clean(value: str) -> str:
        normalized = "".join(ch for ch in str(value).upper() if ch.isalnum()).lstrip("0")
        return normalized or "0"

    a, b = clean(id_a), clean(id_b)
    if a == b:
        return True
    if a.endswith(b) or b.endswith(a) or a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.92
