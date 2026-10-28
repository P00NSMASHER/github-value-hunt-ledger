#!/usr/bin/env python3
"""Deterministic, read-only sanity screen for published coding bounties.

Does NOT fetch sites, claim bounties, contact maintainers, or imply payment.
Input: JSON array of bounty listing rows. See bounty_census_2026-10-28.json.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def issue_key(url: str) -> str:
    """Canonicalize only conventional public GitHub issue URLs."""
    u = urlparse(url)
    parts = u.path.strip('/').split('/')
    if u.scheme != 'https' or u.netloc.lower() != 'github.com' or len(parts) != 4 or parts[2] != 'issues' or not parts[3].isdigit():
        raise ValueError('Expected a canonical https://github.com/owner/repo/issues/N URL')
    return urlunparse(('https', 'github.com', '/' + '/'.join(parts), '', '', ''))


def dollars(v: object) -> Decimal:
    try:
        n = Decimal(str(v))
    except (InvalidOperation, ValueError):
        raise ValueError('Invalid dollar amount') from None
    if not n.is_finite() or n < 0 or n.as_tuple().exponent < -2:
        raise ValueError('Bounty amount must be finite, nonnegative cents')
    return n


def evaluate(rows: list[dict], min_reward: Decimal = Decimal('100')) -> dict:
    if not isinstance(rows, list):
        raise ValueError('Input must be an array of listing objects')
    groups: dict[str, list[dict]] = defaultdict(list)
    seen_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Each listing must be an object')
        listing_id = row.get('listing_id')
        if not isinstance(listing_id, str) or not listing_id or listing_id in seen_ids:
            raise ValueError('Each listing needs a unique nonempty listing_id')
        seen_ids.add(listing_id)
        dollars(row['advertised_usd'])
        groups[issue_key(row['issue_url'])].append(row)

    results = []
    advertised = Decimal(0)
    for url, items in sorted(groups.items()):
        amount = sum((dollars(r['advertised_usd']) for r in items), Decimal(0))
        advertised += amount
        # Contradictory status fields fail closed rather than choosing a favorable row.
        states = {r.get('github_state') for r in items}
        archived = {r.get('repo_archived') for r in items}
        external_allowed = {r.get('external_contributors_allowed') for r in items}
        payouts = {r.get('recent_awards_verified') for r in items}
        claims = [r.get('claim_count') for r in items]
        if 'closed' in states:
            status = 'BLOCKED_CLOSED'
        elif True in archived:
            status = 'BLOCKED_ARCHIVED'
        elif states != {'open'} or archived != {False}:
            status = 'UNVERIFIED_STATE'
        elif amount < min_reward:
            status = 'TOO_SMALL_FOR_FIRST_100'
        elif len(external_allowed) != 1 or external_allowed != {True}:
            status = 'UNVERIFIED_EXTERNAL_ELIGIBILITY'
        elif any(not isinstance(c, int) or isinstance(c, bool) or c > 3 or c < 0 for c in claims):
            status = 'UNVERIFIED_OR_HIGH_COMPETITION'
        elif payouts != {True}:
            status = 'UNVERIFIED_RECENT_PAYOUT'
        else:
            status = 'REVIEW_READY_NOT_PAYMENT_GUARANTEE'
        results.append({'issue_url': url, 'listing_count': len(items),
                        'advertised_usd': f'{amount:.2f}', 'status': status,
                        'listing_ids': [r['listing_id'] for r in items]})
    return {'listings': len(rows), 'unique_issues': len(groups),
            'gross_advertised_usd': f'{advertised:.2f}',
            'review_ready_count': sum(r['status'] == 'REVIEW_READY_NOT_PAYMENT_GUARANTEE' for r in results),
            'collectible_usd_verified': '0.00',
            'issues': results}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='JSON array of listing rows')
    p.add_argument('--min-reward-usd', default='100', help='minimum issue-level reward for the first-$100 screen')
    args = p.parse_args()
    report = evaluate(json.loads(args.input.read_text(encoding='utf-8')), dollars(args.min_reward_usd))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
