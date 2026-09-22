#!/usr/bin/env python3
"""Production entrypoint for the FMC Tariff Rule Ledger."""

from __future__ import annotations

import json
from pathlib import Path

import crawler as base
import crawler_v2 as v2
import currency_terms


_CORE_TERMS = v2.extract_terms_v2
_CORE_COMMAND_CRAWL = base.command_crawl
_CORE_CRAWL_ONE = v2.crawl_one_location_v2
PRODUCTION_PARSER_VERSION = "fmc-ledger-v3-crawl"


def extract_terms_production(text: str, url: str):
    terms = [*_CORE_TERMS(text, url), *currency_terms.extract_non_usd_terms(text, url)]
    seen = set()
    out = []
    for term in terms:
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


def snapshot_fmc_directories(out_dir: Path, timeout: int, max_bytes: int) -> list[dict]:
    """Preserve the exact FMC current/history directory pages used for discovery."""
    manifest = []
    out_dir.mkdir(parents=True, exist_ok=True)

    for entity_class, active, url in base.DIRECTORY_REPORTS:
        entry = {
            "entity_class": entity_class,
            "active": active,
            "url": url,
            "fetched_at": base.utcnow(),
        }
        try:
            raw, resp = v2.fetch_bytes_cached(url, timeout, max_bytes)
            digest = base.sha256_bytes(raw)
            rel = base.write_blob(out_dir / "blobs", digest, raw)
            rows, parsed_digest = base.parse_directory_report(
                entity_class, active, url, timeout, max_bytes
            )
            entry.update({
                "final_url": base.canonicalize_url(resp.url) or resp.url,
                "http_status": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "byte_count": len(raw),
                "sha256": digest,
                "blob_relpath": rel,
                "parsed_sha256": parsed_digest,
                "tariff_location_rows": len(rows),
                "status": "snapshotted",
            })
        except Exception as exc:
            entry.update({
                "status": "error",
                "error_type": type(exc).__name__,
                "detail": str(exc)[:2000],
            })
        manifest.append(entry)

    (out_dir / "fmc_directory_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def crawl_one_location_production(*args, **kwargs):
    result = _CORE_CRAWL_ONE(*args, **kwargs)
    result["parser_version"] = PRODUCTION_PARSER_VERSION
    return result


def command_crawl_production(args):
    out_dir = Path(args.out).resolve()
    manifest = snapshot_fmc_directories(out_dir, args.timeout, args.max_bytes)
    ok = sum(item["status"] == "snapshotted" for item in manifest)
    if ok == 0:
        raise SystemExit("FMC directory snapshot failed for every source report")
    return _CORE_COMMAND_CRAWL(args)


# Install final production semantics on top of the reviewed v2 discovery/storage layer.
v2.extract_terms_v2 = extract_terms_production
base.extract_terms = extract_terms_production
base.crawl_one_location = crawl_one_location_production
base.command_crawl = command_crawl_production


if __name__ == "__main__":
    raise SystemExit(base.main())
