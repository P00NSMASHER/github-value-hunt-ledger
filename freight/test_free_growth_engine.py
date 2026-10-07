from datetime import date
import pytest

from freight.free_growth_engine import (
    Channel,
    GrowthSnapshot,
    build_plan,
    daily_send_cap,
    tagged_url,
)


def snapshot(**overrides):
    base = dict(
        as_of_date=date(2026, 10, 6),
        launch_date=date(2026, 10, 6),
        prospects_screened=100,
        sent_today=20,
        cold_emails_total=20,
        hard_bounces_total=0,
        substantive_replies=0,
        qualified_buyers=0,
        seo_pages_live=4,
        directory_profiles_live=0,
        referral_partners_contacted=0,
        organic_posts_published_this_week=0,
        outreach_preflight_ready=True,
    )
    base.update(overrides)
    return GrowthSnapshot(**base)


def test_day_zero_cap_is_20_and_holds_after_cap():
    s = snapshot()
    assert daily_send_cap(s) == 20
    plan = build_plan(s)
    email = [a for a in plan if a.channel == Channel.OUTBOUND_EMAIL][0]
    assert email.action == "HOLD_UNTIL_NEXT_SEND_WINDOW"


def test_outbound_scales_gradually():
    assert daily_send_cap(snapshot(
        as_of_date=date(2026, 10, 7),
        sent_today=0,
    )) == 25
    assert daily_send_cap(snapshot(
        as_of_date=date(2026, 10, 10),
        sent_today=0,
    )) == 30
    assert daily_send_cap(snapshot(
        as_of_date=date(2026, 10, 14),
        sent_today=0,
    )) == 40


def test_three_percent_hard_bounce_rate_pauses():
    s = snapshot(cold_emails_total=100, hard_bounces_total=3, sent_today=0)
    assert daily_send_cap(s) == 0
    plan = build_plan(s)
    email = [a for a in plan if a.channel == Channel.OUTBOUND_EMAIL][0]
    assert email.action == "PAUSE"


def test_free_channel_gaps_create_actions():
    plan = build_plan(snapshot(seo_pages_live=0))
    channels = {a.channel for a in plan}
    assert Channel.SEO in channels
    assert Channel.DIRECTORIES in channels
    assert Channel.REFERRALS in channels
    assert Channel.CONTENT in channels


def test_tagged_url_preserves_query_and_adds_campaign():
    url = tagged_url(
        "https://example.com/?x=1",
        source="linkedin",
        medium="organic",
        campaign="freight_audit_launch",
        content="post_1",
    )
    assert "x=1" in url
    assert "utm_source=linkedin" in url
    assert "utm_medium=organic" in url
    assert "utm_campaign=freight_audit_launch" in url
    assert "utm_content=post_1" in url


def test_snapshot_rejects_impossible_bounces():
    with pytest.raises(ValueError):
        snapshot(cold_emails_total=2, hard_bounces_total=3)

def test_missing_preflight_defaults_to_prep_without_send():
    from dataclasses import asdict
    inputs = asdict(snapshot(sent_today=0))
    inputs.pop("outreach_preflight_ready")
    plan = build_plan(GrowthSnapshot(**inputs))
    email = [a for a in plan if a.channel == Channel.OUTBOUND_EMAIL][0]
    assert email.action == "PREP_OUTREACH_SAFETY"
    assert email.target == "0 sends"


def test_preflight_readiness_rejects_truthy_strings():
    with pytest.raises(ValueError):
        snapshot(outreach_preflight_ready="true")


def test_preflight_does_not_override_bounce_hold():
    s = snapshot(cold_emails_total=100, hard_bounces_total=3,
                 sent_today=0, outreach_preflight_ready=False)
    email = [a for a in build_plan(s) if a.channel == Channel.OUTBOUND_EMAIL][0]
    assert email.action == "PAUSE"
