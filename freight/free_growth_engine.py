"""Deterministic free-acquisition planner for Freight Recovery.

No prospect PII belongs here. The engine operates on aggregate counts and
channel state, then emits bounded next actions for outbound, SEO, directory,
referral and content channels.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from enum import Enum
import argparse
import json
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse


class Channel(str, Enum):
    OUTBOUND_EMAIL = "OUTBOUND_EMAIL"
    SEO = "SEO"
    DIRECTORIES = "DIRECTORIES"
    REFERRALS = "REFERRALS"
    CONTENT = "CONTENT"


@dataclass(frozen=True)
class GrowthSnapshot:
    as_of_date: date
    launch_date: date
    prospects_screened: int
    sent_today: int
    cold_emails_total: int
    hard_bounces_total: int
    substantive_replies: int
    qualified_buyers: int
    seo_pages_live: int
    directory_profiles_live: int
    referral_partners_contacted: int
    organic_posts_published_this_week: int
    outreach_preflight_ready: bool = False

    def __post_init__(self):
        if type(self.outreach_preflight_ready) is not bool:
            raise ValueError("outreach_preflight_ready must be a boolean")
        if self.as_of_date < self.launch_date:
            raise ValueError("as_of_date cannot precede launch_date")
        for name in (
            "prospects_screened",
            "sent_today",
            "cold_emails_total",
            "hard_bounces_total",
            "substantive_replies",
            "qualified_buyers",
            "seo_pages_live",
            "directory_profiles_live",
            "referral_partners_contacted",
            "organic_posts_published_this_week",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(name + " must be a non-negative integer")
        if self.hard_bounces_total > self.cold_emails_total:
            raise ValueError("hard_bounces_total cannot exceed cold_emails_total")


@dataclass(frozen=True)
class GrowthAction:
    priority: int
    channel: Channel
    action: str
    target: str
    reason: str


def _days_since_launch(snapshot: GrowthSnapshot) -> int:
    return (snapshot.as_of_date - snapshot.launch_date).days


def _bounce_rate(snapshot: GrowthSnapshot) -> float:
    if snapshot.cold_emails_total == 0:
        return 0.0
    return snapshot.hard_bounces_total / snapshot.cold_emails_total


def daily_send_cap(snapshot: GrowthSnapshot) -> int:
    """Gradually scale cold outbound while capping sender-risk exposure."""
    days = _days_since_launch(snapshot)
    if snapshot.cold_emails_total >= 10 and _bounce_rate(snapshot) >= 0.03:
        return 0
    if days <= 0:
        return 20
    if days <= 2:
        return 25
    if days <= 6:
        return 30
    return 40


def build_plan(snapshot: GrowthSnapshot) -> tuple[GrowthAction, ...]:
    actions: list[GrowthAction] = []
    cap = daily_send_cap(snapshot)
    bounce = _bounce_rate(snapshot)

    if cap == 0:
        actions.append(GrowthAction(
            0,
            Channel.OUTBOUND_EMAIL,
            "PAUSE",
            "0 sends",
            f"Hard-bounce rate is {bounce:.1%}; verify recipients before resuming.",
        ))
    elif not snapshot.outreach_preflight_ready:
        actions.append(GrowthAction(
            0, Channel.OUTBOUND_EMAIL, "PREP_OUTREACH_SAFETY", "0 sends",
            "Private mailbox reconciliation, suppression, ICP qualification and per-message reservation gate required.",
        ))
    else:
        remaining = max(0, cap - snapshot.sent_today)
        if remaining:
            actions.append(GrowthAction(
                1,
                Channel.OUTBOUND_EMAIL,
                "SEND_VERIFIED_FIRST_TOUCHES",
                f"up to {remaining} additional verified prospects today",
                f"Current gradual daily cap is {cap}; sender reputation outranks raw volume.",
            ))
        else:
            actions.append(GrowthAction(
                4,
                Channel.OUTBOUND_EMAIL,
                "HOLD_UNTIL_NEXT_SEND_WINDOW",
                "no more cold sends today",
                f"Today's controlled cap of {cap} has been reached.",
            ))

    if snapshot.seo_pages_live < 4:
        actions.append(GrowthAction(
            1, Channel.SEO, "PUBLISH_HIGH_INTENT_PAGES",
            "4 indexed intent pages",
            "Search demand cannot compound until dedicated query pages are live.",
        ))
    else:
        actions.append(GrowthAction(
            4, Channel.SEO, "REQUEST_INDEXING_AND_MONITOR",
            "sitemap + 4 intent pages",
            "Core organic landing pages are live; prioritize indexing and query coverage.",
        ))

    if snapshot.directory_profiles_live < 4:
        actions.append(GrowthAction(
            2, Channel.DIRECTORIES, "CLAIM_FREE_PROFILES",
            "Google Business Profile, Bing Places, Apple Business Connect, LinkedIn Company Page",
            "Free business profiles add branded discovery, citations and another path to the audit site.",
        ))

    if snapshot.referral_partners_contacted < 10:
        actions.append(GrowthAction(
            2, Channel.REFERRALS, "BUILD_REFERRAL_CHANNEL",
            "10 CPAs, fractional CFOs, AP consultants or logistics advisors",
            "Trusted advisors can introduce freight-heavy buyers without paid media.",
        ))

    if snapshot.organic_posts_published_this_week < 2:
        actions.append(GrowthAction(
            3, Channel.CONTENT, "PUBLISH_EVIDENCE_LED_CONTENT",
            f"{2 - snapshot.organic_posts_published_this_week} additional useful post(s) this week",
            "Short practical posts create shareable search/social inventory without invented case studies.",
        ))

    return tuple(sorted(actions, key=lambda x: (x.priority, x.channel.value)))


def tagged_url(
    base_url: str,
    *,
    source: str,
    medium: str,
    campaign: str,
    content: str | None = None,
) -> str:
    if not all(isinstance(x, str) and x.strip() for x in (base_url, source, medium, campaign)):
        raise ValueError("base_url/source/medium/campaign must be non-empty strings")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be absolute http(s)")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({
        "utm_source": source.strip(),
        "utm_medium": medium.strip(),
        "utm_campaign": campaign.strip(),
    })
    if content and content.strip():
        query["utm_content"] = content.strip()
    return urlunparse(parsed._replace(query=urlencode(query)))


def _load_snapshot(path: str) -> GrowthSnapshot:
    data = json.load(open(path, "r", encoding="utf-8"))
    return GrowthSnapshot(
        as_of_date=date.fromisoformat(data["as_of_date"]),
        launch_date=date.fromisoformat(data["launch_date"]),
        prospects_screened=int(data["prospects_screened"]),
        sent_today=int(data["sent_today"]),
        cold_emails_total=int(data["cold_emails_total"]),
        hard_bounces_total=int(data["hard_bounces_total"]),
        substantive_replies=int(data["substantive_replies"]),
        qualified_buyers=int(data["qualified_buyers"]),
        seo_pages_live=int(data["seo_pages_live"]),
        directory_profiles_live=int(data["directory_profiles_live"]),
        referral_partners_contacted=int(data["referral_partners_contacted"]),
        organic_posts_published_this_week=int(data["organic_posts_published_this_week"]),
        outreach_preflight_ready=data.get("outreach_preflight_ready", False),
    )


def _markdown(snapshot: GrowthSnapshot, actions: tuple[GrowthAction, ...]) -> str:
    lines = [
        "# Freight Recovery Free Growth Queue",
        "",
        f"As of: {snapshot.as_of_date.isoformat()}",
        f"Days since launch: {_days_since_launch(snapshot)}",
        f"Cold emails total: {snapshot.cold_emails_total}",
        f"Hard-bounce rate: {_bounce_rate(snapshot):.1%}",
        f"Qualified buyers: {snapshot.qualified_buyers}",
        "",
        "| Priority | Channel | Action | Target | Reason |",
        "|---:|---|---|---|---|",
    ]
    for row in actions:
        lines.append(
            f"| {row.priority} | {row.channel.value} | {row.action} | "
            f"{row.target} | {row.reason} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot_json")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    snapshot = _load_snapshot(args.snapshot_json)
    plan = build_plan(snapshot)
    if args.format == "json":
        print(json.dumps({
            "snapshot": {
                **asdict(snapshot),
                "as_of_date": snapshot.as_of_date.isoformat(),
                "launch_date": snapshot.launch_date.isoformat(),
            },
            "actions": [
                {
                    **asdict(a),
                    "channel": a.channel.value,
                } for a in plan
            ],
        }, indent=2))
    else:
        print(_markdown(snapshot, plan), end="")
