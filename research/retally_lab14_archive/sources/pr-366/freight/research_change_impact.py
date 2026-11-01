"""Mission 5: offline source-change analysis and impact/refresh queues for Lab 14.

Compares ONLY manually provided source-acquisition receipts. HTTP responses,
receipt hashes and analyst excerpts do not establish publisher authenticity,
regulatory authority, vendor truth, or customer outcomes. No live network.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
from pathlib import Path
import re

from freight.research_source_acquisition import (
    MAX_BYTES, MAX_EXCERPT_CHARS, SAFE_MIME, canonical_sha,
    sha_hex, validate_manifest,
)
from freight.research_intelligence import iso
from freight.research_public_campaign import campaign_registry
from freight.research_evidence_gate import run_mission


ROOT = Path(__file__).resolve().parent
HEX64 = re.compile(r"^[0-9a-f]{64}$")
GOOD = "CANDIDATE_UNREVIEWED"
BAD = "FETCH_FAILED_OR_REJECTED"
COMMON = {
    "id", "publisher", "lane", "url", "captured_at_utc",
    "publisher_content_truth_verified", "claim_import_authorized", "status",
}
GOOD_FIELDS = COMMON | {
    "http_status", "content_type", "body_size_bytes",
    "raw_body_sha256", "preview_excerpt", "preview_excerpt_sha256",
    "full_body_saved",
}
BAD_FIELDS = COMMON | {"reason"}
HARD_GATE = (
    "Capture receipts are untrusted public-page candidates, not evidence "
    "of publisher identity, legal applicability, or a proven research claim. "
    "Even a matching body hash cannot be independently rechecked without "
    "the original body. A change requires human source-level review."
)


def _utc_time(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("INVALID_CAPTURE_TIMESTAMP")
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_CAPTURE_TIMESTAMP") from exc
    if observed.tzinfo is None or observed.utcoffset() != timedelta(0):
        raise ValueError("CAPTURE_TIMESTAMP_MUST_BE_UTC")
    return observed.astimezone(timezone.utc)


def _sha(value: object) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def validate_capture_receipt(receipt: object, manifest: dict, *,
                             as_of: date) -> list[str]:
    """Strict detached-receipt shape check; cannot certify historical HTTP truth."""
    errors: list[str] = []
    try:
        validate_manifest(manifest)
    except ValueError as exc:
        return [f"INVALID_SOURCE_MANIFEST:{exc}"]
    if not isinstance(receipt, dict):
        return ["CAPTURE_RECEIPT_MUST_BE_OBJECT"]
    if set(receipt) != {
        "schema_version", "status", "network_execution", "no_claim_verification",
        "captures", "fetch_error_count", "receipt_sha256",
    }:
        errors.append("UNEXPECTED_RECEIPT_FIELDS")
    if receipt.get("schema_version") != 1:
        errors.append("INVALID_CAPTURE_SCHEMA")
    if receipt.get("status") != "CANDIDATES_NEED_HUMAN_SOURCE_REVIEW":
        errors.append("INVALID_CAPTURE_STATUS")
    if receipt.get("network_execution") is not True:
        errors.append("EXECUTION_FLAG_MUST_BE_TRUE_NO_INDEPENDENT_ATTESTATION")
    if receipt.get("no_claim_verification") is not True:
        errors.append("CAPTURE_CANNOT_VERIFY_CLAIMS")
    captures = receipt.get("captures")
    if not isinstance(captures, list) or not 1 <= len(captures) <= 12:
        return errors + ["CAPTURES_MUST_BE_BOUNDED_NONEMPTY_LIST"]
    rows = {s["id"]: s for s in manifest["sources"]}
    seen: set[str] = set()
    failure_count = 0
    time_value: str | None = None
    for idx, row in enumerate(captures):
        prefix = f"CAPTURE[{idx}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix}:ROW_NOT_OBJECT")
            continue
        source_id = row.get("id")
        if not isinstance(source_id, str) or source_id not in rows:
            errors.append(f"{prefix}:UNKNOWN_APPROVED_SOURCE")
            continue
        if source_id in seen:
            errors.append(f"{prefix}:DUPLICATE_CAPTURE_SOURCE")
        seen.add(source_id)
        reference = rows[source_id]
        for key in ("url", "publisher", "lane"):
            if row.get(key) != reference[key]:
                errors.append(f"{prefix}:SOURCE_{key.upper()}_MISMATCH")
        if row.get("publisher_content_truth_verified") is not False:
            errors.append(f"{prefix}:FORGED_PUBLISHER_VERIFICATION")
        if row.get("claim_import_authorized") is not False:
            errors.append(f"{prefix}:UNAUTHORIZED_CLAIM_PROMOTION")
        timestamp = row.get("captured_at_utc")
        try:
            observed = _utc_time(timestamp)
            if observed.date() > as_of:
                errors.append(f"{prefix}:FUTURE_CAPTURE")
        except ValueError as exc:
            errors.append(f"{prefix}:{exc}")
        if time_value is None:
            time_value = timestamp
        elif timestamp != time_value:
            errors.append(f"{prefix}:MIXED_CAPTURE_TIME_IN_ONE_RUN")
        status = row.get("status")
        expected = GOOD_FIELDS if status == GOOD else BAD_FIELDS if status == BAD else set()
        if not expected:
            errors.append(f"{prefix}:INVALID_ITEM_STATUS")
            continue
        if set(row) != expected:
            errors.append(f"{prefix}:UNEXPECTED_OR_MISSING_ITEM_FIELDS")
        if status == BAD:
            failure_count += 1
            if not isinstance(row.get("reason"), str) or not row["reason"] or len(row["reason"]) > 200:
                errors.append(f"{prefix}:INVALID_FAILURE_REASON")
            continue
        if row.get("http_status") != 200 or type(row.get("http_status")) is not int:
            errors.append(f"{prefix}:HTTP_STATUS_UNEXPECTED")
        if row.get("content_type") not in SAFE_MIME:
            errors.append(f"{prefix}:UNSUPPORTED_MIME")
        size = row.get("body_size_bytes")
        if type(size) is not int or not 1 <= size <= MAX_BYTES:
            errors.append(f"{prefix}:BODY_SIZE_INVALID")
        if row.get("full_body_saved") is not False:
            errors.append(f"{prefix}:FULL_BODY_RETENTION_NOT_ALLOWED")
        if not _sha(row.get("raw_body_sha256")):
            errors.append(f"{prefix}:RAW_BODY_HASH_FORMAT")
        preview = row.get("preview_excerpt")
        if not isinstance(preview, str) or not 1 <= len(preview) <= MAX_EXCERPT_CHARS:
            errors.append(f"{prefix}:BOUNDED_PREVIEW_REQUIRED")
        elif sha_hex(preview.encode("utf-8")) != row.get("preview_excerpt_sha256"):
            errors.append(f"{prefix}:PREVIEW_DIGEST_MISMATCH")
    if type(receipt.get("fetch_error_count")) is not int or receipt["fetch_error_count"] != failure_count:
        errors.append("FETCH_ERROR_CENSUS_MISMATCH")
    if not _sha(receipt.get("receipt_sha256")):
        errors.append("RECEIPT_HASH_FORMAT")
    else:
        unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if receipt["receipt_sha256"] != canonical_sha(unsigned):
            errors.append("RECEIPT_TAMPERED")
    return errors


def _record_date(row: dict) -> datetime:
    return _utc_time(row["captured_at_utc"])


def _references(registry: dict, decisions: dict, source_id: str) -> tuple[list[str], list[str], int]:
    claim_ids = sorted(c["id"] for c in registry["claims"] if source_id in c["source_ids"])
    affected = sorted(d["id"] for d in decisions["decisions"]
                      if set(claim_ids) & set(d["claim_ids"]))
    importance = max((c["importance"] for c in registry["claims"]
                      if c["id"] in claim_ids), default=1)
    return claim_ids, affected, importance


def compare_captures(*, before: dict | None, after: dict,
                     manifest: dict, registry: dict, decisions: dict,
                     as_of: date) -> dict:
    """Compare approved source candidates, propagating review obligations only."""
    errors = validate_capture_receipt(after, manifest, as_of=as_of)
    if before is not None:
        errors += ["BASELINE_" + e for e in
                   validate_capture_receipt(before, manifest, as_of=as_of)]
    if errors:
        raise ValueError("INVALID_CAPTURE_COMPARISON:" + ";".join(errors))
    previous = {r["id"]: r for r in (before or {}).get("captures", [])}
    current = {r["id"]: r for r in after["captures"]}
    by_source = {x["id"]: x for x in registry["sources"]}
    result_rows = []
    for source in manifest["sources"]:
        ident = source["id"]
        external_id = "20261010." + ident
        if external_id not in by_source or by_source[external_id]["url"] != source["url"]:
            raise ValueError("SOURCE_REGISTER_MANIFEST_MISMATCH:" + ident)
        a = previous.get(ident)
        b = current.get(ident)
        if a and b and _record_date(b) <= _record_date(a):
            raise ValueError("NON_MONOTONIC_CAPTURE_TIMESTAMPS:" + ident)
        if b is None:
            drift = "NOT_CHECKED_THIS_RUN"
        elif b["status"] == BAD:
            drift = "SOURCE_FETCH_FAILED_REVIEW"
        elif a is None:
            drift = "BASELINE_CAPTURE_UNREVIEWED"
        elif a["status"] == BAD:
            drift = "SOURCE_REAPPEARED_UNREVIEWED"
        elif b["raw_body_sha256"] == a["raw_body_sha256"]:
            drift = "RAW_BODY_UNCHANGED"
        elif b["preview_excerpt_sha256"] == a["preview_excerpt_sha256"]:
            drift = "RAW_CHANGED_PREVIEW_UNCHANGED"
        else:
            drift = "VISIBLE_PREVIEW_CHANGED"

        expires = iso(by_source[external_id]["valid_until"], "valid_until")
        stale = expires < as_of
        change_requires_review = drift in {
            "SOURCE_FETCH_FAILED_REVIEW", "BASELINE_CAPTURE_UNREVIEWED",
            "SOURCE_REAPPEARED_UNREVIEWED", "RAW_CHANGED_PREVIEW_UNCHANGED",
            "VISIBLE_PREVIEW_CHANGED",
        }
        needs_review = stale or change_requires_review
        claim_ids, decision_ids, importance = _references(
            registry, decisions, external_id)
        risk = importance * 10 + len(decision_ids) * 2
        if source["lane"] == "carrier_regulatory":
            risk += 5
        if drift == "VISIBLE_PREVIEW_CHANGED":
            risk += 3
        result_rows.append({
            "source_id": ident, "url": source["url"], "lane": source["lane"],
            "publisher": source["publisher"],
            "baseline_capture_at": a["captured_at_utc"] if a else None,
            "latest_capture_at": b["captured_at_utc"] if b else None,
            "content_change_status": drift, "source_valid_until": expires.isoformat(),
            "expired_source_hold": stale,
            "needs_human_review": needs_review,
            "review_priority_ordinal": risk if needs_review else None,
            "dependent_claim_ids": claim_ids,
            "affected_decision_ids": decision_ids if needs_review else [],
            "claim_truth_or_falsity_determined": False,
            "regulation_or_tariff_currently_effective_proven": False,
            "customer_action_authorized": False,
            "raw_body_reverified_independently": False,
            "next_step": (
                "Independently inspect the original full source, context, "
                "effective date and corresponding claims before updating research."
                if needs_review else
                "No observed substantive change in supplied captures; source "
                "claims remain unverified and subject to their original review."
            ),
        })
    rows = sorted(result_rows, key=lambda r: (
        not r["needs_human_review"], -(r["review_priority_ordinal"] or 0),
        r["source_id"],
    ))
    output = {
        "schema_version": 1, "scope": "DETACHED_RECEIPTS_UNVERIFIED_RESEARCH",
        "as_of": as_of.isoformat(),
        "baseline_supplied": before is not None,
        "source_census": len(rows),
        "human_review_sources": sum(r["needs_human_review"] for r in rows),
        "status_counts": dict(sorted(Counter(x["content_change_status"]
                                             for x in rows).items())),
        "sources": rows,
        "no_claims_automatically_promoted": True,
        "any_publisher_authenticity_proven": False,
        "external_actions_allowed": False,
        "boundary": HARD_GATE,
    }
    output["receipt_sha256"] = canonical_sha(output)
    return output


def build_refresh_queue(*, registry: dict, proof: dict, decisions: dict,
                        as_of: date) -> dict:
    """Current internal source review debt; NO capture or scheduled refresh."""
    source_to_claim: dict[str, list[dict]] = {}
    for claim in registry["claims"]:
        for source_id in claim["source_ids"]:
            source_to_claim.setdefault(source_id, []).append(claim)
    anchor_meta = proof["quote_metadata"]
    observed = {s["source_id"] for s in anchor_meta
                if s["method"] == "PUBLIC_WEB_VIEW"
                and s["support_scope"] == "DIRECT_SCOPE"}
    snippet_only = {s["source_id"] for s in anchor_meta
                    if s["method"] == "SEARCH_RESULT_ONLY"}
    rows = []
    for s in registry["sources"]:
        expires = iso(s["valid_until"], "valid_until")
        days = (expires - as_of).days
        claims = source_to_claim.get(s["id"], [])
        decisions_affected = sorted(
            d["id"] for d in decisions["decisions"]
            if any(c["id"] in d["claim_ids"] for c in claims))
        max_imp = max((c["importance"] for c in claims), default=1)
        if days < 0:
            state = "EXPIRED_SOURCE_HOLD"
        elif days <= 30:
            state = "EXPIRING_WITHIN_30_DAYS"
        elif s["id"] in snippet_only:
            state = "SEARCH_SNIPPET_OR_CONTEXT_REVIEW"
        elif s["id"] not in observed:
            state = "NO_DIRECT_SOURCE_EXCERPT"
        else:
            state = "FRESH_DATE_NOT_INDEPENDENTLY_VERIFIED"
        priority = 3 * max_imp + 2 * len(decisions_affected)
        if s["type"] == "PUBLIC_PRIMARY" and any(
            c["lane"] == "carrier_regulatory" for c in claims
        ):
            priority += 5
        if days < 0:
            priority += 15
        elif days <= 30:
            priority += 8
        rows.append({
            "source_id": s["id"], "url": s["url"], "publisher": s["publisher"],
            "source_type": s["type"], "valid_until": s["valid_until"],
            "days_until_expiry": days,
            "source_review_state": state,
            "dependent_claim_ids": sorted(c["id"] for c in claims),
            "affected_decision_ids": decisions_affected,
            "source_priority_ordinal": priority,
            "review_required_before_external_use": True,
            "independently_verified": False,
            "next_step": (
                "Recheck original publisher page and applicable version; "
                "update a dated source record only after human review."
            ),
        })
    rows.sort(key=lambda x: (-x["source_priority_ordinal"], x["source_id"]))
    report = {
        "schema_version": 1, "scope": "READ_ONLY_MANUAL_REFRESH_BACKLOG",
        "as_of": as_of.isoformat(), "source_count": len(rows),
        "expired_count": sum(x["days_until_expiry"] < 0 for x in rows),
        "due_within_30_days": sum(0 <= x["days_until_expiry"] <= 30 for x in rows),
        "review_queue": rows,
        "automatic_fetch_or_schedule": False,
        "external_actions_allowed": False,
        "any_sources_independently_fact_checked": False,
        "boundary": HARD_GATE,
    }
    report["receipt_sha256"] = canonical_sha(report)
    return report


def render_html(queue: dict, delta: dict | None = None) -> str:
    """Escaped, standalone internal HTML report; no external resources."""
    esc = lambda val: escape(str(val), quote=True)
    top = queue["review_queue"][:20]
    items = "".join(
        '<article class="item"><div class="meta">' + esc(x["source_review_state"])
        + '</div><h3>' + esc(x["publisher"]) + '</h3><p>'
        + esc(x["source_id"]) + ' · ' + esc(x["days_until_expiry"])
        + ' day(s) until expiry</p><p>Affects '
        + str(len(x["dependent_claim_ids"])) + ' claims and '
        + str(len(x["affected_decision_ids"])) + ' research decisions</p>'
        + '<a href="' + esc(x["url"]) + '" rel="noopener noreferrer">Source page</a>'
        + '</article>'
        for x in top
    )
    changes = ""
    if delta is not None:
        changed = [x for x in delta["sources"] if x["needs_human_review"]]
        changes = ('<section><h2>Capture changes requiring review</h2>'
                   + "".join(
                       '<article class="item"><b>' + esc(x["source_id"])
                       + '</b><p>' + esc(x["content_change_status"])
                       + '</p><p>Impacts: '
                       + esc(", ".join(x["affected_decision_ids"]) or "No mapped decisions")
                       + '</p></article>'
                       for x in changed
                   ) + '</section>')
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RETALLY | Source Change Radar</title><style>
:root{--ink:#193a2c;--green:#07834c;--line:#d7e6df}
*{box-sizing:border-box}body{margin:0;background:#f7faf8;color:var(--ink);
font:15px/1.5 system-ui,-apple-system,sans-serif}
main{max-width:1050px;margin:auto;padding:30px 20px 72px}
h1{font-size:clamp(30px,5vw,49px);letter-spacing:-.05em;line-height:1.08}
h2{font-size:22px;margin-top:32px}p,small{color:#61776b}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.item{border:1px solid var(--line);background:#fff;border-radius:14px;padding:18px}
.meta{font-size:11px;font-weight:750;letter-spacing:.08em;color:var(--green)}
.notice{border-left:4px solid var(--green);padding:14px;background:#edf5ee}
a{color:var(--green)}footer{margin-top:32px;border-top:1px solid var(--line);padding-top:20px}
@media(max-width:650px){.grid{grid-template-columns:1fr}}
</style></head><body><main><header><b>RETALLY · LAB 14</b>
<h1>Source Change Radar</h1><p>What changed? Which claims or decisions require fresh review?</p>
<div class="notice">""" + esc(HARD_GATE) + """</div></header>
<h2>Prioritized source review queue</h2><div class="grid">""" + items + """</div>
""" + changes + """
<footer><small>Research-only dated queue · Receipt """ + esc(queue["receipt_sha256"]) + """</small>
<p><a href="research.html">Market Research</a> ·
<a href="opposition.html">Opposition Decisions</a> ·
<a href="index.html">Lab Control Center</a></p></footer>
</main></body></html>"""


