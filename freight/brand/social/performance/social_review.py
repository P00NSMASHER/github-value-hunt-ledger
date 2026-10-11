#!/usr/bin/env python3
"""Read-only RETALLY social launch verifier: local Metricool snapshots only.

No network calls, API credentials, background jobs, posts, or customer data.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

LOCAL_TIMEZONE = ZoneInfo('America/New_York')
VALID_NETWORKS = frozenset({'facebook', 'instagram'})
POSTING_HOURS = {'facebook': 9, 'instagram': 10}


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError('Timestamp must be a string')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f'Timestamp must include a timezone offset: {value}')
    return dt.astimezone(timezone.utc)


def read_json(path: str | Path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data, dict) and isinstance(data.get('text'), str):
        data = json.loads(data['text'])
    return data


def scheduled_datetime(post: dict) -> datetime:
    record = post.get('publicationDate') or {}
    local = datetime.fromisoformat(record['dateTime'])
    if local.tzinfo is not None:
        raise ValueError('Metricool dateTime must be timezone-naive and accompanied by IANA timezone')
    zone = ZoneInfo(record['timezone'])
    aware = local.replace(tzinfo=zone)
    # Catch nonexistent DST wall times: never quietly normalize a missing hour.
    if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != local:
        raise ValueError(f'Nonexistent local scheduled time: {record}')
    return aware.astimezone(timezone.utc)


def _is_allowed_permalink(network: str, permalink: str) -> bool:
    try:
        parsed = urlparse(permalink)
        host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            return False
        if network == 'facebook':
            return host in {'facebook.com', 'www.facebook.com', 'm.facebook.com'} and bool(parsed.path.strip('/'))
        return host in {'instagram.com', 'www.instagram.com'} and parsed.path.startswith(('/p/', '/reel/'))
    except (TypeError, ValueError):
        return False


def _record_receipts(data: dict, as_of: datetime) -> dict:
    receipts = {}
    for receipt in data.get('verified_publications', []):
        uid = receipt.get('uuid')
        network = receipt.get('network')
        permalink = receipt.get('permalink')
        if not uid or uid in receipts or network not in VALID_NETWORKS:
            raise ValueError('Receipt requires a unique UUID and Facebook/Instagram network')
        if not _is_allowed_permalink(network, permalink):
            raise ValueError(f'Invalid verified publication permalink for {uid}')
        verified = parse_timestamp(receipt['verified_at'])
        if verified > as_of:
            raise ValueError(f'Publication verification cannot occur in the future: {uid}')
        receipts[uid] = {'network': network, 'permalink': permalink, 'verified_at': verified.isoformat()}
    return receipts


def _optional_nonnegative_int(data: dict, field: str):
    if field not in data or data[field] is None:
        return None
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f'{field} must be a nonnegative integer or null')
    return value


def _read_metrics(data: dict) -> dict:
    observed = {}
    for item in data.get('posts', []):
        uid = item.get('uuid')
        if not uid or uid in observed:
            raise ValueError('Metric row must have unique UUID')
        observed[uid] = {k: _optional_nonnegative_int(item, k) for k in (
            'reach', 'impressions', 'reactions', 'likes', 'comments', 'shares', 'saves', 'clicks')}
    return observed


def _engagement(network: str, row: dict) -> int | None:
    keys = ('reactions', 'comments', 'shares', 'clicks') if network == 'facebook' else (
        'likes', 'comments', 'shares', 'saves')
    if any(row.get(k) is None for k in keys):
        return None
    return sum(row[k] for k in keys)


def review(schedule: dict, receipts: dict, metrics: dict, *, as_of: datetime) -> dict:
    as_of = as_of.astimezone(timezone.utc)
    records = schedule.get('data')
    if not isinstance(records, list):
        raise ValueError('Expected Metricool scheduled-post snapshot with data: []')
    publication_receipts = _record_receipts(receipts, as_of)
    metric_rows = _read_metrics(metrics)
    posts = []
    seen = set()
    for post in records:
        providers = post.get('providers') or []
        if len(providers) != 1 or providers[0].get('network') not in VALID_NETWORKS:
            continue
        network = providers[0]['network']
        uid = str(post.get('uuid') or '')
        if not uid or uid in seen:
            raise ValueError('Active and draft post UUIDs must be present and unique')
        seen.add(uid)
        when = scheduled_datetime(post)
        eastern = when.astimezone(LOCAL_TIMEZONE)
        draft = post.get('draft') is True
        autopublish = post.get('autoPublish') is True
        receipt = publication_receipts.get(uid)
        warnings = []
        if receipt and receipt['network'] != network:
            raise ValueError(f'Network mismatch between post and proof of publication: {uid}')
        if draft:
            status = 'DRAFT'
            if autopublish:
                warnings.append('Draft unexpectedly has automatic publishing enabled')
            if receipt:
                warnings.append('Publication receipt exists for an item still marked draft; investigate')
        elif receipt:
            status = 'VERIFIED_PUBLIC'
        elif when > as_of:
            status = 'UPCOMING_NOT_YET_PUBLIC'
        else:
            status = 'PUBLICATION_UNVERIFIED'
        if not draft and not autopublish:
            warnings.append('Non-draft post has automatic publishing disabled')
        media = post.get('media') or []
        alt = post.get('mediaAltText') or []
        if not media:
            warnings.append('No attached media')
        if len(media) != len(alt) or any(not isinstance(v, str) or not v.strip() for v in alt):
            warnings.append('Image alternative text is missing or mismatched')
        caption = post.get('text') or ''
        if not draft and network == 'facebook' and (
            'utm_source=facebook' not in caption or 'retallyrecovery.com' not in caption):
            warnings.append('Facebook campaign caption lacks a tagged RETALLY landing link')
        if not draft and network == 'instagram' and 'link in our bio' not in caption.lower():
            warnings.append('Instagram campaign caption lacks a link-in-bio direction')
        if not draft and eastern.hour != POSTING_HOURS[network]:
            warnings.append('Eastern publication hour differs from the configured campaign cadence')
        metric = metric_rows.get(uid, {})
        engagement = _engagement(network, metric) if metric else None
        reach = metric.get('reach')
        posts.append({
            'uuid': uid, 'network': network, 'date_et': eastern.strftime('%Y-%m-%d %I:%M %p %Z'),
            'utc': when.isoformat(), 'status': status, 'draft': draft,
            'auto_publish': autopublish, 'provider_status': providers[0].get('status'),
            'media_count': len(media), 'warnings': warnings,
            'receipt': receipt, 'reach': reach, 'impressions': metric.get('impressions'),
            'interactions': engagement,
            'interaction_rate': round(engagement / reach, 4) if engagement is not None and reach else None,
        })
    for uid in publication_receipts.keys() | metric_rows.keys():
        if uid not in seen:
            raise ValueError(f'Receipt/metric for unknown Facebook/Instagram post UUID: {uid}')
    posts.sort(key=lambda x: (x['utc'], x['network']))
    counts = {name: sum(p['status'] == name for p in posts) for name in (
        'DRAFT', 'UPCOMING_NOT_YET_PUBLIC', 'PUBLICATION_UNVERIFIED', 'VERIFIED_PUBLIC')}
    by_network = {}
    for network in sorted(VALID_NETWORKS):
        eligible = [p for p in posts if p['network'] == network and p['status'] == 'VERIFIED_PUBLIC'
                    and p['reach'] is not None and p['interactions'] is not None]
        cumulative_reach = sum(p['reach'] for p in eligible)
        cumulative_interactions = sum(p['interactions'] for p in eligible)
        by_network[network] = {
            'confirmed_posts_with_complete_measurement': len(eligible),
            'summed_post_reach_not_unique_audience': cumulative_reach,
            'recorded_interactions': cumulative_interactions,
            'descriptive_interactions_per_summed_post_reach': round(cumulative_interactions / cumulative_reach, 4)
              if cumulative_reach else None,
            'can_prioritize_content_by_results': len(eligible) >= 4 and cumulative_reach >= 100,
        }
    return {
        'as_of_utc': as_of.isoformat(),
        'evidence_limits': [
            'Pending in Metricool does not confirm a public Facebook or Instagram post.',
            'Absence of a receipt is UNVERIFIED, never proof that a post failed.',
            'Missing metrics are unknown, never automatically zero.',
            'Summed post reach is not the number of unique people across posts.',
            'Even the minimum sample gate is descriptive, not statistically causal.',
            'A website click or prepared email draft is not a verified customer inquiry.',
        ],
        'counts': counts, 'by_network': by_network, 'posts': posts,
    }


def markdown(result: dict) -> str:
    rows = [
        '# RETALLY social launch evidence report',
        f"Snapshot: {result['as_of_utc']} — **read-only**, no actions performed.",
        '',
        '## Publication status',
        ' | '.join(f"{key.replace('_', ' ').title()}: **{count}**" for key,count in result['counts'].items()),
        '',
        '| Eastern time | Platform | Evidence state | Reach | Interactions | QA |',
        '| --- | --- | --- | ---: | ---: | --- |',
    ]
    for post in result['posts']:
        rows.append(' | '.join((
            f"| {post['date_et']}",post['network'].title(),post['status'],
            str(post['reach']) if post['reach'] is not None else '—',
            str(post['interactions']) if post['interactions'] is not None else '—',
            '; '.join(post['warnings']) if post['warnings'] else 'Pass') )+' |')
    rows.extend(['','## Measurement readiness'])
    for network,vals in result['by_network'].items():
        rows.append(f"**{network.title()}:** {vals['confirmed_posts_with_complete_measurement']} verified, "
           f"measured posts; summed per-post reach {vals['summed_post_reach_not_unique_audience']}; "
           f"interactions {vals['recorded_interactions']}. "
           f"Evidence gate: **{'met for exploratory comparison' if vals['can_prioritize_content_by_results'] else 'insufficient'}**.")
    rows.extend(['','## Evidence limitations'])
    rows.extend(f'- {v}' for v in result['evidence_limits'])
    rows.append('')
    return '\n'.join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule', required=True, help='Original JSON returned by Metricool getScheduledPosts')
    parser.add_argument('--receipts', help='Optional manually verified public permalinks JSON')
    parser.add_argument('--metrics', help='Optional metric rows keyed by stable post UUID')
    parser.add_argument('--as-of', help='UTC or offset-aware ISO timestamp; default now')
    parser.add_argument('--output', help='Optional Markdown report path; otherwise print')
    parser.add_argument('--json-output', help='Optional machine-readable report path')
    args = parser.parse_args()
    as_of = parse_timestamp(args.as_of) if args.as_of else datetime.now(timezone.utc)
    summary = review(read_json(args.schedule), read_json(args.receipts) if args.receipts else {},
                     read_json(args.metrics) if args.metrics else {}, as_of=as_of)
    content = markdown(summary)
    if args.output:
        Path(args.output).write_text(content, encoding='utf-8')
    else:
        print(content)
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
