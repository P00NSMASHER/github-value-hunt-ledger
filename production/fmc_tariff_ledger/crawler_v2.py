#!/usr/bin/env python3
"""Execution wrapper adding publisher-aware crawling to crawler.py.

This keeps the core storage/parser contract stable while adding shared-publisher
resolution and generic rule-section capture.
"""

from __future__ import annotations

import re
import threading
import urllib.parse
from dataclasses import dataclass

import crawler as base
import publisher_adapters as publishers


# Preserve core functions before monkeypatching.
_CORE_EXTRACT_TERMS = base.extract_terms
_CORE_LIKELY_TARIFF_LINK = base.likely_tariff_link
_CORE_FETCH_BYTES = base.fetch_bytes

RULE_SECTION_RE = re.compile(
    r"(?im)^\s*(?:RULE|ITEM)\s+"
    r"(?P<number>[A-Z0-9]+(?:\.[A-Z0-9]+)*)"
    r"\s*[.\-:]?\s*(?P<title>[^\n]{0,180})$"
)
BOGUS_RULE_TOKENS = {"NO", "NUMBER", "NOS", "PAGE", "PAGES"}


@dataclass
class CachedResponse:
    url: str
    status_code: int
    headers: dict[str, str]


_CACHE: dict[str, tuple[bytes, CachedResponse]] = {}
_CACHE_LOCK = threading.Lock()
_URL_LOCKS: dict[str, threading.Lock] = {}


def _url_lock(url: str) -> threading.Lock:
    with _CACHE_LOCK:
        return _URL_LOCKS.setdefault(url, threading.Lock())


def fetch_bytes_cached(url: str, timeout: int, max_bytes: int):
    canonical = base.canonicalize_url(url) or url
    with _CACHE_LOCK:
        cached = _CACHE.get(canonical)
    if cached is not None:
        return cached

    lock = _url_lock(canonical)
    with lock:
        with _CACHE_LOCK:
            cached = _CACHE.get(canonical)
        if cached is not None:
            return cached

        raw, resp = _CORE_FETCH_BYTES(canonical, timeout, max_bytes)
        lightweight = CachedResponse(
            url=resp.url,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )
        result = (raw, lightweight)

        # Shared landing pages are highly duplicated across FMC entities. Cache
        # moderate responses in memory; large carrier PDFs are usually unique.
        if len(raw) <= 8_000_000:
            with _CACHE_LOCK:
                _CACHE[canonical] = result
        return result


def likely_tariff_link_v2(url: str, anchor_text: str = "", depth: int = 0) -> bool:
    if _CORE_LIKELY_TARIFF_LINK(url, anchor_text, depth):
        return True
    return bool(re.search(
        r"history|historical|amendment|filing|revision|rev\b|archive|previous",
        f"{url} {anchor_text}",
        re.I,
    ))


