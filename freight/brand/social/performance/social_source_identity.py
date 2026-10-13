#!/usr/bin/env python3
"""RETALLY read-only cross-connector social-account identity gate.

Inputs are explicitly exported connector responses. No networking or auth.
A brand name, login email, or generic integration id never proves a
social network's underlying account is RETALLY's account.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED_BRAND = "Retally"
EXPECTED_METRICOOL_BRAND_ID = "7322512"
PLATFORMS = (
    ("facebook", "facebookData", "facebook_organic", "id"),
    ("instagram", "instagramData", "instagram", "username"),
    ("youtube", "youtubeData", "youtube", "channel_id"),
    ("linkedin", "linkedinData", "linkedin_organic", "id"),
)


def unpack(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Connector response must be a JSON object")
    if isinstance(value.get("text"), str):
        result = json.loads(value["text"])
        if not isinstance(result, dict):
            raise ValueError("Connector text must decode to an object")
        return result
    return value


def _clean_id(value) -> str | None:
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    s = str(value).strip()
    if not s or len(s) > 128 or not re.fullmatch(r"[a-zA-Z0-9_-]+", s):
        return None
    return s


def _clean_handle(value) -> str | None:
    if not isinstance(value, str):
        return None
    s = value.strip().lstrip("@").casefold()
    if not re.fullmatch(r"[a-z0-9._]{1,30}", s):
        return None
    return s


def _find_brand(metricool: dict, brand_id: str):
    rows = metricool.get("data")
    if not isinstance(rows, list):
        raise ValueError("Metricool brand list missing")
    matches = [x for x in rows if isinstance(x, dict)
               and str(x.get("id")) == brand_id]
    if len(matches) != 1:
        raise ValueError("Exactly one chosen Metricool brand id is required")
    item = matches[0]
    if str(item.get("label") or "").strip().casefold() != EXPECTED_BRAND.casefold():
        raise ValueError("Connected Metricool brand is not RETALLY")
    data = item.get("networksData")
    if not isinstance(data, dict):
        raise ValueError("RETALLY brand has no declared networks")
    return data


def _accounts(windsor: dict):
    sources = windsor.get("result")
    if not isinstance(sources, list):
        raise ValueError("Windsor connected account list missing")
    result = {}
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            raise ValueError("Malformed connector entry")
        slug = source["id"]
        if slug in result:
            raise ValueError("Duplicate Windsor connector type")
        accounts = source.get("accounts")
        if accounts is None:
            accounts = []
        if not isinstance(accounts, list):
            raise ValueError("Malformed Windsor account list")
        keys = set()
        for account in accounts:
            if not isinstance(account, dict) or _clean_id(account.get("id")) is None:
                raise ValueError("Malformed Windsor account identity")
            key = account["id"]
            if key in keys:
                raise ValueError("Duplicate connected account ID")
            keys.add(key)
        result[slug] = accounts
    return result


def review(metricool: dict, windsor: dict,
           *, brand_id: str = EXPECTED_METRICOOL_BRAND_ID) -> dict:
    brand_id = _clean_id(brand_id)
    if brand_id is None:
        raise ValueError("Invalid Metricool brand id")
    brand = _find_brand(unpack(metricool), brand_id)
    connected = _accounts(unpack(windsor))
    records = {}
    for platform, field, slug, identity_field in PLATFORMS:
        expected_raw = brand.get(field)
        expected = (_clean_handle(expected_raw) if identity_field == "username"
                    else _clean_id(expected_raw))
        rows = connected.get(slug, [])
        if expected is None:
            status, reason = "NOT_VERIFIED", "RETALLY Metricool channel identity is absent"
            matched = []
        elif not rows:
            status, reason = "NOT_CONNECTED", "No corresponding Windsor channel account"
            matched = []
        else:
            matched = []
            for account in rows:
                candidate = (_clean_handle(account.get("name"))
                             if identity_field == "username"
                             else _clean_id(account.get("id")))
                if candidate == expected:
                    matched.append(account)
            if len(matched) == 1:
                status, reason = "IDENTITY_MATCH", "Exact identity agreement for this platform"
            elif len(matched) > 1:
                raise ValueError("Ambiguous duplicate matching cross-source accounts")
            elif identity_field == "channel_id":
                status, reason = "NOT_VERIFIED", "Windsor account id is not the same as the Metricool YouTube channel id"
            else:
                status, reason = "IDENTITY_MISMATCH", "Connected Windsor account is not the RETALLY channel"

        # Restrict all future joins to the one exact matched account. In
        # particular, never pool a differently named personal Instagram.
        safe_id = str(matched[0]["id"]) if len(matched) == 1 else None
        records[platform] = {
            "state": status,
            "reason": reason,
            "cross_source_aggregation_allowed": bool(safe_id),
            "exact_matched_account_id": safe_id,
            "other_accounts_ignored": max(0, len(rows) - len(matched)),
        }
    return {
        "purpose": "ACCOUNT_IDENTITY_ONLY_NOT_POST_PUBLICATION_OR_LEAD_PROOF",
        "metricool_brand_id": brand_id,
        "platforms": records,
        "rules": [
            "Never attribute Instagram analytics from an unmatched personal account to RETALLY.",
            "A YouTube connector account or login email is not a confirmed channel id.",
            "Facebook account-id agreement permits exact-account selection, not proof of social publication.",
            "Metricool scheduled status is not an independently verified public permalink.",
            "No cross-platform conversion or recovered-funds count can be inferred.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metricool", type=Path, required=True)
    parser.add_argument("--windsor", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-mismatch", action="store_true",
                        help="Optional exit 2 if any connected account is mismatched")
    args = parser.parse_args()
    report = review(json.loads(args.metricool.read_text(encoding="utf-8")),
                    json.loads(args.windsor.read_text(encoding="utf-8")))
    result = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)
    if args.fail_on_mismatch and any(
            x["state"] == "IDENTITY_MISMATCH" for x in report["platforms"].values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