def mission5_queue(*, as_of: date) -> dict:
    registry = campaign_registry(as_of=as_of)
    proof, decisions = run_mission(as_of=as_of)
    return build_refresh_queue(registry=registry, proof=proof,
                               decisions=decisions, as_of=as_of)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline public-source change impact")
    parser.add_argument("--as-of-date", default=date.today().isoformat())
    parser.add_argument("--before", type=Path,
                        help="Previous detached candidate receipt (optional)")
    parser.add_argument("--after", type=Path,
                        help="New detached candidate receipt (optional)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.before and not args.after:
        parser.error("--before requires --after")
    now = iso(args.as_of_date, "as-of-date")
    registry = campaign_registry(as_of=now)
    proof, decisions = run_mission(as_of=now)
    queue = build_refresh_queue(registry=registry, proof=proof,
                                decisions=decisions, as_of=now)
    delta = None
    if args.after:
        manifest = json.loads((ROOT / "research/PUBLIC_SOURCE_MANIFEST_20261010.json")
                              .read_text(encoding="utf-8"))
        before = (json.loads(args.before.read_text(encoding="utf-8"))
                  if args.before else None)
        after = json.loads(args.after.read_text(encoding="utf-8"))
        delta = compare_captures(
            before=before, after=after, manifest=manifest,
            registry=registry, decisions=decisions, as_of=now,
        )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "research_refresh_queue.json").write_text(
        json.dumps(queue, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if delta:
        (args.out / "research_source_changes.json").write_text(
            json.dumps(delta, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.out / "research_refresh.html").write_text(
        render_html(queue, delta), encoding="utf-8")
    print(json.dumps({
        "scope": queue["scope"],
        "review_queue_sources": queue["source_count"],
        "expired": queue["expired_count"],
        "source_change_comparison_run": delta is not None,
        "receipt_sha256": queue["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