def _generic_rule_terms(text: str, url: str) -> list[base.ExtractedTerm]:
    """Preserve every RULE/ITEM section, not only preselected commercial keywords."""
    matches = [
        match
        for match in RULE_SECTION_RE.finditer(text)
        if match.group("number").upper() not in BOGUS_RULE_TOKENS
    ]
    if not matches:
        return []

    doc_start, doc_end = base.detect_effective_dates(text)
    version = base.detect_source_version(text, url)
    out: list[base.ExtractedTerm] = []

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        block = re.sub(r"\s+", " ", text[start:end]).strip()[:12000]
        if not block:
            continue
        number = match.group("number")
        title = match.group("title").strip(" .:-")
        local_start, local_end = base.detect_effective_dates(block)
        effective_from = local_start or doc_start
        effective_to = local_end or doc_end
        rule_type = f"rule:{number}"
        locator = f"rule:{number}"

        out.append(base.ExtractedTerm(
            rule_type=rule_type,
            term_kind="rule_text",
            amount_value=None,
            currency=None,
            unit=None,
            quantity_value=None,
            effective_from=effective_from,
            effective_to=effective_to,
            source_version=version,
            evidence_locator=locator,
            evidence_excerpt=(f"{title} — {block}" if title else block)[:4000],
            confidence=0.95,
        ))

        for money in base.MONEY_RE.finditer(block):
            out.append(base.ExtractedTerm(
                rule_type=rule_type,
                term_kind="money",
                amount_value=money.group("amount").replace(",", ""),
                currency="USD",
                unit=(money.group("unit") or "").strip() or None,
                quantity_value=None,
                effective_from=effective_from,
                effective_to=effective_to,
                source_version=version,
                evidence_locator=locator,
                evidence_excerpt=block[:4000],
                confidence=0.94,
            ))

        for pct in base.PERCENT_RE.finditer(block):
            out.append(base.ExtractedTerm(
                rule_type=rule_type,
                term_kind="percent",
                amount_value=pct.group("amount"),
                currency=None,
                unit=(pct.group("unit") or "%").strip(),
                quantity_value=None,
                effective_from=effective_from,
                effective_to=effective_to,
                source_version=version,
                evidence_locator=locator,
                evidence_excerpt=block[:4000],
                confidence=0.92,
            ))

        free = base.FREE_DAYS_RE.search(block)
        if free:
            out.append(base.ExtractedTerm(
                rule_type=rule_type,
                term_kind="quantity",
                amount_value=None,
                currency=None,
                unit="days",
                quantity_value=free.group("qty"),
                effective_from=effective_from,
                effective_to=effective_to,
                source_version=version,
                evidence_locator=locator,
                evidence_excerpt=block[:4000],
                confidence=0.96,
            ))

    return out


def extract_terms_v2(text: str, url: str) -> list[base.ExtractedTerm]:
    core = _CORE_EXTRACT_TERMS(text, url)
    generic = _generic_rule_terms(text, url)
    seen: set[tuple] = set()
    out: list[base.ExtractedTerm] = []
    for term in [*core, *generic]:
        key = (
            term.rule_type,
            term.term_kind,
            term.amount_value,
            term.currency,
            term.unit,
            term.quantity_value,
            term.effective_from,
            term.effective_to,
            term.source_version,
            term.evidence_locator,
            term.evidence_excerpt,
        )
        if key not in seen:
            seen.add(key)
            out.append(term)
    return out


def _entity_specific_same_site_link(src, anchor: str, href: str) -> bool:
    if src.organization_no and src.organization_no in f"{anchor} {href}":
        return True
    return publishers.entity_match_score(
        anchor,
        src.legal_name,
        src.trade_name,
    ) >= 0.50


