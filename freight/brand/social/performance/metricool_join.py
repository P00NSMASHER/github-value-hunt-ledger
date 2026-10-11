#!/usr/bin/env python3
"""Offline, fail-closed bridge from Metricool post rows to RETALLY evidence.

Metricool-reported permalinks are CANDIDATES, never independent proof.
No network access, credentials, posts, or background jobs.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from social_review import LOCAL_TIMEZONE, parse_timestamp, read_json, scheduled_datetime, _record_receipts

SPEC = {
    'facebook': {
        'date': 'FBPO01', 'caption': 'FBPO03', 'url': 'FBPO06',
        'metrics': {'comments': 'FBPO08', 'impressions': 'FBPO11',
                    'reach': 'FBPO12', 'reactions': 'FBPO13',
                    'shares': 'FBPO14', 'clicks': 'FBPO23'},
    },
    'instagram': {
        'date': 'IGPO01', 'caption': 'IGPO03', 'url': 'IGPO06',
        'metrics': {'comments': 'IGPO08', 'likes': 'IGPO13',
                    'reach': 'IGPO14', 'saves': 'IGPO15', 'shares': 'IGPO27'},
    },
}


def _caption(value):
    if not isinstance(value, str):
        return ''
    return ' '.join(unicodedata.normalize('NFKC', value).split()).casefold()


def _metric(value):
    """Parse Metricool's integer-like strings without turning null into zero."""
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('Boolean is not a metric count')
    if isinstance(value, int):
        if value < 0:
            raise ValueError('Negative metric count')
        return value
    if isinstance(value, float):
        if not (value.is_integer() and 0 <= value < float('inf')):
            raise ValueError('Fractional, negative, or nonfinite metric count')
        return int(value)
    if isinstance(value, str) and re.fullmatch(r'\d+(?:\.0+)?', value.strip()):
        return int(value.strip().split('.')[0])
    raise ValueError('Invalid metric count')


def _published_date(value):
    if not isinstance(value, str):
        raise ValueError('Provider post date is absent')
    if re.fullmatch(r'\d{8}', value):
        return datetime.strptime(value, '%Y%m%d').date()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return date.fromisoformat(value)
    raise ValueError('Unrecognized provider post date')


