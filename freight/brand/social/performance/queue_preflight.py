#!/usr/bin/env python3
"""RETALLY offline preflight: compare an immutable planner snapshot with a fresh export.

Does not contact Facebook, Instagram or Metricool; does not publish or schedule.
Disappearance from the *upcoming* feed is never evidence of a successful post.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from social_review import (
    LOCAL_TIMEZONE, POSTING_HOURS, VALID_NETWORKS,
    parse_timestamp, read_json, scheduled_datetime,
)


def _index(document: dict, label: str) -> dict:
    """Index FB/IG items by immutable UUID. Reject ambiguous source records."""
    if not isinstance(document, dict) or not isinstance(document.get('data'), list):
        raise ValueError(f'{label}: expected a Metricool data array')
    records = {}
    for row in document['data']:
        if not isinstance(row, dict):
            raise ValueError(f'{label}: post is not an object')
        providers = row.get('providers')
        if not isinstance(providers, list):
            raise ValueError(f'{label}: providers must be an array')
        managed = [x for x in providers if isinstance(x, dict)
                   and x.get('network') in VALID_NETWORKS]
        if not managed:
            continue
        if len(providers) != 1 or len(managed) != 1:
            raise ValueError(f'{label}: ambiguous multi-network post')
        uid = row.get('uuid')
        if not isinstance(uid, str) or not uid.strip() or uid in records:
            raise ValueError(f'{label}: missing or repeated immutable UUID')
        for key in ('draft', 'autoPublish'):
            if type(row.get(key)) is not bool:
                raise ValueError(f'{label}: {key} must be a boolean for {uid}')
        if not isinstance(row.get('text'), str):
            raise ValueError(f'{label}: missing caption for {uid}')
        for key in ('media', 'mediaAltText'):
            vals = row.get(key)
            if not isinstance(vals, list) or any(not isinstance(v, str) for v in vals):
                raise ValueError(f'{label}: {key} must be a string list for {uid}')
        scheduled_datetime(row)  # validates IANA local wall-time
        records[uid] = row
    if not records:
        raise ValueError(f'{label}: no Facebook/Instagram rows; refusing all-clear')
    return records


def _event(events: list, uid: str, network: str, severity: str, code: str, detail: str):
    events.append({'uuid': uid, 'network': network, 'severity': severity,
                   'code': code, 'detail': detail})


def _quality(uid: str, row: dict, events: list):
    network = row['providers'][0]['network']
    draft = row['draft']
    if draft and row['autoPublish']:
        _event(events, uid, network, 'HIGH', 'DRAFT_AUTO_PUBLISH_ON',
               'An unpublished draft has automatic publishing enabled.')
    if draft:
        return
    if not row['autoPublish']:
        _event(events, uid, network, 'HIGH', 'ACTIVE_AUTO_PUBLISH_OFF',
               'Active post is no longer set for automatic publication.')
    media, alts = row['media'], row['mediaAltText']
    if not media:
        _event(events, uid, network, 'HIGH', 'ACTIVE_MISSING_MEDIA',
               'Active image post has no media.')
    if len(media) != len(alts) or any(not x.strip() for x in alts):
        _event(events, uid, network, 'WARN', 'ALT_TEXT_MISSING_OR_MISMATCHED',
               'Media alternative text is missing or has a different count.')
    data = row.get(network + 'Data') or {}
    if isinstance(data, dict) and data.get('type') not in (None, 'POST'):
        _event(events, uid, network, 'HIGH', 'POST_FORMAT_CHANGED',
               'Campaign expected a static post, not another content format.')
    eastern = scheduled_datetime(row).astimezone(LOCAL_TIMEZONE)
    if eastern.hour != POSTING_HOURS[network] or eastern.minute != 0:
        _event(events, uid, network, 'HIGH', 'POSTING_TIME_OUTSIDE_CADENCE',
               'Eastern clock time differs from 9 AM Facebook / 10 AM Instagram.')
    if network == 'instagram':
        if 'link in our bio' not in row['text'].casefold():
            _event(events, uid, network, 'WARN', 'MISSING_BIO_LINK_DIRECTION',
                   'Instagram caption does not direct visitors to the profile link.')
    else:
        urls = re.findall(r'https://[^\s<>()]+', row['text'])
        def tracked(url: str) -> bool:
            try:
                parsed = urlparse(url.rstrip('.,;'))
                q = parse_qs(parsed.query)
                return (parsed.scheme == 'https' and parsed.hostname == 'www.retallyrecovery.com'
                        and q.get('utm_source') == ['facebook']
                        and q.get('utm_medium') == ['organic_social']
                        and bool(q.get('utm_campaign')) and bool(q.get('utm_content')))
            except (ValueError, TypeError):
                return False
        if not any(tracked(url) for url in urls):
            _event(events, uid, network, 'HIGH', 'FACEBOOK_LINK_NOT_TRACKED',
                   'Facebook caption lacks a canonical HTTPS RETALLY link with source/campaign/content tags.')
    status = row['providers'][0].get('status')
    if status in {'FAILED', 'ERROR', 'REJECTED'}:
        _event(events, uid, network, 'HIGH', 'PROVIDER_ERROR_STATE',
               'Metricool reports a publishing error state; verify in provider.')
    elif status not in {None, 'PENDING'}:
        _event(events, uid, network, 'INFO', 'PROVIDER_STATUS_CHANGED',
               'Planner provider state changed; this is not independent publication proof.')


def compare(baseline: dict, current: dict, *, as_of: datetime) -> dict:
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError('as_of must include a timezone')
    as_of = as_of.astimezone(timezone.utc)
    old = _index(baseline, 'baseline')
    now = _index(current, 'current')
    events = []
    for uid, item in old.items():
        network = item['providers'][0]['network']
        future = scheduled_datetime(item) > as_of
        if uid not in now:
            if item['draft']:
                _event(events, uid, network, 'WARN', 'DRAFT_NO_LONGER_IN_FEED',
                       'Original review-only draft was not returned by the latest upcoming-feed query.')
            elif future:
                _event(events, uid, network, 'HIGH', 'UPCOMING_POST_NO_LONGER_IN_FEED',
                       'Originally active future post is absent; do not assume it published.')
            else:
                _event(events, uid, network, 'INFO', 'DUE_POST_NO_LONGER_IN_FEED',
                       'Post date elapsed and it is no longer in upcoming feed; publication remains unverified.')
            continue
        updated = now[uid]
        newnet = updated['providers'][0]['network']
        if newnet != network:
            _event(events, uid, network, 'HIGH', 'NETWORK_CHANGED',
                   'Same UUID now targets a different platform.')
        for key, code, severity in (
            ('draft', 'DRAFT_FLAG_CHANGED', 'HIGH'),
            ('autoPublish', 'AUTO_PUBLISH_FLAG_CHANGED', 'HIGH'),
            ('text', 'CAPTION_CHANGED', 'WARN'),
            ('media', 'MEDIA_CHANGED', 'HIGH'),
            ('mediaAltText', 'ALT_TEXT_CHANGED', 'WARN'),
        ):
            if item[key] != updated[key]:
                _event(events, uid, network, severity, code,
                       f'Original {key} differs from current queue; review before publication.')
        if scheduled_datetime(item) != scheduled_datetime(updated):
            _event(events, uid, network, 'HIGH', 'SCHEDULE_INSTANT_CHANGED',
                   'Original UTC publishing instant differs from latest queue; check time-zone conversion.')
        fmt1 = (item.get(network + 'Data') or {}).get('type') if isinstance(item.get(network + 'Data'), dict) else None
        fmt2 = (updated.get(newnet + 'Data') or {}).get('type') if isinstance(updated.get(newnet + 'Data'), dict) else None
        if fmt1 != fmt2:
            _event(events, uid, network, 'HIGH', 'FORMAT_CHANGED',
                   'Static post type differs from original approved format.')
    for uid, row in now.items():
        if uid not in old:
            _event(events, uid, row['providers'][0]['network'],
                   'INFO' if row['draft'] else 'HIGH',
                   'ADDED_REVIEW_DRAFT' if row['draft'] else 'NEW_ACTIVE_POST',
                   'New review-only draft is not in the frozen baseline.'
                   if row['draft'] else 'Unapproved active post is absent from frozen campaign.')
        _quality(uid, row, events)
    # Sorting does not use current time or mutable numeric Metricool post IDs.
    events.sort(key=lambda x: (x['uuid'], x['code']))
    severity_counts = {level: sum(x['severity'] == level for x in events)
                       for level in ('HIGH', 'WARN', 'INFO')}
    return {
        'as_of_utc': as_of.isoformat(),
        'baseline_active': sum(not x['draft'] for x in old.values()),
        'current_active': sum(not x['draft'] for x in now.values()),
        'baseline_drafts': sum(x['draft'] for x in old.values()),
        'current_drafts': sum(x['draft'] for x in now.values()),
        'severity_counts': severity_counts,
        'preflight_state': 'REVIEW_HIGH_RISK_DRIFT' if severity_counts['HIGH']
                           else 'NO_HIGH_RISK_DRIFT_DETECTED',
        'publication_verification': 'NOT_CHECKED',
        'evidence_limit': 'Upcoming queue comparisons never certify a live Meta post, delivery or engagement.',
        'events': events,
    }


def render(result: dict) -> str:
    lines = ['# RETALLY — Social Queue Preflight',
             f"Read-only comparison: {result['as_of_utc']}",
             f"**{result['preflight_state']}**; publication NOT independently checked.",
             '',
             f"Frozen: {result['baseline_active']} active + {result['baseline_drafts']} draft. "
             f"Fresh: {result['current_active']} active + {result['current_drafts']} draft.",
             f"Changes: {result['severity_counts']['HIGH']} high, "
             f"{result['severity_counts']['WARN']} review, "
             f"{result['severity_counts']['INFO']} informational.", '',
             '| Network | Immutable UUID | Severity | Check | Explanation |',
             '| --- | --- | --- | --- | --- |']
    def cell(v):
        return str(v).replace('|', '\\|').replace('\n', ' ')
    for e in result['events']:
        lines.append('| ' + ' | '.join(cell(e[k]) for k in
                     ('network', 'uuid', 'severity', 'code', 'detail')) + ' |')
    if not result['events']:
        lines.append('| — | — | — | — | No changes detected in the current planner snapshot. |')
    lines.extend(['', '**Limit:** ' + result['evidence_limit'],
                  'An unchanged draft is not approved for publication.',
                  'An item missing after its due date requires a real public-permalink check.',
                  ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--current', required=True)
    parser.add_argument('--as-of', help='Offset-aware ISO timestamp; defaults to now')
    parser.add_argument('--output', help='Markdown file; otherwise stdout')
    parser.add_argument('--json-output', help='Machine-readable report')
    parser.add_argument('--fail-on-risk', action='store_true',
                        help='Exit 2 on high-severity drift (for manual/PR CI gating)')
    args = parser.parse_args()
    when = parse_timestamp(args.as_of) if args.as_of else datetime.now(timezone.utc)
    report = compare(read_json(args.baseline), read_json(args.current), as_of=when)
    if args.output:
        Path(args.output).write_text(render(report), encoding='utf-8')
    else:
        print(render(report))
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.fail_on_risk and report['severity_counts']['HIGH']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
