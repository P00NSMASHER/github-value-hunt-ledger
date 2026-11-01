#!/usr/bin/env python3
"""Offline, evidence-honest quality gate for RETALLY's scheduled organic social posts.

Reads an explicitly provided Metricool JSON export. Makes NO network calls and
never schedules, publishes, contacts a customer or verifies a public permalink.
The stable post UUID (not Metricool's mutable numeric ID) identifies issues.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

SITE = "www.retallyrecovery.com"
NETWORKS = {"facebook", "instagram", "youtube", "linkedin"}
CONTENT_LINK = re.compile(r"https://[^\s<>()]+")
ALLOWED_IMAGE_TYPES = {".jpeg", ".jpg", ".png", ".webp"}
TRUSTED_MEDIA_HOST = "static.metricool.com"
FORBIDDEN_CLAIMS = (
    (re.compile(r"\b(?:we|retally)\s+(?:have\s+)?recovered\s+\$\s*\d", re.I),
     "Unverified first-person dollar recovery claim"),
    (re.compile(r"\bour\s+customers?\s+(?:have\s+)?saved\s+\$", re.I),
     "Unverified customer savings claim"),
    (re.compile(r"\b(?:guarantee|guaranteed)\s+(?:any\s+)?(?:refund|recovery|savings)\b", re.I),
     "Positive guarantee claim requires removal or independent review"),
)


def unwrap(document: dict) -> dict:
    if isinstance(document, dict) and isinstance(document.get("text"), str):
        document = json.loads(document["text"])
    if not isinstance(document, dict) or not isinstance(document.get("data"), list):
        raise ValueError("Expected a Metricool JSON export with data array")
    return document


def local_time(record: dict) -> datetime:
    time_record = record.get("publicationDate")
    if not isinstance(time_record, dict):
        raise ValueError("Missing publicationDate")
    dt = datetime.fromisoformat(time_record["dateTime"])
    if dt.tzinfo is not None:
        raise ValueError("Expected local wall time and separate IANA timezone")
    tz = ZoneInfo(time_record["timezone"])
    aware = dt.replace(tzinfo=tz)
    if aware.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != dt:
        raise ValueError("Nonexistent local wall time")
    return aware


def _urls(caption: str) -> list[str]:
    return [x.rstrip(".,;]") for x in CONTENT_LINK.findall(caption)]


def site_link(url: str, network: str, *, site_dir: Path | None) -> tuple[bool, str]:
    try:
        split = urlsplit(url)
        if (split.scheme != "https" or split.hostname != SITE or split.username or
                split.password or split.port not in (None, 443) or
                "\\" in split.path or ".." in split.path or "%" in split.path):
            return False, "Not the exact canonical HTTPS RETALLY host/path"
        query = parse_qs(split.query, keep_blank_values=True)
        required = {"utm_source": network, "utm_medium": "organic_social"}
        for key, value in required.items():
            if query.get(key) != [value]:
                return False, f"Missing or incorrect {key}"
        if not query.get("utm_campaign", [""])[0] or not query.get("utm_content", [""])[0]:
            return False, "Missing campaign/content attribution"
        if split.path.startswith("/api/") or split.fragment == "start-audit":
            return False, "Links directly to an unverified intake route"
        if site_dir is not None and split.path != "/":
            stem = split.path.strip("/")
            if not re.fullmatch(r"[a-z0-9-]+", stem):
                return False, "Not a public canonical extension-free content path"
            if not (site_dir / (stem + ".html")).is_file():
                return False, "No matching public source page in the website repository"
        return True, ""
    except (ValueError, TypeError, IndexError, KeyError):
        return False, "Malformed campaign URL"


def media_link(url: str, network: str) -> bool:
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            return False
        if p.hostname != TRUSTED_MEDIA_HOST or not p.path.startswith("/planner/"):
            return False
        suffix = Path(p.path).suffix.lower()
        return suffix == ".mp4" if network == "youtube" else suffix in ALLOWED_IMAGE_TYPES
    except (TypeError, ValueError):
        return False


def classify_first_line(caption: str) -> str | None:
    first = caption.strip().split("\n", 1)[0].lower()
    if "liftgate" in first:
        return "liftgate"
    if "detention" in first or "gate log" in first:
        return "detention"
    if "fuel surcharge" in first:
        return "fuel"
    if "rate sheet" in first or "rate version" in first:
        return "rate"
    if "credit" in first and ("reverse" in first or "reversal" in first):
        return "credit"
    return None


def audit(snapshot: dict, *, site_dir: Path | None = None) -> dict:
    rows = unwrap(snapshot)["data"]
    issues = []
    records = []
    seen = set()
    times = set()
    images_by_network = defaultdict(list)

    def note(uuid: str, network: str, severity: str, code: str, detail: str):
        issues.append({"uuid": uuid, "network": network, "severity": severity,
                       "code": code, "detail": detail})

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every post must be an object")
        providers = row.get("providers")
        if not isinstance(providers, list) or len(providers) != 1:
            raise ValueError("Expected one provider per planner post")
        network = providers[0].get("network")
        if network not in NETWORKS:
            continue
        uid = row.get("uuid")
        if not isinstance(uid, str) or not uid or uid in seen:
            raise ValueError("Missing or duplicate immutable post UUID")
        seen.add(uid)
        when = local_time(row)
        if type(row.get("draft")) is not bool or type(row.get("autoPublish")) is not bool:
            raise ValueError("draft/autoPublish must be explicit booleans")
        draft, auto = row["draft"], row["autoPublish"]
        caption = row.get("text")
        if not isinstance(caption, str):
            raise ValueError("Caption must be a string")
        media, alts = row.get("media", []), row.get("mediaAltText", [])
        if not isinstance(media, list) or not isinstance(alts, list):
            raise ValueError("Media/alt text must be lists")
        status = providers[0].get("status")
        records.append({"uuid": uid, "network": network,
                        "scheduled": when.isoformat(), "draft": draft,
                        "automatic": auto, "provider_status": status})
        if draft:
            if auto:
                note(uid, network, "HIGH", "DRAFT_AUTO", "Draft must not auto-publish")
            continue
        stamp = (network, when.astimezone(timezone.utc).isoformat())
        if stamp in times:
            note(uid, network, "HIGH", "SLOT_COLLISION", "Another post occupies this exact platform/time")
        times.add(stamp)
        if not auto:
            note(uid, network, "HIGH", "AUTO_DISABLED", "Non-draft lacks auto-publishing")
        if status in {"FAILED", "ERROR", "REJECTED"}:
            note(uid, network, "HIGH", "PROVIDER_FAILED", "Planner reports provider failure")
        if not caption.strip():
            note(uid, network, "HIGH", "EMPTY_CAPTION", "Published content has no copy")
        if len(caption) > (2200 if network == "instagram" else 5000):
            note(uid, network, "HIGH", "CAPTION_TOO_LONG", "Caption exceeds conservative platform limit")
        for pattern, message in FORBIDDEN_CLAIMS:
            if pattern.search(caption):
                note(uid, network, "HIGH", "UNVERIFIED_CLAIM", message)
        if re.search(r"\b(?:gate\s+in|gate\s+out)\s*:\s*\d\d:\d\d", caption, re.I):
            if not re.search(r"\b(?:illustrative|hypothetical|sample)\b", caption, re.I):
                note(uid, network, "HIGH", "UNLABELLED_SCENARIO",
                     "Timestamp-based synthetic example must be disclosed as illustrative")

        if network in {"instagram", "youtube"} and not media:
            note(uid, network, "HIGH", "REQUIRED_MEDIA_MISSING", "Network requires image/video")
        elif network == "facebook" and not media:
            note(uid, network, "WARN", "TEXT_ONLY", "RETALLY's visual-first campaign has no artwork")
        if len(alts) != len(media) and network != "youtube":
            note(uid, network, "HIGH", "ALT_COUNT", "Media and alt descriptions are not paired")
        for index, url in enumerate(media):
            if not isinstance(url, str) or not media_link(url, network):
                note(uid, network, "HIGH", "UNTRUSTED_MEDIA", "Media URL/type is not approved")
            if network != "youtube":
                alt = alts[index] if index < len(alts) else ""
                if not isinstance(alt, str) or len(alt.strip()) < 20:
                    note(uid, network, "WARN", "WEAK_ALT", "Image needs descriptive alternative text")
                images_by_network[(network, url)].append(uid)

        if media and network != "youtube":
            topic = classify_first_line(caption)
            first_alt = str(alts[0]).lower() if alts else ""
            synonyms = {"liftgate": ("liftgate",), "detention": ("detention", "gate", "minutes"),
                        "fuel": ("fuel", "surcharge"), "rate": ("rate", "tariff"),
                        "credit": ("credit", "reconciliation", "ledger")}
            if topic and not any(term in first_alt for term in synonyms[topic]):
                note(uid, network, "HIGH", "VISUAL_TOPIC_MISMATCH",
                     f"Lead topic '{topic}' absent from first artwork's description")

        links = _urls(caption)
        if network in {"facebook", "youtube"}:
            good = [u for u in links if site_link(u, network, site_dir=site_dir)[0]]
            if len(good) != 1 or len(links) != 1:
                note(uid, network, "HIGH", "INVALID_TRACKED_CTA",
                     "Require exactly one canonical, source-tagged, source-backed educational link")
            elif urlsplit(good[0]).path == "/" and urlsplit(good[0]).fragment == "start-audit":
                note(uid, network, "HIGH", "INTAKE_CTA", "Do not promote disabled intake")
        elif network == "instagram":
            if links:
                note(uid, network, "WARN", "NONCLICKABLE_INSTAGRAM_URL",
                     "An Instagram caption link is not clickable; favor profile link")
            if not any(phrase in caption.lower() for phrase in (
                    "link in bio", "link in our bio", "in our bio",
                    "save this", "save for", "save it", "swipe", "share this")):
                note(uid, network, "INFO", "LOW_CONVERSION_CTA",
                     "Consider one practical save/share/bio action without formulaic repetition")
        if network == "youtube":
            details = row.get("youtubeData") or {}
            if details.get("madeForKids") is not False or not details.get("title"):
                note(uid, network, "HIGH", "YOUTUBE_METADATA", "Audience and title missing")
    for (network, url), uuids in images_by_network.items():
        if len(uuids) > 3:
            for uid in uuids[3:]:
                note(uid, network, "INFO", "CREATIVE_FATIGUE",
                     "Exact visual reused more than three times on the same platform")
    totals = Counter(x["severity"] for x in issues)
    return {
        "scope": "READ_ONLY_PLANNER_QUALITY_NOT_PUBLICATION_OR_REAL_CUSTOMER_PROOF",
        "checked_posts": len(records),
        "active_posts": sum(not x["draft"] for x in records),
        "draft_posts": sum(x["draft"] for x in records),
        "provider_pending_is_not_publication_proof": True,
        "severity_counts": {s: totals[s] for s in ("HIGH", "WARN", "INFO")},
        "issues": sorted(issues, key=lambda x: ({"HIGH": 0, "WARN": 1, "INFO": 2}[x["severity"]],
                                                      x["network"], x["uuid"], x["code"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", required=True, type=Path)
    parser.add_argument("--site-root", type=Path,
                        default=Path(__file__).resolve().parents[3] / "site")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--fail-on-high", action="store_true")
    args = parser.parse_args()
    source = args.site_root if args.site_root.is_dir() else None
    report = audit(json.loads(args.schedule.read_text(encoding="utf-8")), site_dir=source)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output:
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if args.fail_on_high and report["severity_counts"]["HIGH"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