def _public_post_url(network, value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port:
            return False
        host = (parsed.hostname or '').lower()
        path = parsed.path
        if network == 'instagram':
            return host in {'instagram.com', 'www.instagram.com'} and bool(re.fullmatch(r'/(?:p|reel)/[\w-]+/?', path))
        if host not in {'facebook.com', 'www.facebook.com', 'm.facebook.com'}:
            return False
        return bool(re.search(r'/(?:posts|videos)/[^/]+/?$', path) or
                    re.fullmatch(r'/share/p/[^/]+/?', path) or
                    (path.endswith('/story.php') and 'story_fbid=' in parsed.query))
    except (TypeError, ValueError):
        return False


def _same_url(a, b):
    """Compare independently reviewed publication URLs, not pages/profiles."""
    u, v = urlparse(a), urlparse(b)
    def canon(host):
        return (host or '').lower().removeprefix('www.').removeprefix('m.')
    return (u.scheme, canon(u.hostname), u.path.rstrip('/')) == (
        v.scheme, canon(v.hostname), v.path.rstrip('/'))


def _load_export(document, network, as_of):
    spec = SPEC[network]
    if not isinstance(document, dict):
        raise ValueError(f'{network} export must be a JSON object')
    field_ids = document.get('field_ids')
    if not isinstance(field_ids, list) or len(field_ids) != len(set(field_ids)):
        raise ValueError(f'{network} export needs unique, ordered field_ids')
    required = {spec['date'], spec['caption'], spec['url']}
    if not required.issubset(field_ids):
        raise ValueError(f'{network} export is missing {sorted(required - set(field_ids))}')
    collected_at = parse_timestamp(document.get('observed_at'))
    if collected_at > as_of:
        raise ValueError(f'{network} export observed_at is in the future')
    rows = document.get('rows')
    if not isinstance(rows, list):
        raise ValueError(f'{network} export needs rows: []')
    parsed = []
    for n, row in enumerate(rows, 1):
        if not isinstance(row, list) or len(row) != len(field_ids):
            raise ValueError(f'{network} row {n} has wrong field count')
        parsed.append(dict(zip(field_ids, row)))
    return parsed, collected_at


def join(schedule, exports, receipts, *, as_of):
    """Only exact-caption, close-date, unique matches can produce candidates.

    Verified metrics export requires *separate* independently confirmed receipts.
    """
    as_of = as_of.astimezone(timezone.utc)
    records = schedule.get('data') if isinstance(schedule, dict) else None
    if not isinstance(records, list):
        raise ValueError('Frozen schedule requires data: []')
    approved = _record_receipts(receipts or {}, as_of)
    lookup = {}
    known_uuids = set()
    for p in records:
        providers = p.get('providers') or []
        if len(providers) != 1 or providers[0].get('network') not in SPEC:
            continue
        uuid = str(p.get('uuid') or '')
        if not uuid or uuid in known_uuids:
            raise ValueError('Duplicate or missing schedule UUID')
        known_uuids.add(uuid)
        if p.get('draft') is True:
            continue
        key = (providers[0]['network'], _caption(p.get('text')))
        lookup.setdefault(key, []).append(p)
    if not set(approved).issubset(known_uuids):
        raise ValueError('Independent receipt contains a UUID absent from frozen schedule')
    candidates, skipped, metrics = [], [], []
    used = set()
    for network in ('facebook', 'instagram'):
        doc = exports.get(network)
        if doc is None:
            continue
        provider_rows, observed_at = _load_export(doc, network, as_of)
        spec = SPEC[network]
        for index, row in enumerate(provider_rows, 1):
            key = (network, _caption(row[spec['caption']]))
            matches = lookup.get(key, [])
            identifier = {'network': network, 'row_number': index}
            if not key[1]:
                skipped.append({**identifier, 'reason': 'EMPTY_CAPTION'})
                continue
            if not matches:
                skipped.append({**identifier, 'reason': 'NOT_IN_FROZEN_CAMPAIGN'})
                continue
            if len(matches) > 1:
                skipped.append({**identifier, 'reason': 'AMBIGUOUS_DUPLICATE_CAPTION'})
                continue
            p = matches[0]
            uid = str(p['uuid'])
            if uid in used:
                skipped.append({**identifier, 'uuid': uid, 'reason': 'DUPLICATE_ANALYTICS_ROW'})
                continue
            try:
                day = _published_date(row[spec['date']])
            except ValueError:
                skipped.append({**identifier, 'uuid': uid, 'reason': 'BAD_PROVIDER_DATE'})
                continue
            eastern = scheduled_datetime(p).astimezone(LOCAL_TIMEZONE).date()
            if abs((day - eastern).days) > 1 or day > observed_at.date():
                skipped.append({**identifier, 'uuid': uid, 'reason': 'DATE_MISMATCH'})
                continue
            permalink = row[spec['url']]
            if not _public_post_url(network, permalink):
                skipped.append({**identifier, 'uuid': uid, 'reason': 'NOT_A_PUBLIC_POST_URL'})
                continue
            try:
                numbers = {name: _metric(row.get(field)) for name, field in spec['metrics'].items()}
            except ValueError:
                skipped.append({**identifier, 'uuid': uid, 'reason': 'INVALID_PROVIDER_METRIC'})
                continue
            receipt = approved.get(uid)
            verified = bool(receipt and receipt['network'] == network and
                            _same_url(receipt['permalink'], permalink))
            if receipt and not verified:
                skipped.append({**identifier, 'uuid': uid, 'reason': 'INDEPENDENT_RECEIPT_URL_MISMATCH'})
                continue
            used.add(uid)
            candidates.append({
                'uuid': uid, 'network': network, 'provider_permalink': permalink,
                'scheduled_date_et': eastern.isoformat(), 'provider_date': day.isoformat(),
                'observed_at_utc': observed_at.isoformat(),
                'evidence_state': 'INDEPENDENTLY_VERIFIED_WITH_RECEIPT' if verified else 'PROVIDER_REPORTED_UNVERIFIED',
                'metrics': numbers,
            })
            if verified:
                metrics.append({'uuid': uid, **numbers,
                                'observed_at': observed_at.isoformat(),
                                'source_permalink': permalink})
    return {
        'as_of_utc': as_of.isoformat(),
        'counts': {'provider_matched': len(candidates),
                   'independently_verified_matched': len(metrics),
                   'unmatched_or_rejected': len(skipped)},
        'evidence_limits': [
            'A Metricool post URL alone is NOT independent proof that a visitor can see the post.',
            'Only exact normalized-caption and near-date unique matches are joined.',
            'Only matches with separately verified same-post receipts can export report-ready metric rows.',
            'No observed metric is turned into a qualified inquiry or recovered funds.',
        ],
        'candidates': candidates, 'skipped': skipped,
        'verified_metrics': {'posts': metrics},
    }


def markdown(summary):
    lines = ['# RETALLY — Metricool publication evidence matching',
             f"On-demand snapshot: {summary['as_of_utc']}", '',
             'Metricool publication rows are **candidates only** until independently verified.', '',
             f"Provider matches: **{summary['counts']['provider_matched']}**; "
             f"independently verified: **{summary['counts']['independently_verified_matched']}**; "
             f"skipped: **{summary['counts']['unmatched_or_rejected']}**.", '',
             '| Network | Frozen UUID | Provider result | Reach |',
             '| --- | --- | --- | ---: |']
    for c in summary['candidates']:
        lines.append('| ' + ' | '.join([c['network'], c['uuid'], c['evidence_state'],
                       str(c['metrics'].get('reach')) if c['metrics'].get('reach') is not None else 'unknown']) + ' |')
    if summary['skipped']:
        lines.extend(['', '## Unmatched / rejected Metricool rows'])
        for x in summary['skipped']:
            lines.append(f"- {x['network']} row {x['row_number']}: {x['reason']}" +
                         (f" (UUID {x['uuid']})" if x.get('uuid') else ''))
    lines.extend(['', '## Evidence limits'] + [f'- {s}' for s in summary['evidence_limits']])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedule', required=True)
    parser.add_argument('--facebook-export', help='JSON with field_ids, observed_at, rows returned by Metricool')
    parser.add_argument('--instagram-export', help='Same shape as Facebook export')
    parser.add_argument('--receipts', help='Optional independently verified publication receipts')
    parser.add_argument('--as-of', help='Offset-aware timestamp; defaults to now')
    parser.add_argument('--output', help='Markdown report file, otherwise stdout')
    parser.add_argument('--json-output', help='Full machine-readable evidence report')
    parser.add_argument('--verified-metrics-output', help='Only metrics for independently verified receipts')
    args = parser.parse_args()
    current = parse_timestamp(args.as_of) if args.as_of else datetime.now(timezone.utc)
    exports = {}
    for network, path in (('facebook', args.facebook_export), ('instagram', args.instagram_export)):
        if path:
            exports[network] = read_json(path)
    result = join(read_json(args.schedule), exports,
                  read_json(args.receipts) if args.receipts else {}, as_of=current)
    rendered = markdown(result)
    if args.output:
        Path(args.output).write_text(rendered, encoding='utf-8')
    else:
        print(rendered)
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if args.verified_metrics_output:
        Path(args.verified_metrics_output).write_text(json.dumps(result['verified_metrics'], indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()