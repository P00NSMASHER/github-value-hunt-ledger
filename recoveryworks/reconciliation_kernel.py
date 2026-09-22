"""Deterministic reconciliation kernel for RecoveryWorks.

This is a Python compatibility implementation of the invariants verified in
dylanpulver/recon at commit e6b787213bb023568c99c432ea4733e1f2456a5e.

It is intentionally a matching primitive only. A match is not evidence of
contractual/statutory entitlement and cannot by itself create a validated
RecoveryFinding.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import json
import math
import re
from typing import Any, Iterable, Mapping, Sequence

SOURCE_REPOSITORY = "https://github.com/dylanpulver/recon"
SOURCE_COMMIT = "e6b787213bb023568c99c432ea4733e1f2456a5e"
SOURCE_LICENSE = "MIT"

_AMOUNT_RE = re.compile(r"^[-+]?\d+(\.\d+)?$")
_PREFIX_RE = re.compile(r"^(REF|REFERENCE|INV|INVOICE|ORDER|ORD|TXN|TRANSACTION)[\s:_-]*", re.I)
_SEPARATORS_RE = re.compile(r"[\s:_\-./]+")
_MAX_SAFE_INTEGER = 9_007_199_254_740_991


@dataclass(frozen=True)
class ReconTxn:
    id: str
    amount: int | float | str
    date: str
    currency: str
    reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedReference:
    value: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class MatchReceipt:
    rule: str
    fields: tuple[str, ...]
    date_delta_days: int
    amount_delta_minor: int
    notes: tuple[str, ...]
    normalization: Mapping[str, Any] | None = None
    tolerance: Mapping[str, int] | None = None


@dataclass(frozen=True)
class MatchGroup:
    internal_ids: tuple[str, ...]
    settlement_ids: tuple[str, ...]
    internal_total_minor: int
    settlement_total_minor: int
    currency: str
    receipt: MatchReceipt


@dataclass(frozen=True)
class ResidualCandidate:
    id: str
    amount_delta_minor: int
    shared_reference: str


@dataclass(frozen=True)
class Residual:
    side: str
    id: str
    category: str
    date: str
    amount_minor: int
    currency: str
    reference: str | None = None
    candidate: ResidualCandidate | None = None


@dataclass(frozen=True)
class ManyToOneConfig:
    enabled: bool = True
    date_window_days: int = 7
    tolerance_bps: int = 0
    max_group_size: int = 6
    max_candidates: int = 18
    max_nodes: int = 50_000


@dataclass(frozen=True)
class ReconConfig:
    decimals: int = 2
    date_window_days: int = 3
    amount_tolerance_bps: int = 50
    amount_tolerance_min_minor: int = 0
    many_to_one: ManyToOneConfig = field(default_factory=ManyToOneConfig)


@dataclass(frozen=True)
class ReconSummary:
    internal_rows: int
    settlement_rows: int
    match_groups: int
    matched_internal: int
    matched_settlement: int
    unmatched_internal: int
    unmatched_settlement: int
    by_rule: Mapping[str, int]
    matched_internal_total_minor: int
    matched_settlement_total_minor: int
    unmatched_internal_total_minor: int
    unmatched_settlement_total_minor: int
    drift_net_minor: int


@dataclass(frozen=True)
class ReconResult:
    matches: tuple[MatchGroup, ...]
    unmatched_internal: tuple[Residual, ...]
    unmatched_settlement: tuple[Residual, ...]
    summary: ReconSummary
    kernel_repository: str = SOURCE_REPOSITORY
    kernel_commit: str = SOURCE_COMMIT

    def canonical_json(self) -> str:
        """Stable serialized form for fixture comparisons and proof manifests."""
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class _Row:
    id: str
    minor: int
    day: int
    date: str
    currency: str
    raw_ref: str | None
    norm: NormalizedReference | None
    txn: ReconTxn


def _validate_config(config: ReconConfig) -> None:
    if type(config.decimals) is not int or not 0 <= config.decimals <= 9:
        raise ValueError("decimals must be an integer between 0 and 9")
    for name, value in (
        ("date_window_days", config.date_window_days),
        ("amount_tolerance_bps", config.amount_tolerance_bps),
        ("amount_tolerance_min_minor", config.amount_tolerance_min_minor),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    m = config.many_to_one
    if type(m.enabled) is not bool:
        raise ValueError("many_to_one.enabled must be boolean")
    if type(m.date_window_days) is not int or m.date_window_days < 0:
        raise ValueError("many_to_one.date_window_days must be a non-negative integer")
    if type(m.tolerance_bps) is not int or m.tolerance_bps < 0:
        raise ValueError("many_to_one.tolerance_bps must be a non-negative integer")
    if type(m.max_group_size) is not int or m.max_group_size < 2:
        raise ValueError("many_to_one.max_group_size must be at least 2")
    if type(m.max_candidates) is not int or m.max_candidates < 2:
        raise ValueError("many_to_one.max_candidates must be at least 2")
    if type(m.max_nodes) is not int or m.max_nodes < 1:
        raise ValueError("many_to_one.max_nodes must be positive")


def parse_amount_to_minor(value: int | float | str, decimals: int = 2) -> int:
    """Parse major-unit money strictly into integer minor units."""
    if isinstance(value, bool):
        raise ValueError("boolean is not a money amount")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"amount is not finite: {value}")
        text = str(value)
    elif isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ValueError(f"unsupported amount type: {type(value).__name__}")

    if not _AMOUNT_RE.fullmatch(text):
        raise ValueError(f"unparseable amount {value!r} (expected e.g. '12.34')")

    sign = -1 if text.startswith("-") else 1
    unsigned = text.lstrip("+-")
    whole, dot, fraction = unsigned.partition(".")
    if len(fraction) > decimals:
        raise ValueError(
            f"amount {value!r} has {len(fraction)} fractional digits, config allows {decimals}"
        )
    minor_text = whole + fraction.ljust(decimals, "0")
    minor = int(minor_text or "0")
    if minor > _MAX_SAFE_INTEGER:
        raise ValueError(f"amount {value!r} exceeds safe integer range in minor units")
    return sign * minor


def _parse_iso_date(value: str) -> int:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("date is required")
    raw = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ValueError(f"invalid ISO date {value!r}; expected YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"impossible calendar date {value!r}") from exc
    return parsed.toordinal()


def normalize_reference(value: str) -> NormalizedReference:
    raw = value.strip()
    current = raw
    steps: list[str] = []

    upper = current.upper()
    if upper != current:
        current = upper
        steps.append("uppercase")

    stripped = _PREFIX_RE.sub("", current)
    if stripped != current:
        prefix = current[: len(current) - len(stripped)].strip(" _:-")
        current = stripped
        steps.append(f"strip-prefix:{prefix or 'KNOWN'}")

    compact = _SEPARATORS_RE.sub("", current)
    if compact != current:
        current = compact
        steps.append("strip-separators")

    if current.isdigit():
        no_zeros = current.lstrip("0") or "0"
        if no_zeros != current:
            current = no_zeros
            steps.append("strip-leading-zeros")

    return NormalizedReference(value=current, steps=tuple(steps))


def _prepare_rows(
    txns: Iterable[ReconTxn],
    side: str,
    config: ReconConfig,
) -> list[_Row]:
    seen: set[str] = set()
    rows: list[_Row] = []
    for txn in txns:
        if not isinstance(txn.id, str) or not txn.id:
            raise ValueError(f"{side} row is missing an id")
        if txn.id in seen:
            raise ValueError(f'duplicate id "{txn.id}" on {side} side — ids must be unique per side')
        seen.add(txn.id)
        if not isinstance(txn.currency, str) or not txn.currency.strip():
            raise ValueError(f'{side} row "{txn.id}" is missing a currency')
        day = _parse_iso_date(txn.date)
        raw_ref = txn.reference if isinstance(txn.reference, str) and txn.reference.strip() else None
        rows.append(
            _Row(
                id=txn.id,
                minor=parse_amount_to_minor(txn.amount, config.decimals),
                day=day,
                date=txn.date.strip(),
                currency=txn.currency.strip().upper(),
                raw_ref=raw_ref,
                norm=normalize_reference(raw_ref) if raw_ref else None,
                txn=txn,
            )
        )
    rows.sort(key=lambda r: (r.day, r.minor, r.id))
    return rows


def _allowed_tolerance_minor(minor: int, config: ReconConfig) -> int:
    bps_part = (abs(minor) * config.amount_tolerance_bps) // 10_000
    return max(bps_part, config.amount_tolerance_min_minor)


def _consumed_bps(delta_minor: int, settlement_minor: int) -> int:
    if settlement_minor == 0:
        return 0
    return round((abs(delta_minor) / abs(settlement_minor)) * 10_000)


def _bounded_subset_sum(
    values: Sequence[int],
    target: int,
    *,
    max_size: int,
    tolerance: int,
    max_nodes: int,
) -> tuple[tuple[int, ...] | None, bool]:
    if target <= 0:
        return None, False
    if any(v <= 0 for v in values):
        raise ValueError("bounded subset sum requires strictly positive values")

    order = sorted(enumerate(values), key=lambda pair: (-pair[1], pair[0]))
    suffix_sum = [0] * (len(order) + 1)
    for i in range(len(order) - 1, -1, -1):
        suffix_sum[i] = suffix_sum[i + 1] + order[i][1]

    nodes = 0
    exhausted = False
    chosen: list[int] = []

    def dfs(pos: int, count: int, running: int) -> tuple[int, ...] | None:
        nonlocal nodes, exhausted
        if nodes >= max_nodes:
            exhausted = True
            return None
        nodes += 1
        if count >= 2 and abs(running - target) <= tolerance:
            return tuple(sorted(chosen))
        if pos >= len(order) or count >= max_size:
            return None
        if running > target + tolerance:
            return None
        if running + suffix_sum[pos] < target - tolerance:
            return None

        source_index, value = order[pos]
        chosen.append(source_index)
        with_value = dfs(pos + 1, count + 1, running + value)
        if with_value is not None:
            return with_value
        chosen.pop()
        return dfs(pos + 1, count, running)

    found = dfs(0, 0, 0)
    return found, exhausted if found is None else False


def reconcile(
    internal: Iterable[ReconTxn],
    settlement: Iterable[ReconTxn],
    config: ReconConfig | None = None,
) -> ReconResult:
    config = config or ReconConfig()
    _validate_config(config)
    a_rows = _prepare_rows(internal, "internal", config)
    b_rows = _prepare_rows(settlement, "settlement", config)

    matches: list[MatchGroup] = []
    a_matched: set[str] = set()
    b_matched: set[str] = set()

    def pair(a: _Row, b: _Row, receipt: MatchReceipt) -> None:
        a_matched.add(a.id)
        b_matched.add(b.id)
        matches.append(
            MatchGroup(
                internal_ids=(a.id,),
                settlement_ids=(b.id,),
                internal_total_minor=a.minor,
                settlement_total_minor=b.minor,
                currency=a.currency,
                receipt=receipt,
            )
        )

    # Tier 1 — exact.
    exact_pool: dict[tuple[str, int, int, str], list[_Row]] = {}
    for b in b_rows:
        if b.raw_ref is None:
            continue
        exact_pool.setdefault((b.currency, b.minor, b.day, b.raw_ref.strip()), []).append(b)
    for a in a_rows:
        if a.raw_ref is None:
            continue
        pool = exact_pool.get((a.currency, a.minor, a.day, a.raw_ref.strip()))
        while pool and pool[0].id in b_matched:
            pool.pop(0)
        if not pool:
            continue
        b = pool.pop(0)
        pair(
            a,
            b,
            MatchReceipt(
                rule="exact",
                fields=("currency", "amount", "date", "reference"),
                date_delta_days=0,
                amount_delta_minor=0,
                notes=(f'reference "{a.raw_ref.strip()}" identical on both sides',),
            ),
        )

    # Tier 2 — normalized reference.
    fuzzy_pool: dict[tuple[str, int, str], list[_Row]] = {}
    for b in b_rows:
        if b.id in b_matched or b.norm is None or not b.norm.value:
            continue
        fuzzy_pool.setdefault((b.currency, b.minor, b.norm.value), []).append(b)
    for a in a_rows:
        if a.id in a_matched or a.norm is None or not a.norm.value:
            continue
        candidates = [
            b for b in fuzzy_pool.get((a.currency, a.minor, a.norm.value), [])
            if b.id not in b_matched and abs(a.day - b.day) <= config.date_window_days
        ]
        if not candidates:
            continue
        b = min(candidates, key=lambda r: (abs(a.day - r.day), r.id))
        steps = tuple(dict.fromkeys((*a.norm.steps, *b.norm.steps)))
        pair(
            a,
            b,
            MatchReceipt(
                rule="reference-fuzzy",
                fields=("currency", "amount", "reference(normalized)", f"date(±{config.date_window_days}d)"),
                date_delta_days=a.day - b.day,
                amount_delta_minor=0,
                normalization={
                    "internal_raw": a.raw_ref,
                    "settlement_raw": b.raw_ref,
                    "normalized": a.norm.value,
                    "steps": steps,
                },
                notes=(f'references normalize to "{a.norm.value}"',),
            ),
        )

    # Tier 3 — exact amount + date window.
    amount_pool: dict[tuple[str, int], list[_Row]] = {}
    for b in b_rows:
        if b.id not in b_matched:
            amount_pool.setdefault((b.currency, b.minor), []).append(b)
    for a in a_rows:
        if a.id in a_matched:
            continue
        candidates = [
            b for b in amount_pool.get((a.currency, a.minor), [])
            if b.id not in b_matched and abs(a.day - b.day) <= config.date_window_days
        ]
        if not candidates:
            continue
        b = min(candidates, key=lambda r: (abs(a.day - r.day), r.id))
        pair(
            a,
            b,
            MatchReceipt(
                rule="amount-date-window",
                fields=("currency", "amount", f"date(±{config.date_window_days}d)"),
                date_delta_days=a.day - b.day,
                amount_delta_minor=0,
                notes=(f"amounts identical; dates {abs(a.day-b.day)} day(s) apart",),
            ),
        )

    # Tier 4 — amount tolerance.
    for a in a_rows:
        if a.id in a_matched:
            continue
        allowed = _allowed_tolerance_minor(a.minor, config)
        if allowed <= 0:
            continue
        candidates: list[tuple[int, int, str, _Row]] = []
        for b in b_rows:
            if b.id in b_matched or b.currency != a.currency:
                continue
            if abs(a.day - b.day) > config.date_window_days:
                continue
            delta = a.minor - b.minor
            if abs(delta) <= allowed:
                candidates.append((abs(delta), abs(a.day - b.day), b.id, b))
        if not candidates:
            continue
        _, _, _, b = min(candidates, key=lambda item: item[:3])
        delta = a.minor - b.minor
        pair(
            a,
            b,
            MatchReceipt(
                rule="amount-tolerance",
                fields=(
                    "currency",
                    f"amount(±{config.amount_tolerance_bps}bps)",
                    f"date(±{config.date_window_days}d)",
                ),
                date_delta_days=a.day - b.day,
                amount_delta_minor=delta,
                tolerance={
                    "amount_delta_minor": delta,
                    "allowed_delta_minor": allowed,
                    "consumed_bps": _consumed_bps(delta, b.minor),
                },
                notes=(f"amount delta {delta} minor units within allowance {allowed}",),
            ),
        )

    # Tier 5 — bounded many-to-one.
    m = config.many_to_one
    if m.enabled:
        for b in b_rows:
            if b.id in b_matched or b.minor <= 0:
                continue
            candidates = [
                a for a in a_rows
                if a.id not in a_matched
                and a.currency == b.currency
                and a.minor > 0
                and abs(a.day - b.day) <= m.date_window_days
            ][: m.max_candidates]
            if len(candidates) < 2:
                continue
            tolerance = (abs(b.minor) * m.tolerance_bps) // 10_000
            indices, exhausted = _bounded_subset_sum(
                [a.minor for a in candidates],
                b.minor,
                max_size=m.max_group_size,
                tolerance=tolerance,
                max_nodes=m.max_nodes,
            )
            if exhausted or indices is None:
                continue
            group = sorted((candidates[i] for i in indices), key=lambda r: r.id)
            total = sum(a.minor for a in group)
            delta = total - b.minor
            for a in group:
                a_matched.add(a.id)
            b_matched.add(b.id)
            receipt_tolerance = None
            if m.tolerance_bps > 0:
                receipt_tolerance = {
                    "amount_delta_minor": delta,
                    "allowed_delta_minor": tolerance,
                    "consumed_bps": _consumed_bps(delta, b.minor),
                }
            matches.append(
                MatchGroup(
                    internal_ids=tuple(a.id for a in group),
                    settlement_ids=(b.id,),
                    internal_total_minor=total,
                    settlement_total_minor=b.minor,
                    currency=b.currency,
                    receipt=MatchReceipt(
                        rule="many-to-one",
                        fields=("currency", "sum(amount)", f"date(±{m.date_window_days}d)"),
                        date_delta_days=max((a.day - b.day for a in group), key=abs),
                        amount_delta_minor=delta,
                        tolerance=receipt_tolerance,
                        notes=(f"{len(group)} internal rows sum to settlement row {b.id}",),
                    ),
                )
            )

    open_a = [a for a in a_rows if a.id not in a_matched]
    open_b = [b for b in b_rows if b.id not in b_matched]

    def residual_for(row: _Row, side: str, others: Sequence[_Row]) -> Residual:
        category = "missing-in-settlement" if side == "internal" else "missing-in-internal"
        candidate: ResidualCandidate | None = None
        if row.norm is not None and row.norm.value:
            possible = [
                other for other in others
                if other.currency == row.currency
                and other.norm is not None
                and other.norm.value == row.norm.value
                and other.minor != row.minor
            ]
            if possible:
                best = min(possible, key=lambda other: (abs(row.minor-other.minor), other.id))
                category = "amount-mismatch"
                candidate = ResidualCandidate(
                    id=best.id,
                    amount_delta_minor=row.minor - best.minor,
                    shared_reference=row.norm.value,
                )
        return Residual(
            side=side,
            id=row.id,
            category=category,
            date=row.date,
            amount_minor=row.minor,
            currency=row.currency,
            reference=row.raw_ref,
            candidate=candidate,
        )

    unmatched_internal = tuple(residual_for(row, "internal", open_b) for row in open_a)
    unmatched_settlement = tuple(residual_for(row, "settlement", open_a) for row in open_b)

    by_rule = {name: 0 for name in (
        "exact", "reference-fuzzy", "amount-date-window", "amount-tolerance", "many-to-one"
    )}
    for group in matches:
        by_rule[group.receipt.rule] += 1

    matched_internal_ids = {i for group in matches for i in group.internal_ids}
    matched_settlement_ids = {i for group in matches for i in group.settlement_ids}
    matched_internal_total = sum(r.minor for r in a_rows if r.id in matched_internal_ids)
    matched_settlement_total = sum(r.minor for r in b_rows if r.id in matched_settlement_ids)

    summary = ReconSummary(
        internal_rows=len(a_rows),
        settlement_rows=len(b_rows),
        match_groups=len(matches),
        matched_internal=len(matched_internal_ids),
        matched_settlement=len(matched_settlement_ids),
        unmatched_internal=len(unmatched_internal),
        unmatched_settlement=len(unmatched_settlement),
        by_rule=by_rule,
        matched_internal_total_minor=matched_internal_total,
        matched_settlement_total_minor=matched_settlement_total,
        unmatched_internal_total_minor=sum(r.amount_minor for r in unmatched_internal),
        unmatched_settlement_total_minor=sum(r.amount_minor for r in unmatched_settlement),
        drift_net_minor=matched_internal_total - matched_settlement_total,
    )

    matches.sort(key=lambda g: (g.receipt.rule, g.internal_ids, g.settlement_ids))
    return ReconResult(
        matches=tuple(matches),
        unmatched_internal=unmatched_internal,
        unmatched_settlement=unmatched_settlement,
        summary=summary,
    )
