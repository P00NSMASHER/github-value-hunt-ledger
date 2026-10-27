#!/usr/bin/env python3
"""Read-only cross-provider reconciliation for RETALLY Facebook posts.

Consumes explicit, time-stamped Metricool and Windsor.ai exports. An account
match and a post id match are necessary but NEVER prove public visibility,
customer inquiries, attributable sales, or recovered freight charges.

This code has no network access or publishing side effects.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, date
from pathlib import Path
from urllib.parse import urlsplit

from metricool_join import _caption, _metric, _published_date
from social_review import parse_timestamp
from social_source_identity import review as identity_review

FB_FIELDS = (
    "FBPO01", "FBPO03", "FBPO04", "FBPO06",
    "FBPO08", "FBPO09", "FBPO11", "FBPO12", "FBPO13", "FBPO14",
)
METRIC_FIELDS = {
    "post_impressions": ("FBPO11", "post_impressions"),
    "post_reach": ("FBPO12", "post_impressions_unique"),
    "post_reactions": ("FBPO13", "post_reactions_total"),
    "post_comments": ("FBPO08", "post_comments_total"),
    "post_shares": ("FBPO14", "post_activity_by_action_type_share"),
    "post_link_clicks": ("FBPO09", "post_clicks_by_type_link_clicks"),
}
WINDSOR_FIELDS = frozenset({
    "account_id", "date", "post_id", "post_message", "permalink_url",
    "is_published", *[p[1] for p in METRIC_FIELDS.values()],
})


def _id(value, expected_page: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"([0-9]{6,25})_([0-9]{6,25})", value)
    return match.group(2) if match and match.group(1) == expected_page else None


def _url_post_id(value) -> str | None:
    """Allow page aliases, but require Facebook HTTPS post URL and exact post ID."""
    if not isinstance(value, str):
        return None
    try:
        p = urlsplit(value)
        if (p.scheme != "https" or p.hostname not in
                {"facebook.com", "www.facebook.com", "m.facebook.com"} or
                p.username or p.password or p.port is not None):
            return None
        match = re.fullmatch(r"/[^/]+/posts/([0-9]{6,25})/?", p.path)
        return match.group(1) if match and not p.query and not p.fragment else None
    except (ValueError, TypeError):
        return None


def _time(value: str, as_of: datetime) -> str:
    observed = parse_timestamp(value)
    if observed > as_of:
        raise ValueError("Observation timestamp cannot be in the future")
    return observed.isoformat()


def _metricool_rows(export: dict, expected_page: str, as_of: datetime):
    if not isinstance(export, dict):
        raise ValueError("Metricool export must be a JSON object")
    fields = export.get("field_ids")
    if not isinstance(fields, list) or len(fields) != len(set(fields)):
        raise ValueError("Metricool field IDs must be a unique ordered list")
    missing = set(FB_FIELDS).difference(fields)
    if missing:
        raise ValueError(f"Metricool export missing required fields: {sorted(missing)}")
    stamp = _time(export.get("observed_at"), as_of)
    source = export.get("rows")
    if not isinstance(source, list):
        raise ValueError("Metricool export must include rows")
    records = {}
    rejected = []
    for index, values in enumerate(source, 1):
        if not isinstance(values, list) or len(values) != len(fields):
            raise ValueError("Metricool row does not match field list")
        row = dict(zip(fields, values))
        key = _id(row["FBPO04"], expected_page)
        if not key:
            rejected.append({"source": "metricool", "row": index, "reason": "ACCOUNT_OR_POST_ID_MISMATCH"})
            continue
        if key in records:
            raise ValueError("Duplicate Metricool post ID")
        if not _caption(row["FBPO03"]):
            rejected.append({"source": "metricool", "row": index, "reason": "EMPTY_CAPTION"})
            continue
        try:
            day = _published_date(row["FBPO01"])
        except ValueError:
            rejected.append({"source": "metricool", "row": index, "reason": "INVALID_DATE"})
            continue
        if _url_post_id(row["FBPO06"]) != key:
            rejected.append({"source": "metricool", "row": index, "reason": "INVALID_POST_PERMALINK"})
            continue
        try:
            metrics = {name: _metric(row[left]) for name, (left, _) in METRIC_FIELDS.items()}
        except ValueError:
            rejected.append({"source": "metricool", "row": index, "reason": "INVALID_COUNTER"})
            continue
        records[key] = {"date": day, "caption": _caption(row["FBPO03"]),
                        "candidate_url": row["FBPO06"], "metrics": metrics}
    return records, rejected, stamp


def _published(value) -> bool | None:
    if value is True or value == "True" or value == "true":
        return True
    if value is False or value == "False" or value == "false":
        return False
    return None


def _windsor_rows(snapshot: dict, expected_page: str, as_of: datetime):
    if not isinstance(snapshot, dict):
        raise ValueError("Windsor export must be a JSON object")
    stamp = _time(snapshot.get("observed_at"), as_of)
    rows = snapshot.get("result")
    if not isinstance(rows, list):
        raise ValueError("Windsor export must contain result: []")
    records = {}
    rejected = []
    ignored_other_pages = 0
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError("Windsor Post row must be an object")
        if row.get("account_id") != expected_page:
            ignored_other_pages += 1
            continue
        key = _id(row.get("post_id"), expected_page)
        if not key:
            rejected.append({"source": "windsor", "row": index, "reason": "ACCOUNT_OR_POST_ID_MISMATCH"})
            continue
        if key in records:
            raise ValueError("Duplicate Windsor post ID")
        if _url_post_id(row.get("permalink_url")) != key:
            rejected.append({"source": "windsor", "row": index, "reason": "INVALID_POST_PERMALINK"})
            continue
        try:
            day = date.fromisoformat(row["date"])
        except (ValueError, TypeError, KeyError):
            rejected.append({"source": "windsor", "row": index, "reason": "INVALID_DATE"})
            continue
        caption = _caption(row.get("post_message"))
        if not caption:
            rejected.append({"source": "windsor", "row": index, "reason": "EMPTY_CAPTION"})
            continue
        try:
            metrics = {name: _metric(row.get(right)) for name, (_, right) in METRIC_FIELDS.items()}
        except ValueError:
            rejected.append({"source": "windsor", "row": index, "reason": "INVALID_COUNTER"})
            continue
        records[key] = {"date": day, "caption": caption,
                        "candidate_url": row["permalink_url"], "metrics": metrics,
                        "provider_published": _published(row.get("is_published"))}
    return records, rejected, ignored_other_pages, stamp


def reconcile(metricool_brand: dict, windsor_connections: dict,
              metricool_posts: dict, windsor_posts: dict, *,
              as_of: datetime) -> dict:
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be offset-aware")
    as_of = as_of.astimezone(timezone.utc)
    identity = identity_review(metricool_brand, windsor_connections)
    fb = identity["platforms"]["facebook"]
    if fb["state"] != "IDENTITY_MATCH" or not fb["exact_matched_account_id"]:
        return {
            "state": "ACCOUNT_IDENTITY_BLOCKED",
            "reason": fb["state"],
            "checked_posts": 0,
            "candidates": [],
            "not_verified": True,
            "evidence_limits": [
                "Never query or compare records from unverified page accounts.",
                "No confirmation of public visibility, outcomes, or qualified leads.",
            ],
        }
    page = fb["exact_matched_account_id"]
    first, first_rejected, m_observed = _metricool_rows(metricool_posts, page, as_of)
    second, second_rejected, ignored, w_observed = _windsor_rows(windsor_posts, page, as_of)
    candidates, skipped = [], [*first_rejected, *second_rejected]
    for key, m in sorted(first.items()):
        w = second.get(key)
        if not w:
            skipped.append({"source": "reconcile", "post_id_suffix": key,
                            "reason": "NO_MATCHING_SECOND_PROVIDER"})
            continue
        if m["caption"] != w["caption"]:
            skipped.append({"source": "reconcile", "post_id_suffix": key,
                            "reason": "POST_CAPTION_MISMATCH"})
            continue
        if abs((m["date"] - w["date"]).days) > 1:
            skipped.append({"source": "reconcile", "post_id_suffix": key,
                            "reason": "POST_DATE_DISAGREEMENT"})
            continue
        metric_comparison = {}
        disagreements = []
        for metric_name in METRIC_FIELDS:
            a, b = m["metrics"][metric_name], w["metrics"][metric_name]
            state = ("NOT_COMPARABLE" if a is None or b is None else
                     "MATCH" if a == b else "RECHECK_PROVIDER_LAG_OR_DEFINITION")
            if state == "RECHECK_PROVIDER_LAG_OR_DEFINITION":
                disagreements.append(metric_name)
            metric_comparison[metric_name] = {
                "metricool": a, "windsor": b, "state": state,
            }
        status = (
            "CROSS_PROVIDER_REPORTED_PUBLISHED"
            if w["provider_published"] is True else
            "WINDSOR_REPORTS_NOT_PUBLISHED"
            if w["provider_published"] is False else
            "PUBLISH_STATE_UNKNOWN"
        )
        candidates.append({
            "post_id_suffix": key,
            "state": status,
            "metricool_post_candidate": m["candidate_url"],
            "windsor_post_candidate": w["candidate_url"],
            "same_underlying_post_id": True,
            "exact_caption_and_date_reconciled": True,
            "page_alias_paths_differ": m["candidate_url"] != w["candidate_url"],
            "counter_comparison": metric_comparison,
            "counter_disagreements": disagreements,
            "independently_visible_to_public": False,
            "verified_customer_lead": False,
        })
    return {
        "state": "ACCOUNT_SCOPED_PROVIDER_RECONCILIATION_ONLY",
        "as_of_utc": as_of.isoformat(),
        "metricool_observed_at": m_observed,
        "windsor_observed_at": w_observed,
        "checked_posts": len(first),
        "matched_provider_post_candidates": len(candidates),
        "ignored_unrelated_page_rows": ignored,
        "independently_verified_public_posts": 0,
        "candidates": candidates,
        "skipped": skipped,
        "not_verified": True,
        "evidence_limits": [
            "The connector-reported is_published flag is not public-permalink verification.",
            "Different Facebook Page alias URLs may identify the same immutable post ID.",
            "Source metric differences can reflect lag and non-identical measurement definitions.",
            "Post impressions, summed post reach and link clicks do not establish unique leads.",
            "Qualified leads require a received, reviewed inquiry; recovery requires actual eligible funds.",
            "A disconnected or mismatched Instagram or YouTube account must not be included.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metricool-brand", required=True, type=Path)
    parser.add_argument("--windsor-connections", required=True, type=Path)
    parser.add_argument("--metricool-posts", required=True, type=Path)
    parser.add_argument("--windsor-posts", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    result = reconcile(load(args.metricool_brand), load(args.windsor_connections),
                       load(args.metricool_posts), load(args.windsor_posts),
                       as_of=parse_timestamp(args.as_of))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "state": result["state"],
        "candidate_posts": result.get("matched_provider_post_candidates", 0),
        "independently_verified_public_posts": result.get("independently_verified_public_posts", 0),
        "review_required": result.get("skipped", []),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