def crawl_one_location_v2(
    src,
    out_dir,
    max_depth: int,
    timeout: int,
    max_bytes: int,
    max_pages: int,
):
    family = publishers.family_for(src.tariff_url)
    seeds = publishers.seed_urls(
        src.tariff_url,
        src.organization_no,
        src.legal_name,
        src.trade_name,
    )
    queue: list[tuple[str, int, bool, str]] = [
        (seed.url, 0, seed.parse_entity_terms, seed.role) for seed in seeds
    ]
    seen: set[str] = set()
    snapshots: list[dict] = []
    errors: list[dict] = []
    terms_payload: list[tuple[int, base.ExtractedTerm]] = []
    entity_scoped_snapshots = 0

    while queue and len(snapshots) < max_pages:
        requested_url, depth, parse_flag, role = queue.pop(0)
        requested_url = base.canonicalize_url(requested_url) or requested_url
        seen_key = f"{requested_url}|{int(parse_flag)}"
        if seen_key in seen:
            continue
        seen.add(seen_key)

        try:
            raw, resp = fetch_bytes_cached(requested_url, timeout, max_bytes)
            final_url = base.canonicalize_url(resp.url) or resp.url
            digest = base.sha256_bytes(raw)
            ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            text = ""
            links: list[tuple[str, str]] = []
            parse_kind = "binary"
            title = None
            parser_status = "snapshotted"

            try:
                text, links, parse_kind, title = base.extract_text_and_links(
                    raw, ctype, final_url
                )
                parser_status = f"parsed:{parse_kind}"
            except Exception as exc:
                parser_status = f"snapshot_only:{type(exc).__name__}"
                errors.append({
                    "url": final_url,
                    "stage": "parse",
                    "error_type": type(exc).__name__,
                    "detail": str(exc)[:2000],
                })

            auth_page = bool(text) and publishers.auth_or_login_page(text, final_url)
            if auth_page:
                parser_status += ":auth_required"
                errors.append({
                    "url": final_url,
                    "stage": "publisher_access",
                    "error_type": "AuthenticationRequired",
                    "detail": (
                        f"{family} returned a login/access page. Snapshot retained; "
                        "no attempt was made to bypass authentication."
                    ),
                })

            should_parse = bool(text) and publishers.should_parse_entity_terms(
                family=family,
                explicit_parse_flag=parse_flag,
                text=text,
                url=final_url,
                organization_no=src.organization_no,
                legal_name=src.legal_name,
                trade_name=src.trade_name,
            )
            if should_parse:
                entity_scoped_snapshots += 1
                parser_status += ":entity_scoped"
            elif family != "direct":
                parser_status += f":publisher_{role}"

            doc_start, doc_end = base.detect_effective_dates(text) if text else (None, None)
            version = base.detect_source_version(text, final_url) if text else None
            blob_relpath = base.write_blob(out_dir / "blobs", digest, raw)

            snap_idx = len(snapshots)
            snapshots.append({
                "requested_url": requested_url,
                "final_url": final_url,
                "fetched_at": base.utcnow(),
                "http_status": resp.status_code,
                "content_type": ctype,
                "byte_count": len(raw),
                "sha256": digest,
                "blob_relpath": blob_relpath,
                "parser_status": parser_status,
                "title": title,
                "source_version": version,
                "effective_from": doc_start,
                "effective_to": doc_end,
            })

            if should_parse:
                for term in extract_terms_v2(text, final_url):
                    terms_payload.append((snap_idx, term))

            if auth_page:
                continue

            if depth < max_depth and links:
                for href, anchor in links[:600]:
                    href = base.canonicalize_url(href) or href
                    if f"{href}|0" in seen or f"{href}|1" in seen:
                        continue

                    child_parse = parse_flag
                    follow = False

                    if base.same_site(src.tariff_url, href) or base.same_site(final_url, href):
                        follow = likely_tariff_link_v2(href, anchor, depth)
                        if family != "direct" and _entity_specific_same_site_link(src, anchor, href):
                            child_parse = True
                            follow = True
                    else:
                        follow, cross_parse = publishers.allow_cross_publisher_link(
                            family,
                            href,
                            anchor,
                            src.organization_no,
                            src.legal_name,
                            src.trade_name,
                        )
                        child_parse = child_parse or cross_parse

                    if follow:
                        queue.append((href, depth + 1, child_parse, "discovered_link"))

        except Exception as exc:
            errors.append({
                "url": requested_url,
                "stage": "fetch",
                "error_type": type(exc).__name__,
                "detail": str(exc)[:2000],
            })

    if family != "direct" and entity_scoped_snapshots == 0:
        errors.append({
            "url": src.tariff_url,
            "stage": "publisher_adapter",
            "error_type": "EntityTariffNotResolved",
            "detail": (
                f"Publisher family {family} was inventoried but no entity-scoped "
                "tariff content was resolved for this FMC organization in this run."
            ),
        })

    return {
        "source": src,
        "snapshots": snapshots,
        "terms": terms_payload,
        "errors": errors,
        "seen_count": len(seen),
    }


# Monkeypatch only the execution seams; storage/CLI remain the reviewed core contract.
base.fetch_bytes = fetch_bytes_cached
base.likely_tariff_link = likely_tariff_link_v2
base.extract_terms = extract_terms_v2
base.crawl_one_location = crawl_one_location_v2


if __name__ == "__main__":
    raise SystemExit(base.main())
